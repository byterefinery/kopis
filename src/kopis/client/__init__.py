"""Kopis: pure-Python web development (client side).

This is the client-side half of the ``kopis`` package: it runs in the
browser under Brython. It shares its API with the server-side half (the
``kopis.server`` subpackage); only the implementation differs: no web
server, no root directory. ``k.run()`` and ``k.add_static_file()`` are
no-ops here; ``k.document`` is a live view of the browser document; and
``k.bind``/``k.rpc`` implement the RPC client half.

Calls and results travel both ways over a single WebSocket connection
per browser tab (``/__kopis__/rpc``): calls to functions registered with
:meth:`Kopis.bind` arrive as messages, and results — in either direction
— are sent as messages. The connection is re-opened automatically on
disconnect. The browser's implicit event loop drives everything;
``aio.run`` starts a coroutine without blocking.
"""

__all__ = [
    "Document",
    "Element",
    "Kopis",
    "Placeholder",
    "RpcError",
    "aio",
    "document",
    "javascript",
]

import itertools
import platform
from collections.abc import Callable
from typing import Any, Self

from ..common import KopisBase, Placeholder, RpcError, WS_PATH, decode, encode

if platform.python_implementation() == "Brython":
    # Client: `browser` and `javascript` are Brython built-in modules.
    from browser import aio, document, window, websocket
    import javascript
else:
    # Server: `aio`, `document`, `window`, `websocket`, and `javascript`
    # are Brython-only; stand-ins keep this subpackage importable under
    # CPython.
    from unittest.mock import MagicMock

    aio = MagicMock()
    document = MagicMock()
    window = MagicMock()
    websocket = MagicMock()
    javascript = MagicMock()


_RETRY_DELAY = 1.0  # pause before reopening a dropped connection
_DONE_CAP = 1000  # completed calls remembered, to deduplicate replayed calls


def _ws_url() -> str:
    """The WebSocket URL of the server, derived from the page URL."""
    url = str(window.location.href)
    if url.startswith("http"):
        url = url.replace("http", "ws", 1)
    return url.rstrip("/") + WS_PATH


class Element:
    """A reference to an element of the browser document.

    The unified document API works the same way as on the server:
    :meth:`append` adds HTML elements, ``<=`` adds content, and
    :meth:`addEventListener` attaches an event handler. Any other attribute is
    delegated to the underlying DOM element, so all DOM properties and
    methods (``id``, ``innerHTML``, ``value``, ...) work as-is.
    """

    def __init__(self, element: Any) -> None:
        self._element = element

    def append(self, *html: str) -> Element:
        """Append one or more HTML elements as children of this element.

        Each fragment is inserted as-is just before this element's end
        tag. Returns ``self`` so calls can be chained::

            k.document.body.append("<a/>").append("<b/>")
        """
        for fragment in html:
            fragment = fragment.strip()
            if not fragment:
                continue
            self._element.insertAdjacentHTML("beforeend", fragment)
        return self

    def addEventListener(self, event: str, handler: Callable) -> Any:
        """Add an event listener to this element (delegates to the DOM)."""
        return self._element.addEventListener(event, handler)

    def __le__(self, content: object) -> None:
        """Append ``content`` as a child of this element."""
        self._element <= content  # noqa: B015 (Brython's <= adds a child)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None

    def __getattr__(self, name: str) -> Any:
        # Only called when normal attribute lookup fails. Dunder lookups
        # (pickle, copy, introspection) must keep failing as usual, and
        # ``_element`` is guarded to avoid infinite recursion on a
        # half-initialized instance.
        if name == "_element" or (name.startswith("__") and name.endswith("__")):
            raise AttributeError(name)
        return getattr(self._element, name)


class Document:
    """A live view of the browser document.

    The unified document API works the same way as on the server: look up
    an element by tag name with either subscripting or attribute access,
    or by CSS selector with :meth:`querySelector`; both return an
    :class:`Element`::

        with k.document.body as el:
            el.append("<button id=...></button>")
        k.document.querySelector("#btn0").addEventListener("click", handler)
    """

    def __init__(self, document: Any) -> None:
        self._document = document

    def _element(self, name: str) -> Element:
        try:
            return Element(getattr(self._document, name))
        except AttributeError as exc:
            raise AttributeError(f"no <{name}> element in the document") from exc

    def querySelector(self, selector: str) -> Element | None:
        """Return the first element matching ``selector``, or ``None``."""
        element = self._document.querySelector(selector)
        if element is None:
            return None
        return Element(element)

    def __getitem__(self, name: str) -> Element:
        return self._element(name)

    def __getattr__(self, name: str) -> Element:
        # Only called when normal attribute lookup fails. Dunder lookups
        # (pickle, copy, introspection) must keep failing as usual, and
        # ``_document`` is guarded to avoid infinite recursion on a
        # half-initialized instance.
        if name == "_document" or (name.startswith("__") and name.endswith("__")):
            raise AttributeError(name)
        return self._element(name)

    def __le__(self, content: object) -> None:
        """Append ``content`` to the document (its body)."""
        self._document <= content  # noqa: B015 (Brython's <= adds to the document)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None


class Kopis(KopisBase):
    """A kopis application, client side.

    Instantiate it in app code (the same code runs on the server, where
    :meth:`run` starts the web server, and in the browser, where it is a
    no-op). Values passed between the sides are pickled, so objects are
    restored on the other end as long as their type exists there; anything
    else arrives as a :class:`Placeholder`::

        from kopis import Kopis
        k = Kopis()

        @k.bind
        async def client_fn(x): ...         # callable from the server

        result = await k.rpc.server_fn(x)   # calls a server function

    Calls and results travel both ways over a single WebSocket connection
    per tab; it is re-opened automatically when the connection drops.
    """

    side = "client"

    def __init__(self, root: object = None, use: str | None = "brython") -> None:
        super().__init__(use)
        self._pending: dict[int, Any] = {}  # call id -> future of a client call
        self._done: dict[tuple[str, int], dict] = {}  # (instance, call id) -> result
        self._outbox: list[dict] = []  # messages waiting for the connection
        self._next_id = itertools.count(1)
        self._ws: Any = None
        self._open = False
        self._closed_by_user = False
        self._connect()

    @property
    def document(self) -> Document:
        """A live view of the browser document."""
        return Document(document)

    def add_static_file(self, path: str, file_path: object) -> None:
        """No-op on the client: files are served by the server."""

    def run(self, host: str = "0.0.0.0", port: int = 5000) -> None:
        """No-op on the client: the web server runs on the server side."""

    def close(self) -> None:
        """Close the connection to the server (without reconnecting)."""
        self._closed_by_user = True
        if self._ws is not None:
            self._ws.close()

    async def _rpc_call(self, name: str, args: tuple, kwargs: dict) -> object:
        """Call a function bound on the server and await its result."""
        call_id = next(self._next_id)
        fut = aio.Future()
        self._pending[call_id] = fut
        self._send(
            {
                "type": "call",
                "id": call_id,
                "method": name,
                "args": list(args),
                "kwargs": kwargs,
            }
        )
        return await fut

    def _connect(self) -> None:
        """Open (re-open) the WebSocket connection to the server."""
        ws = websocket.WebSocket(_ws_url())
        self._ws = ws
        self._open = False

        # Event handlers check that their socket is still the current one:
        # a stale close event from an abandoned socket can arrive after a
        # newer socket has opened, and must not clobber its state.

        def on_open(*event: object) -> None:
            if self._ws is not ws:
                return
            self._open = True
            # Send anything that was queued while the connection was down.
            for message in self._outbox:
                ws.send(encode(message))
            self._outbox.clear()

        def on_message(event: Any) -> None:
            if self._ws is not ws:
                return
            self._handle_message(event)

        def on_close(*event: object) -> None:
            if self._ws is not ws:
                return
            self._open = False
            self._ws = None
            # Client calls still in flight can no longer receive their result.
            for fut in self._pending.values():
                fut.set_exception(
                    RpcError("ConnectionError", "connection to the server was lost")
                )
            self._pending.clear()
            if self._closed_by_user:
                return
            print("kopis: connection closed, reconnecting")
            aio.run(self._reconnect())

        ws.onopen = on_open
        ws.onmessage = on_message
        ws.onclose = on_close

    def _send(self, message: dict) -> None:
        """Send a message, or queue it until the connection is open again."""
        if self._open and self._ws is not None:
            try:
                self._ws.send(encode(message))
                return
            except Exception as exc:  # noqa: BLE001 - the socket is dying; queue it
                print("kopis: send failed:", exc)
        self._outbox.append(message)

    def _handle_message(self, event: Any) -> None:
        """Handle a message received from the server."""
        try:
            msg = decode(str(event.data))
        except Exception:  # noqa: BLE001 - a bad message must not kill the connection
            return
        if not isinstance(msg, dict):
            return
        if msg.get("type") == "call":
            aio.run(self._run_call(msg))
        elif msg.get("type") == "result":
            fut = self._pending.pop(msg.get("id"), None)
            if fut is not None:
                self._settle_result(fut, msg)

    async def _run_call(self, call: dict) -> None:
        """Run a client function called by the server and send the result."""
        call_id = call["id"]
        # Call ids restart after a server restart, so they are remembered
        # together with the server instance that issued them.
        key = (call.get("instance", ""), call_id)
        done = self._done.get(key)
        if done is None:
            payload: dict = {"type": "result", "id": call_id}
            payload.update(
                await self._dispatch(
                    call.get("method"), call.get("args", []), call.get("kwargs", {})
                )
            )
            self._done[key] = payload
            while len(self._done) > _DONE_CAP:
                del self._done[next(iter(self._done))]
        else:
            # Duplicate delivery: the server replays calls until their result
            # is received, so a reconnect can re-send one we already ran.
            # Re-send the stored result instead of running it again.
            payload = done
        self._send(payload)

    async def _reconnect(self) -> None:
        await aio.sleep(_RETRY_DELAY)
        if not self._closed_by_user:
            self._connect()
