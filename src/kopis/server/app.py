"""The server-side ``Kopis`` application.

A web application served from a root directory: files in the root
directory are served as static assets, and the ``document`` is served
at ``/``. The document is either an in-memory string assigned to
``k.document``, or the ``index.html`` file in the root directory (the
assigned string takes precedence); :meth:`Kopis.add_static_file` serves
files from anywhere on disk at a chosen URL.

The server never parses the document: in the brython way, the browser
parses the HTML it loads. (The client can parse fragments on demand with
``k.parse_html``; on the server that is a stand-in returning a
``browser.DOMNode``, since the server itself never parses HTML.)
``k.document`` on the server is therefore a stand-in of the
brython ``browser.document`` object (a
:class:`~kopis.server.browser.DOMNode` of the raw HTML string served at
``/``): unified code works on it identically to the live DOM in the
browser — ``document <= ...``, ``document.createElement``,
``bind``, and friends all succeed — but nothing is rendered or fired:
the browser does all that by running the same code under Brython.

By default (``use="brython"``), the app runs client-side Python code
with `Brython <https://brython.info>`_: the Brython scripts and the
modules of the ``kopis`` package are served, a default document is
created when the root has no ``index.html`` and ``k.document`` is never
assigned, and the running script (the app) is attached to the document
as a Brython script, so the same application code runs in the browser
under Brython.

RPC: register a function with ``@k.rpc.register`` (the short way is
``@k.register``) to make it callable from the other side as
``await k.rpc.<name>(...)`` (the short way is ``await k.<name>(...)``).
Inside a registered function, ``k.rpc`` targets the client that made
the call; calls can also be sent explicitly with ``k.call(client_id,
...)``. Calls and results travel both
ways over a single WebSocket connection per client
(``/__kopis__/rpc``), which the client re-opens on disconnect. Each
tab announces its own random ``client_id`` in the WebSocket URL (all
tabs of a browser share the same session cookie, which would make them
collide; the cookie identity remains as a fallback for clients that
don't announce one), and all exchanged data is JSON: the values of
``args``, ``kwargs``, and ``result`` are pickled
Python objects (base64-encoded in the JSON), and a value that cannot be
(de)serialized arrives as a ``Placeholder`` carrying the string of the
exception.
"""

import asyncio
import contextvars
import hashlib
import itertools
import sys
import uuid
from pathlib import Path
from typing import Any

from aiohttp import web
from aiohttp_session import Session, get_session, setup
from aiohttp_session.cookie_storage import EncryptedCookieStorage

from ..common import KopisBase, WS_PATH, decode, encode
from . import browser

__all__ = ["Kopis"]


def _entry_script() -> Path | None:
    """The path of the running script, if determinable from ``sys.argv[0]``."""
    argv0 = sys.argv[0] if sys.argv else ""
    if argv0 and Path(argv0).is_file():
        return Path(argv0).resolve()
    return None


class _Stream:
    """An open WebSocket connection of a client, and the queue of messages
    to send on it.

    The queue is a delivery mirror of the durable per-client call queue:
    a call is queued here as soon as it is queued, and is replayed from
    the durable queue whenever the client (re)connects. ``close()`` wakes
    the sender loop of a stream that was replaced by a newer connection.
    """

    def __init__(self, ws: web.WebSocketResponse) -> None:
        self.ws = ws
        self.queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()

    def push(self, message: dict[str, Any]) -> None:
        """Queue a message for delivery to the client."""
        self.queue.put_nowait(message)

    def close(self) -> None:
        """Wake the sender loop so it can stop (a sentinel is enqueued)."""
        self.queue.put_nowait(None)


class Kopis(KopisBase):
    """A web application served from a root directory.

    The root directory defaults to the directory of the running script.
    See the module docstring for the semantics of the document and of
    RPC.
    """

    side = "server"

    #: The document created when the root has no ``index.html`` and
    #: ``k.document`` is never assigned (brython mode).
    _DEFAULT_DOCUMENT = """\
<html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
    </head>

    <body>
    </body>
</html>
"""

    def __init__(
        self,
        root: str | Path | None = None,
        use: str | None = "brython",
    ) -> None:
        super().__init__(use)

        if root is not None:
            self.root = Path(root).resolve()
        else:
            entry = _entry_script()
            self.root = entry.parent if entry is not None else Path.cwd()

        self._entry = _entry_script()
        self._brython = self.use == "brython"
        self._document: str | None = None  # the HTML assigned to k.document
        self._served: str | None = None  # cache of the document served at /

        # RPC state.
        self._instance = uuid.uuid4().hex  # distinguishes call ids across restarts
        self._pending_calls: dict[str, list[dict[str, Any]]] = {}
        self._pending_results: dict[int, asyncio.Future] = {}
        self._streams: dict[str, _Stream] = {}
        self._next_call_id = itertools.count(1)
        self._current_client: contextvars.ContextVar[str | None] = (
            contextvars.ContextVar("kopis_current_client", default=None)
        )

        self.app = web.Application()
        # Sessions (cookie-based) identify which client a request comes
        # from. The key is derived from the root directory, so it survives
        # server restarts: a client that reconnects after a restart is
        # still recognized, and calls queued for it are replayed.
        session_key = hashlib.sha256(str(self.root).encode()).digest()
        setup(
            self.app, EncryptedCookieStorage(session_key, cookie_name="kopis_session")
        )

        # Registered before the static route so that it takes precedence
        # on ``/`` and on ``/__kopis__/rpc``.
        self.app.router.add_get("/", self._serve_document)
        self.app.router.add_get(WS_PATH, self._rpc_ws)

        self.app.router.add_static("/", self.root, follow_symlinks=True)

        if self._brython:
            self._setup_brython()

        self._register_document()

    # -- document ------------------------------------------------------------

    @property
    def document(self) -> browser.DOMNode:
        """The document served at ``/`` (a stand-in of the brython
        ``browser.document`` object; there is no live DOM on the server,
        so DOM operations on it succeed but do nothing)."""
        return browser.document

    @document.setter
    def document(self, value: str) -> None:
        self._document = value
        self._served = None
        self._register_document()

    def _register_document(self) -> None:
        """Register the served document as ``document`` of the server
        stand-ins (the brython ``browser.document`` object)."""
        try:
            browser.set_document(self._served_document())
        except FileNotFoundError:
            pass  # no document yet (nothing assigned, no index.html)

    def _source_html(self) -> str:
        """The HTML the document is built from: the string assigned to
        ``k.document``, else the root's ``index.html``, else (brython
        mode) the default document."""
        if self._document is not None:
            return self._document
        index = self.root / "index.html"
        if index.is_file():
            return index.read_text()
        if self._brython:
            return self._DEFAULT_DOCUMENT
        raise FileNotFoundError(index)

    def _served_document(self) -> str:
        """The document served at ``/`` (cached until changed)."""
        if self._served is None:
            html = self._source_html()
            self._served = self._annotate(html) if self._brython else html
        return self._served

    @staticmethod
    def _insert_before(html: str, close_tag: str, content: str) -> str:
        """Insert ``content`` just before the first ``close_tag``."""
        idx = html.lower().find(close_tag)
        if idx == -1:
            raise ValueError(f"no {close_tag} in the document")
        return html[:idx] + content + html[idx:]

    def _annotate(self, html: str) -> str:
        """Annotate ``html`` with the Brython scripts (in ``<head>``) and
        the app entry script (in ``<body>``), wrapping a bare fragment
        in a full document when needed.

        The browser parses the served HTML and runs the app code under
        Brython on the live DOM it builds, so the served document must
        carry the scripts; the server itself never parses the document.
        """
        head_scripts = (
            '<script type="text/javascript" src="brython.js"></script>'
            '<script type="text/javascript" src="brython_stdlib.js"></script>'
        )
        body_scripts = ""
        entry = self._entry
        if entry is not None and entry.is_file():
            body_scripts = f'<script type="text/python" src="/{entry.name}"></script>'
        if "<html" not in html.lower():
            return (
                "<html><head>"
                f"{head_scripts}"
                f"</head><body>{html}{body_scripts}</body></html>"
            )
        if "</head>" not in html.lower():
            start = html.lower().find("<html")
            end = html.find(">", start)
            if end == -1:
                raise ValueError("no <html> start tag in the document")
            html = html[: end + 1] + f"<head>{head_scripts}</head>" + html[end + 1 :]
        else:
            html = self._insert_before(html, "</head>", head_scripts)
        if body_scripts:
            if "</body>" not in html.lower():
                html = html.rstrip() + f"<body>{body_scripts}</body>"
            else:
                html = self._insert_before(html, "</body>", body_scripts)
        return html

    def _setup_brython(self) -> None:
        """Set up the app to run client-side code with Brython.

        Serves the JavaScript files of the installed ``brython`` package
        at ``/brython.js`` and ``/brython_stdlib.js``, and serves the
        whole ``kopis`` package at the URLs Brython's import system
        expects (so e.g. ``from kopis import ...`` in app code
        resolves). The served document is annotated with the Brython
        scripts and the app entry script by :meth:`_annotate`.
        """
        import brython  # Optional dependency, required only for use="brython".

        # Serve the brython scripts from where the package installed them.
        brython_path = Path(brython.__file__).parent
        self.add_static_file("/brython.js", brython_path / "data" / "brython.js")
        self.add_static_file(
            "/brython_stdlib.js", brython_path / "data" / "brython_stdlib.js"
        )

        # Serve the `kopis` package at the URLs Brython's import system
        # expects, so e.g. ``from kopis import Kopis`` in app code
        # resolves. Every ``.py`` file in the package is served at its
        # corresponding URL, so any module the client imports exists.
        # This file lives in ``kopis/server/``, so the package root is
        # one level up.
        kopis_path = Path(__file__).resolve().parent.parent
        for file in sorted(kopis_path.rglob("*.py")):
            url = "/kopis/" + file.relative_to(kopis_path).as_posix()
            self.add_static_file(url, file)

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

    def parse_html(self, html_str: str) -> list[browser.DOMNode]:
        """Parse an HTML fragment into elements (a stand-in).

        The server has no live DOM, so the fragment is not parsed: a list
        holding one stand-in ``browser.DOMNode`` is returned, and DOM
        operations on it succeed but do nothing — the browser parses the
        same fragment under Brython.
        """
        return [browser.DOMNode()]

    async def _serve_document(self, request: web.Request) -> web.Response:
        """Serve the document at ``/``.

        The browser parses the served HTML and, in brython mode, runs
        the same application code under Brython on the live DOM it
        builds; the server never parses the document itself. The
        session cookie also identifies the client that loads the
        document.
        """
        try:
            text = self._served_document()
        except FileNotFoundError:
            raise web.HTTPNotFound()

        session = await get_session(request)
        self._ensure_client_id(session)

        return web.Response(text=text, content_type="text/html")

    @staticmethod
    def _ensure_client_id(session: Session) -> str:
        """Return the client id stored in ``session``, creating one if needed."""
        client_id = session.get("client_id")
        if client_id is None:
            client_id = uuid.uuid4().hex
            session["client_id"] = client_id
        return client_id

    # -- RPC ----------------------------------------------------------------

    def call(
        self, client_id: str, method: str, *args: object, **kwargs: object
    ) -> asyncio.Future:
        """Queue a call to a function the client registered with
        :meth:`~kopis.common.KopisBase.register`.

        Returns a future that resolves with the client's return value, or
        raises :class:`~kopis.common.RpcError` if the call failed there.
        The call is sent to the client's open WebSocket at once, or held
        in the queue and replayed when the client (re)connects. Requires a
        running event loop.
        """
        call_id = next(self._next_call_id)
        call: dict[str, Any] = {
            "type": "call",
            "id": call_id,
            "instance": self._instance,
            "method": method,
            "args": list(args),
            "kwargs": kwargs,
        }
        self._pending_calls.setdefault(client_id, []).append(call)
        future = asyncio.get_running_loop().create_future()
        self._pending_results[call_id] = future
        self._send_to(client_id, call)
        return future

    async def _rpc_call(
        self, name: str, args: tuple[object, ...], kwargs: dict[str, object]
    ) -> object:
        """Call a client function on the client that is currently being served."""
        client_id = self._current_client.get()
        if client_id is None:
            raise RuntimeError(
                "k.rpc can only be used inside a function called by a client; "
                "use k.call(client_id, ...) to target a client explicitly"
            )
        return await self.call(client_id, name, *args, **kwargs)

    async def _rpc_ws(self, request: web.Request) -> web.WebSocketResponse:
        """Handle a client's WebSocket connection (GET /__kopis__/rpc).

        One connection per browser tab, bidirectional: ``call`` and
        ``result`` messages travel both ways as JSON. On (re)connection,
        every call still awaiting its result is replayed, so a dropped
        connection loses no work; the client skips call ids it already
        ran. Results come back as ``result`` messages.
        """
        session = await get_session(request)
        client_id = request.query.get("client_id")
        if client_id is None:
            # No announced id: fall back to the session cookie identity.
            client_id = session.get("client_id")
            if client_id is None:
                # Give the client a new identity. A successful upgrade (101)
                # cannot carry the session cookie, but this 400 can, so the
                # client's reconnect attempt right after it connects cleanly.
                self._ensure_client_id(session)
                raise web.HTTPBadRequest(text="no session yet; try again")

        ws = web.WebSocketResponse(heartbeat=20)
        await ws.prepare(request)
        stream = _Stream(ws)
        old = self._streams.get(client_id)
        self._streams[client_id] = stream
        if old is not None:
            old.close()
            try:
                await old.ws.close()
            except Exception:  # noqa: BLE001, S110 - the old socket is usually already dead
                pass
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
            except asyncio.CancelledError, Exception:  # noqa: BLE001, S110
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

    async def _run_client_call(self, client_id: str, msg: dict[str, Any]) -> None:
        """Run a server function called by a client and send the result."""
        payload: dict[str, Any] = {"type": "result", "id": msg.get("id")}
        token = self._current_client.set(client_id)
        try:
            payload.update(
                await self._dispatch(
                    msg.get("method"), msg.get("args", []), msg.get("kwargs", {})
                )
            )
        finally:
            self._current_client.reset(token)
        self._send_to(client_id, payload)

    def _send_to(self, client_id: str, message: dict[str, Any]) -> None:
        """Queue a message for the client, if it is connected."""
        stream = self._streams.get(client_id)
        if stream is not None:
            stream.push(message)

    def _resolve_result(self, client_id: str, msg: dict[str, Any]) -> None:
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
        self._settle_result(future, msg)

    def run(self, host: str = "0.0.0.0", port: int = 5000) -> None:
        web.run_app(self.app, host=host, port=port)
