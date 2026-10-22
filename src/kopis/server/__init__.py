"""Kopis: pure-Python web development (server side).

This is the server-side half of the ``kopis`` package: it runs on CPython
and serves a web application — a root directory of static files, an HTML
document at ``/``, and RPC to and from clients. The client-side half
(the ``kopis.client`` subpackage) runs in the browser under Brython; with
``Kopis(use="brython")`` the whole package is served to the browser, so
``import kopis`` resolves to the client side there.
"""

__all__ = ["Document", "Element", "Kopis"]

import asyncio
import contextvars
import inspect
import itertools
import json
import os
import sys
import time
import uuid
from collections.abc import Callable
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Self

from aiohttp import web
from aiohttp_session import Session, get_session, setup
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from aiohttp_sse import EventSourceResponse
from bs4 import BeautifulSoup, Tag
from bs4.builder import HTMLTreeBuilder

try:
    from dataclasses import asdict, is_dataclass
except ImportError:  # Interpreter without dataclasses support.
    asdict = None
    is_dataclass = None


# --- Wire format, shared with the client-side `kopis` subpackage ---------
#
# RPC messages are JSON. Custom types participate by defining a
# ``to_json()`` method that returns plain JSON-able data; dataclasses and
# objects with a ``__dict__`` are converted to a dict of their attributes;
# anything else falls back to ``str()``. Neither side assumes the other
# side has the same types — a value always arrives on the receiving end
# as plain JSON data (dicts, lists, strings, numbers).


class RpcError(Exception):
    """Raised when a remote function call failed on the other side."""

    def __init__(self, type: str, message: str) -> None:
        super().__init__(f"{type}: {message}")
        self.type = type
        self.message = message


def _convert(value: object) -> object:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    to_json = getattr(value, "to_json", None)
    if callable(to_json):
        return _convert(to_json())
    if (
        is_dataclass is not None
        and asdict is not None
        and is_dataclass(value)
        and not isinstance(value, type)
    ):
        return _convert(asdict(value))
    if isinstance(value, dict):
        return {key: _convert(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_convert(item) for item in value]
    if hasattr(value, "__dict__"):
        return _convert(vars(value))
    return str(value)


def encode(value: object) -> str:
    """Serialize ``value`` to a JSON string, converting custom types to plain data."""
    return json.dumps(_convert(value))


def decode(text: str) -> Any:
    """Parse a JSON string into plain Python values."""
    return json.loads(text)


def _entry_script_dir() -> Path | None:
    """Return the directory of the running script, if determinable."""
    argv0 = sys.argv[0] if sys.argv else ""

    if argv0 and Path(argv0).is_file():
        return Path(argv0).resolve().parent

    # Fall back to the file of the __main__ module on the call stack
    # (covers cases where sys.argv[0] is not a file, e.g. ``python -c``).
    frame = inspect.currentframe()

    while frame is not None:
        if frame.f_globals.get("__name__") == "__main__":
            file = frame.f_globals.get("__file__")

            if file:
                return Path(file).resolve().parent

        frame = frame.f_back

    return None


#: Tags that never have children or an end tag.
_empty_tags = HTMLTreeBuilder.DEFAULT_EMPTY_ELEMENT_TAGS
_VOID_TAGS = frozenset(_empty_tags) if _empty_tags is not None else frozenset()

#: How long an SSE stream waits for the next call before re-checking whether
#: the client is still connected (bounded by the response's ping interval).
_SSE_IDLE_TIMEOUT = 15.0


def _line_offsets(text: str) -> list[int]:
    """Return the offset of the first character of every line in ``text``."""
    offsets = [0]
    for i, ch in enumerate(text):
        if ch == "\n":
            offsets.append(i + 1)
    return offsets


def _insertion_offset(text: str, tag: Tag) -> int:
    """Return the offset in ``text`` where new children of ``tag`` belong.

    ``tag`` must be an element parsed from ``text``; its ``sourceline``
    and ``sourcepos`` attributes identify which element it is. The
    returned offset is just before ``tag``'s end tag, or just before the
    end tag that implicitly closes it. If the element has no end tag in
    the document, the offset is the end of the document.
    """
    target = (tag.sourceline, tag.sourcepos)
    line_offsets = _line_offsets(text)
    found: list[int | None] = [None]

    class _Scanner(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.stack: list[tuple[str, int, int]] = []

        def _offset(self) -> int:
            line, col = self.getpos()
            return line_offsets[line - 1] + col

        def handle_starttag(
            self, tag: str, attrs: list[tuple[str, str | None]]
        ) -> None:
            if tag in _VOID_TAGS:
                return
            line, col = self.getpos()
            self.stack.append((tag, line, col))

        def handle_endtag(self, tag: str) -> None:
            if found[0] is not None:
                return
            for i in range(len(self.stack) - 1, -1, -1):
                if self.stack[i][0] == tag:
                    break
            else:
                return  # Stray end tag with no matching open tag.
            if any(entry[1:] == target for entry in self.stack[i:]):
                found[0] = self._offset()
            del self.stack[i:]

    scanner = _Scanner()
    scanner.feed(text)
    scanner.close()
    return found[0] if found[0] is not None else len(text)


class Document:
    """A live view of the HTML document served at ``/``.

    The document is stored as a plain string; :mod:`beautifulsoup4` is
    used to parse it and locate elements. Look up an element by tag name
    with either subscripting or attribute access; both return an
    :class:`Element` for the first element with that name::

        k.document["head"].append('<meta name="viewport" content="...">')
        with k.document.body as el:
            el.append("<script src=...></script>")
    """

    def __init__(self, owner: Kopis) -> None:
        self._owner = owner

    def _element(self, name: str) -> Element:
        tag = self._owner._parse().find(name)
        if tag is None:
            raise KeyError(f"no <{name}> element in the document")
        return Element(self, tag)

    def __getitem__(self, name: str) -> Element:
        return self._element(name)

    def __getattr__(self, name: str) -> Element:
        # Only called when normal attribute lookup fails. Dunder lookups
        # (pickle, copy, introspection) must keep failing as usual, and
        # ``_owner`` is guarded to avoid infinite recursion on a
        # half-initialized instance.
        if name == "_owner" or (name.startswith("__") and name.endswith("__")):
            raise AttributeError(name)
        try:
            return self._element(name)
        except KeyError as exc:
            raise AttributeError(str(exc)) from exc

    def __str__(self) -> str:
        return str(self._owner._parse())

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None


class Element:
    """A reference to an element of the document.

    The ``tag`` attribute is the underlying
    :class:`bs4.element.Tag`, so any Beautiful Soup method works on it.
    """

    def __init__(self, document: Document, tag: Tag) -> None:
        self._document = document
        self.tag = tag

    def append(self, *html: str) -> Element:
        """Append one or more HTML elements as children of this element.

        Each fragment is parsed with Beautiful Soup to validate it, then
        inserted as-is just before this element's end tag, so the rest of
        the document is preserved exactly. Returns ``self`` so calls can
        be chained::

            k.document["head"].append("<a/>").append("<b/>")
        """
        for fragment in html:
            self._document._owner._insert_into(self.tag, fragment)
        return self

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None


class _Rpc:
    """Proxy for ``k.rpc``: ``k.rpc.name(args)`` calls a client function."""

    def __init__(self, owner: Kopis) -> None:
        self._owner = owner

    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)

        async def call(*args: object, **kwargs: object) -> object:
            return await self._owner._call_client(name, args, kwargs)

        return call


class _Stream:
    """An open SSE stream of a client, and the queue of calls to push to it.

    The queue is a delivery mirror of the durable per-client call queue:
    a call is pushed here as soon as it is queued, and is replayed from the
    durable queue whenever the client (re)connects. ``close()`` wakes the
    delivery loop of a stream that was replaced by a newer connection.
    """

    def __init__(self) -> None:
        self.queue: asyncio.Queue[dict | None] = asyncio.Queue()

    def push(self, call: dict) -> None:
        """Queue a call for delivery to the client."""
        self.queue.put_nowait(call)

    def close(self) -> None:
        """Wake the delivery loop so it can stop (a sentinel is enqueued)."""
        self.queue.put_nowait(None)


class Kopis:
    """A web application served from a root directory.

    The root directory defaults to the directory of the running script.
    Files in the root directory are served as static assets, and the
    ``document`` is served at ``/``. The document is either an in-memory
    string assigned to ``k.document``, or the ``index.html`` file in the
    root directory. ``k.document`` also gives a :class:`Document` view
    that supports adding HTML elements to existing elements, e.g.
    ``k.document["head"].append("<script src=...></script>")``, and
    :meth:`add_static_file` serves files from anywhere on disk at a
    chosen URL.

    ``use="brython"`` configures the app to run client-side Python code
    with `Brython <https://brython.info>`_: the Brython scripts and the
    modules of the ``kopis`` package are served, and a default document
    loading the Brython scripts is created.

    RPC: decorate a server function with ``@k.bind`` to make it callable
    from the client as ``await k.rpc.<name>(...)``. Clients register
    their own functions the same way, and the server can call them back
    with ``await k.rpc.<name>(...)`` (inside a bound function, which
    targets the calling client) or ``k.call(client_id, ...)``. Calls to
    client functions are pushed over a Server-Sent Events stream
    (``/__kopis__/rpc/events``); the client posts its results back to
    ``/__kopis__/rpc/results`` as soon as they are ready. Clients are
    identified by an encrypted session cookie, and all exchanged data
    is plain JSON (custom types are converted via their ``to_json()``
    method).
    """

    def __init__(
        self,
        root: str | Path | None = None,
        use: str | None = None,
    ) -> None:
        if root is not None:
            self.root = Path(root).resolve()
        else:
            self.root = _entry_script_dir() or Path.cwd()

        self._document: str | None = None
        self._soup: BeautifulSoup | None = None

        # RPC state.
        self._bound: dict[str, Callable] = {}
        self._clients: dict[str, float] = {}
        self._pending_calls: dict[str, list[dict]] = {}
        self._pending_results: dict[int, asyncio.Future] = {}
        self._streams: dict[str, _Stream] = {}
        self._next_call_id = itertools.count(1)
        self._current_client: contextvars.ContextVar[str | None] = contextvars.ContextVar(
            "kopis_current_client", default=None
        )
        self.rpc = _Rpc(self)

        self.app = web.Application()
        # Sessions (cookie-based) identify which client a request comes from.
        setup(
            self.app,
            EncryptedCookieStorage(os.urandom(32), cookie_name="kopis_session"),
        )

        # Registered before the static route so that it takes precedence on ``/``.
        self.app.router.add_get("/", self._serve_document)
        self.app.router.add_post("/__kopis__/rpc", self._rpc)
        self.app.router.add_get("/__kopis__/rpc/events", self._rpc_events)
        self.app.router.add_post("/__kopis__/rpc/results", self._rpc_results)

        self.app.router.add_static("/", self.root, follow_symlinks=True)

        if use not in (None, "brython"):
            raise ValueError(f"unknown value for use: {use!r}")

        if use == "brython":
            self._setup_brython()

    @property
    def document(self) -> Document:
        """A live view of the HTML document served at ``/``."""
        return Document(self)

    @document.setter
    def document(self, value: str) -> None:
        self._document = value
        self._soup = BeautifulSoup(value, "html.parser")

    @property
    def soup(self) -> BeautifulSoup:
        """The document parsed with Beautiful Soup."""
        return self._parse()

    def document_text(self) -> str:
        """The raw HTML text of the document.

        Returns the in-memory document if one was assigned, otherwise
        the contents of ``index.html`` in the root directory.
        """
        if self._document is not None:
            return self._document

        index = self.root / "index.html"
        if not index.is_file():
            raise FileNotFoundError(index)

        return index.read_text()

    def _parse(self) -> BeautifulSoup:
        """The document parsed with Beautiful Soup, cached until changed."""
        if self._soup is None:
            self._soup = BeautifulSoup(self.document_text(), "html.parser")
        return self._soup

    def _insert_into(self, tag: Tag, fragment: str) -> None:
        fragment = fragment.strip()
        if not fragment:
            return

        if tag.name in _VOID_TAGS:
            raise ValueError(f"cannot add children to <{tag.name}>")

        # Parse the fragment with Beautiful Soup to validate it and to
        # confirm it actually contains elements.
        soup = BeautifulSoup(fragment, "html.parser")
        if not any(isinstance(c, Tag) for c in soup.children):
            return

        text = self.document_text()
        offset = _insertion_offset(text, tag)
        self._document = text[:offset] + fragment + text[offset:]
        self._soup = None

    def bind(self, func) -> Callable:
        """Register a function so that clients can call it via ``k.rpc``.

        The function is called with the JSON-decoded arguments sent by the
        client; inside it, ``k.rpc`` targets the client that made the call::

            @k.bind
            async def add(x, y):
                return x + y
        """
        self._bound[func.__name__] = func
        return func

    def call(
        self, client_id: str, method: str, *args: object, **kwargs: object
    ) -> asyncio.Future:
        """Queue a call to a function the client registered with :meth:`bind`.

        Returns a future that resolves with the client's return value, or
        raises :class:`RpcError` if the call failed there.
        The call is pushed to the client's open SSE stream at once, or held
        in the queue until the client (re)connects. Requires a running
        event loop.
        """
        call_id = next(self._next_call_id)
        call = {"id": call_id, "method": method, "args": list(args), "kwargs": kwargs}
        self._pending_calls.setdefault(client_id, []).append(call)
        future: asyncio.Future = asyncio.get_running_loop().create_future()
        self._pending_results[call_id] = future
        stream = self._streams.get(client_id)
        if stream is not None:
            stream.push(call)
        return future

    async def _call_client(self, method: str, args: tuple, kwargs: dict) -> object:
        """Call a client function on the client that is currently being served."""
        client_id = self._current_client.get()
        if client_id is None:
            raise RuntimeError(
                "k.rpc can only be used inside a function called by a client; "
                "use k.call(client_id, ...) to target a client explicitly"
            )
        return await self.call(client_id, method, *args, **kwargs)

    @property
    def clients(self) -> dict[str, float]:
        """Client ids (session cookies) with their last activity time."""
        return dict(self._clients)

    def _ensure_client_id(self, session: Session) -> str:
        client_id = session.get("client_id")
        if client_id is None:
            client_id = uuid.uuid4().hex
            session["client_id"] = client_id
        self._clients[client_id] = time.time()
        return client_id

    def _json(self, payload: object) -> web.Response:
        """Serialize ``payload`` to a JSON response (custom types allowed)."""
        return web.Response(text=encode(payload), content_type="application/json")

    async def _rpc(self, request: web.Request) -> web.Response:
        """Handle a client -> server RPC call (POST /__kopis__/rpc)."""
        session = await get_session(request)
        client_id = self._ensure_client_id(session)
        try:
            msg = decode(await request.text())
            method: str = msg["method"]
            args: list = msg.get("args", [])
            kwargs: dict = msg.get("kwargs", {})
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise web.HTTPBadRequest(text=f"bad RPC request: {exc}")

        func = self._bound.get(method)
        if func is None:
            return self._json(
                {
                    "error": {
                        "type": "NameError",
                        "message": f"no function {method!r} bound on the server",
                    }
                }
            )

        token = self._current_client.set(client_id)
        try:
            try:
                result = func(*args, **kwargs)
                if inspect.iscoroutine(result):
                    result = await result
                payload: dict = {"result": result}
            except Exception as exc:  # noqa: BLE001 - report any failure to the client
                payload = {"error": {"type": type(exc).__name__, "message": str(exc)}}
        finally:
            self._current_client.reset(token)
        return self._json(payload)

    async def _rpc_events(self, request: web.Request) -> web.StreamResponse:
        """Serve a client's SSE stream (GET /__kopis__/rpc/events).

        The stream pushes ``call`` events, one per call queued for functions
        the client registered with :meth:`bind`. On (re)connection, every
        call still awaiting its result is replayed, so a dropped connection
        loses no work; the client skips call ids it already ran. Results
        come back over :meth:`_rpc_results`.
        """
        session = await get_session(request)
        if session.get("client_id") is None:
            # A brand-new session cannot be established here: the stream's
            # headers go out before the session middleware could set the
            # cookie. The document request always runs first and does that.
            raise web.HTTPBadRequest(text="no session; load the document first")
        client_id = self._ensure_client_id(session)
        resp = EventSourceResponse()
        await resp.prepare(request)
        stream = _Stream()
        old = self._streams.get(client_id)
        self._streams[client_id] = stream
        if old is not None:
            old.close()
        try:
            for call in list(self._pending_calls.get(client_id, [])):
                await self._send_call(resp, call)
            while True:
                try:
                    call = await asyncio.wait_for(
                        stream.queue.get(), timeout=_SSE_IDLE_TIMEOUT
                    )
                except TimeoutError:
                    if not resp.is_connected():
                        break  # client gone
                    continue
                if call is None:
                    break  # replaced by a newer connection
                await self._send_call(resp, call)
        except Exception:  # noqa: BLE001, S110 - a dead connection just ends the stream
            # Pending calls stay queued and are replayed when the client
            # (re)connects.
            pass
        finally:
            if resp.prepared:
                resp.stop_streaming()
            if self._streams.get(client_id) is stream:
                del self._streams[client_id]
        return resp

    @staticmethod
    async def _send_call(resp: EventSourceResponse, call: dict) -> None:
        await resp.send(encode(call), event="call", id=str(call["id"]))

    async def _rpc_results(self, request: web.Request) -> web.Response:
        """Handle results from a client (POST /__kopis__/rpc/results).

        Each result resolves the future created by :meth:`call` and removes
        the call from the replay queue. Duplicates (a lost round trip) are
        ignored, so the client can safely re-send results.
        """
        session = await get_session(request)
        client_id = self._ensure_client_id(session)
        try:
            msg = decode(await request.text())
            results: list = msg.get("results", [])
        except (json.JSONDecodeError, TypeError):
            raise web.HTTPBadRequest(text="bad results request")
        if not isinstance(results, list):
            raise web.HTTPBadRequest(text="bad results request")

        calls = self._pending_calls.get(client_id)
        for res in results:
            if not isinstance(res, dict):
                continue
            call_id = res.get("id")
            future = self._pending_results.pop(call_id, None)
            if future is None or future.done():
                continue
            if calls is not None:
                calls = [c for c in calls if c.get("id") != call_id]
                if calls:
                    self._pending_calls[client_id] = calls
                else:
                    del self._pending_calls[client_id]
            if "error" in res:
                err = res["error"]
                future.set_exception(RpcError(err.get("type", "Error"), err.get("message", "")))
            else:
                future.set_result(res.get("result"))
        return self._json({"ok": True})

    def _setup_brython(self) -> None:
        """Set up the app to run client-side code with Brython.

        Serves the JavaScript files of the installed ``brython`` package
        at ``/brython.js`` and ``/brython_stdlib.js``, serves the whole
        ``kopis`` package at the URLs Brython's import system expects
        (so e.g. ``from kopis import ...`` in client code resolves), and
        initializes a default document with the Brython scripts in its
        ``<head>``. The package's ``__init__`` differentiates the sides,
        so ``import kopis`` in browser code picks the client side.
        """
        import brython  # Optional dependency, required only for use="brython".

        # Locate the JavaScript files shipped with the installed `brython` package.
        brython_path = Path(brython.__file__).parent
        brython_js = brython_path / "data" / "brython.js"
        brython_stdlib_js = brython_path / "data" / "brython_stdlib.js"

        # Serve the brython scripts from where the package installed them.
        self.add_static_file("/brython.js", brython_js)
        self.add_static_file("/brython_stdlib.js", brython_stdlib_js)

        # Serve the `kopis` package at the URLs Brython's import system
        # expects, so e.g. ``from kopis import Kopis`` in client.py
        # resolves. Every ``.py`` file in the package is served at its
        # corresponding URL, so any module the client imports exists.
        # This file lives in ``kopis/server/``, so the package root is
        # two levels up.
        kopis_path = Path(__file__).resolve().parent.parent
        for file in sorted(kopis_path.rglob("*.py")):
            url = "/kopis/" + file.relative_to(kopis_path).as_posix()
            self.add_static_file(url, file)

        self.document = """
            <html>
                <head>
                    <meta charset="utf-8">
                </head>

                <body>
                </body>
            </html>
        """

        with self.document["head"] as el:
            el.append(
                '<meta name="viewport" content="width=device-width, initial-scale=1">'
            )
            el.append(
                f'<script type="text/javascript" src="{brython_js.name}"></script>'
            )
            el.append(
                f'<script type="text/javascript" src="{brython_stdlib_js.name}"></script>'
            )

    def add_static_file(self, path: str, file_path: str | Path) -> None:
        """Serve a single file at the URL ``path``.

        The explicit route takes precedence over the root static route,
        so files outside the root directory (e.g. data shipped with an
        installed package) can be served directly::

            k.add_static_file("/brython.js", brython_js_path)
        """
        file_path = Path(file_path).resolve()

        async def _handler(_request: web.Request) -> web.FileResponse:
            return web.FileResponse(file_path)

        self.app.router.add_get(path, _handler)

    async def _serve_document(self, request: web.Request) -> web.Response:
        """Serve the document, rendered as valid HTML.

        The document text (in-memory or ``index.html``) is parsed with
        Beautiful Soup and re-serialized, so the browser always receives
        a canonical, valid form of the document. The session cookie also
        identifies the client that loads the document.
        """
        try:
            html = str(self._parse())
        except FileNotFoundError:
            raise web.HTTPNotFound()

        session = await get_session(request)
        self._ensure_client_id(session)

        return web.Response(text=html, content_type="text/html")

    def run(self, host: str = "0.0.0.0", port: int = 5000) -> None:
        web.run_app(self.app, host=host, port=port)
