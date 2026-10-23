"""Kopis: pure-Python web development (server side).

This is the server-side half of the ``kopis`` package: it runs on CPython
and serves a web application — a root directory of static files, an HTML
document at ``/``, and RPC to and from clients. It shares its API with the
client-side half (the ``kopis.client`` subpackage, which runs in the browser
under Brython); only the implementation differs. With
``Kopis(use="brython")`` the whole package is served to the browser and the
running script is attached to the document, so ``import kopis`` in browser
code resolves to the client side there.
"""

__all__ = ["Document", "Element", "Kopis", "Placeholder", "RpcError", "aio"]

import asyncio
import contextvars
import html
import inspect
import itertools
import os
import sys
import time
import uuid
from collections.abc import Callable
from html.parser import HTMLParser
from pathlib import Path
from typing import Self

from .._wire import Placeholder, RpcError, decode, encode
from aiohttp import web
from aiohttp_session import Session, get_session, setup
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from bs4 import BeautifulSoup, Tag
from bs4.builder import HTMLTreeBuilder


def _entry_script() -> Path | None:
    """Return the path of the running script, if determinable."""
    argv0 = sys.argv[0] if sys.argv else ""

    if argv0 and Path(argv0).is_file():
        return Path(argv0).resolve()

    # Fall back to the file of the __main__ module on the call stack
    # (covers cases where sys.argv[0] is not a file, e.g. ``python -c``).
    frame = inspect.currentframe()

    while frame is not None:
        if frame.f_globals.get("__name__") == "__main__":
            file = frame.f_globals.get("__file__")

            if file:
                return Path(file).resolve()

        frame = frame.f_back

    return None


def _entry_script_dir() -> Path | None:
    """Return the directory of the running script, if determinable."""
    entry = _entry_script()
    return entry.parent if entry is not None else None


#: Tags that never have children or an end tag.
_empty_tags = HTMLTreeBuilder.DEFAULT_EMPTY_ELEMENT_TAGS
_VOID_TAGS = frozenset(_empty_tags) if _empty_tags is not None else frozenset()

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
    with either subscripting or attribute access, or by CSS selector
    with :meth:`querySelector`; both return an :class:`Element`::

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

    def querySelector(self, selector: str) -> Element | None:
        """Return the first element matching ``selector``, or ``None``."""
        tag = self._owner._parse().select(selector)
        if not tag:
            return None
        return Element(self, tag[0])

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

    def __le__(self, content: object) -> None:
        """Append ``content`` as text to the document (its body)."""
        self.body <= content  # noqa: B015 (<= appends to the document)

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

    def bind(self, event: str, handler: Callable) -> Element:
        """Bind an event handler to this element.

        The server has no live DOM, so this is a no-op; the handler takes
        effect when the same code runs in the browser.
        """
        return self

    def __le__(self, content: object) -> None:
        """Append ``content`` as text to this element."""
        self._document._owner._insert_into(self.tag, str(content), is_text=True)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None


class _Noop:
    """A no-op stand-in for the document (and its elements) on the server.

    In brython mode the document is built in the browser, where the same
    application code runs under Brython. Document operations therefore do
    nothing on the server (but never fail), so the unified application
    code can run unmodified on both sides.
    """

    def append(self, *html: str) -> Self:
        return self

    def bind(self, event: str, handler: Callable) -> Self:
        return self

    def querySelector(self, selector: str) -> Self:
        return self

    def __getitem__(self, name: object) -> Self:
        return self

    def __le__(self, content: object) -> None:
        return None

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None

    def __getattr__(self, name: str) -> Self:
        # Any attribute (e.g. ``body``, ``head``) resolves to the same
        # no-op, so chained lookups keep working. Dunder lookups must keep
        # failing as usual.
        if name.startswith("_"):
            raise AttributeError(name)
        return self


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
    """An open WebSocket connection of a client, and the queue of messages
    to send on it.

    The queue is a delivery mirror of the durable per-client call queue:
    a call is queued here as soon as it is queued, and is replayed from the
    durable queue whenever the client (re)connects. ``close()`` wakes the
    sender loop of a stream that was replaced by a newer connection.
    """

    def __init__(self, ws: web.WebSocketResponse) -> None:
        self.ws = ws
        self.queue: asyncio.Queue[dict | None] = asyncio.Queue()

    def push(self, message: dict) -> None:
        """Queue a message for delivery to the client."""
        self.queue.put_nowait(message)

    def close(self) -> None:
        """Wake the sender loop so it can stop (a sentinel is enqueued)."""
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
    loading the Brython scripts is created. The running script (the app)
    is attached to the document as a Brython script, so the same
    application code runs in the browser under Brython. In brython mode
    the document is built in the browser, so ``k.document`` is a no-op
    view on the server.

    RPC: decorate a function with ``@k.bind`` to make it callable from
    the other side as ``await k.rpc.<name>(...)``. Inside a bound
    function, ``k.rpc`` targets the client that made the call; calls can
    also be sent explicitly with ``k.call(client_id, ...)``. Calls and
    results travel both ways over a single WebSocket connection per
    client (``/__kopis__/rpc``), which the client re-opens on disconnect.
    Clients are identified by an encrypted session cookie, and all
    exchanged data is JSON: the values of ``args``, ``kwargs``, and
    ``result`` are pickled Python objects (base64-encoded in the JSON),
    and a value that cannot be (de)serialized arrives as a
    ``Placeholder`` carrying the string of the exception.
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
        self._noop = _Noop()

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
        self.app.router.add_get("/__kopis__/rpc", self._rpc_ws)

        self.app.router.add_static("/", self.root, follow_symlinks=True)

        if use not in (None, "brython"):
            raise ValueError(f"unknown value for use: {use!r}")

        self._brython = use == "brython"

        if self._brython:
            self._setup_brython()

    @property
    def document(self) -> Document | _Noop:
        """A live view of the HTML document served at ``/``.

        In brython mode the document is built in the browser (by the same
        application code running under Brython), so this view is a no-op
        on the server.
        """
        if self._brython:
            return self._noop
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

    def _insert_into(self, tag: Tag, fragment: str, is_text: bool = False) -> None:
        if tag.name in _VOID_TAGS:
            raise ValueError(f"cannot add children to <{tag.name}>")

        if is_text:
            # Raw text is inserted as-is (escaped); no HTML validation.
            body = html.escape(fragment)
        else:
            body = fragment.strip()
            if not body:
                return

            # Parse the fragment with Beautiful Soup to validate it and to
            # confirm it actually contains elements.
            soup = BeautifulSoup(fragment, "html.parser")
            if not any(isinstance(c, Tag) for c in soup.children):
                return

        text = self.document_text()
        offset = _insertion_offset(text, tag)
        self._document = text[:offset] + body + text[offset:]
        self._soup = None

    def bind(self, func) -> Callable:
        """Register a function so that clients can call it via ``k.rpc``.

        The function is called with the arguments sent by the client,
        restored from their pickles (a value that could not be restored
        arrives as a ``Placeholder``); inside it, ``k.rpc`` targets the
        client that made the call::

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
        The call is sent to the client's open WebSocket at once, or held
        in the queue and replayed when the client (re)connects. Requires a
        running event loop.
        """
        call_id = next(self._next_call_id)
        call = {
            "type": "call",
            "id": call_id,
            "method": method,
            "args": list(args),
            "kwargs": kwargs,
        }
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

    async def _rpc_ws(self, request: web.Request) -> web.WebSocketResponse:
        """Handle a client's WebSocket connection (GET /__kopis__/rpc).

        One connection per browser tab, bidirectional: ``call`` and
        ``result`` messages travel both ways as JSON. On (re)connection,
        every call still awaiting its result is replayed, so a dropped
        connection loses no work; the client skips call ids it already
        ran. Results come back as ``result`` messages.
        """
        session = await get_session(request)
        client_id = session.get("client_id")
        if client_id is None:
            # A brand-new session cannot be established here: the
            # connection's headers go out before the session middleware
            # could set the cookie. The document request always runs
            # first and does that.
            raise web.HTTPBadRequest(text="no session; load the document first")
        self._clients[client_id] = time.time()

        ws = web.WebSocketResponse(heartbeat=20)
        await ws.prepare(request)
        stream = _Stream(ws)
        old = self._streams.get(client_id)
        self._streams[client_id] = stream
        if old is not None:
            old.close()
        for call in list(self._pending_calls.get(client_id, [])):
            stream.push(call)
        sender = asyncio.ensure_future(self._ws_send(stream))
        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    self._handle_message(client_id, msg.data)
        except Exception:  # noqa: BLE001, S110 - a dead connection just ends the stream
            # Pending calls stay queued and are replayed when the client
            # (re)connects.
            pass
        finally:
            if self._streams.get(client_id) is stream:
                del self._streams[client_id]
            sender.cancel()
            try:
                await sender
            except (Exception, asyncio.CancelledError):  # noqa: BLE001, S110
                pass
        return ws

    @staticmethod
    async def _ws_send(stream: _Stream) -> None:
        """Send queued messages to the client until the connection ends."""
        try:
            while True:
                message = await stream.queue.get()
                if message is None:
                    return
                await stream.ws.send_str(encode(message))
        except Exception:  # noqa: BLE001, S110 - a dead connection just ends the sender
            # Queued calls remain pending and are replayed on reconnect.
            pass

    def _handle_message(self, client_id: str, text: str) -> None:
        """Dispatch a message received from a client."""
        try:
            msg = decode(text)
        except Exception:  # noqa: BLE001 - a bad message simply cannot be routed
            return
        if not isinstance(msg, dict):
            return
        if msg.get("type") == "call":
            asyncio.ensure_future(self._run_client_call(client_id, msg))
        elif msg.get("type") == "result":
            self._resolve_result(client_id, msg)

    async def _run_client_call(self, client_id: str, msg: dict) -> None:
        """Run a server function called by a client and send the result."""
        method = msg.get("method")
        args = msg.get("args", [])
        kwargs = msg.get("kwargs", {})
        payload: dict = {"type": "result", "id": msg.get("id")}
        func = self._bound.get(method)
        if func is None:
            payload["error"] = {
                "type": "NameError",
                "message": f"no function {method!r} bound on the server",
            }
        elif not isinstance(args, list) or not isinstance(kwargs, dict):
            payload["error"] = {
                "type": "TypeError",
                "message": "bad RPC call: args must be a list, kwargs a dict",
            }
        else:
            token = self._current_client.set(client_id)
            try:
                try:
                    result = func(*args, **kwargs)
                    if inspect.iscoroutine(result):
                        result = await result
                    payload["result"] = result
                except Exception as exc:  # noqa: BLE001 - report any failure to the client
                    payload["error"] = {
                        "type": type(exc).__name__,
                        "message": str(exc),
                    }
            finally:
                self._current_client.reset(token)
        self._send_to(client_id, payload)

    def _send_to(self, client_id: str, message: dict) -> None:
        """Queue a message for the client, if it is connected."""
        stream = self._streams.get(client_id)
        if stream is not None:
            stream.push(message)

    def _resolve_result(self, client_id: str, msg: dict) -> None:
        """Resolve the future of a client call from its result.

        Duplicates (a lost round trip) are ignored, so the client can
        safely re-send results.
        """
        call_id = msg.get("id")
        future = self._pending_results.pop(call_id, None)
        if future is None or future.done():
            return
        calls = self._pending_calls.get(client_id)
        if calls is not None:
            calls = [c for c in calls if c.get("id") != call_id]
            if calls:
                self._pending_calls[client_id] = calls
            else:
                del self._pending_calls[client_id]
        if "error" in msg:
            err = msg["error"]
            future.set_exception(RpcError(err.get("type", "Error"), err.get("message", "")))
        else:
            future.set_result(msg.get("result"))

    def _setup_brython(self) -> None:
        """Set up the app to run client-side code with Brython.

        Serves the JavaScript files of the installed ``brython`` package
        at ``/brython.js`` and ``/brython_stdlib.js``, serves the whole
        ``kopis`` package at the URLs Brython's import system expects
        (so e.g. ``from kopis import ...`` in app code resolves),
        initializes a default document with the Brython scripts in its
        ``<head>``, and attaches the running script (the app) to the
        document as a Brython script, so the same application code runs
        in the browser under Brython. The package's ``__init__``
        differentiates the sides, so ``import kopis`` in browser code
        picks the client side.
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
        # expects, so e.g. ``from kopis import Kopis`` in app code
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

        # The real (source) view is used for the framework's own setup;
        # the ``k.document`` property is a no-op in brython mode because
        # the document is built in the browser.
        doc = Document(self)

        with doc["head"] as el:
            el.append(
                '<meta name="viewport" content="width=device-width, initial-scale=1">'
            )
            el.append(
                f'<script type="text/javascript" src="{brython_js.name}"></script>'
            )
            el.append(
                f'<script type="text/javascript" src="{brython_stdlib_js.name}"></script>'
            )

        # Attach the running script (the app) as a Brython script, so the
        # same application code runs in the browser under Brython.
        entry = _entry_script()
        if entry is not None and entry.is_file():
            with doc["body"] as el:
                el.append(f'<script type="text/python" src="/{entry.name}"></script>')

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
