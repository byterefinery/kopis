"""The client-side ``Kopis`` application (Brython, in the browser).

No web server and no root directory: ``k.run()`` and
``k.add_static_file()`` are no-ops, and ``k.document`` is the browser
document itself (the live DOM, the brython ``browser.document``). The RPC client half lives here: calls and results
travel both ways over a single WebSocket connection per browser tab
(``/__kopis__/rpc``), re-opened automatically on disconnect. The
browser's implicit event loop drives everything; ``aio.run`` starts a
coroutine without blocking.
"""

import itertools
from pathlib import Path
from typing import Any

from ..common import KopisBase, RpcError, WS_PATH, decode, encode
from .brython import aio, browser_document, window, websocket

__all__ = ["Kopis"]

_RETRY_DELAY = 1.0  # pause before reopening a dropped connection
_DONE_CAP = 1000  # completed calls remembered, to deduplicate replayed calls


def _ws_url() -> str:
    """The WebSocket URL of the server, derived from the page URL."""
    url = str(window.location.href)
    if url.startswith("http"):
        url = url.replace("http", "ws", 1)
    return url.rstrip("/") + WS_PATH


class Kopis(KopisBase):
    """A kopis application, client side.

    Instantiate it in app code (the same code runs on the server, where
    :meth:`run` starts the web server, and in the browser, where it is a
    no-op). Values passed between the sides are pickled, so objects are
    restored on the other end as long as their type exists there; anything
    else arrives as a :class:`~kopis.common.Placeholder`::

        from kopis import Kopis
        k = Kopis()

        @k.rpc.register
        async def client_fn(x): ...         # callable from the server

        result = await k.rpc.server_fn(x)   # calls a server function

    Calls and results travel both ways over a single WebSocket connection
    per tab; it is re-opened automatically when the connection drops.
    """

    side = "client"

    def __init__(
        self, root: str | Path | None = None, use: str | None = "brython"
    ) -> None:
        super().__init__(use)
        self._pending: dict[int, Any] = {}  # call id -> future of a client call
        self._done: dict[
            tuple[str, int], dict[str, Any]
        ] = {}  # (instance, call id) -> result
        self._outbox: list[dict[str, Any]] = []  # messages waiting for the connection
        self._next_id = itertools.count(1)
        self._ws: Any = None
        self._open = False
        self._closed_by_user = False
        self._connect()

    @property
    def document(self) -> Any:
        """The browser document (the live DOM; the brython
        ``browser.document`` object)."""
        return browser_document

    def add_static_file(self, path: str, file_path: str | Path) -> None:
        """No-op on the client: files are served by the server."""

    def run(self, host: str = "0.0.0.0", port: int = 5000) -> None:
        """No-op on the client: the web server runs on the server side."""

    def close(self) -> None:
        """Close the connection to the server (without reconnecting)."""
        self._closed_by_user = True
        if self._ws is not None:
            self._ws.close()

    async def _rpc_call(
        self, name: str, args: tuple[object, ...], kwargs: dict[str, object]
    ) -> object:
        """Call a function registered on the server and await its result."""
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

        ws.bind("open", on_open)
        ws.bind("message", on_message)
        ws.bind("close", on_close)

    def _send(self, message: dict[str, Any]) -> None:
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

    async def _run_call(self, call: dict[str, Any]) -> None:
        """Run a client function called by the server and send the result."""
        call_id = call["id"]
        # Call ids restart after a server restart, so they are remembered
        # together with the server instance that issued them.
        key = (call.get("instance", ""), call_id)
        done = self._done.get(key)
        if done is None:
            payload: dict[str, Any] = {"type": "result", "id": call_id}
            payload.update(
                await self._dispatch(
                    call.get("method"), call.get("args", []), call.get("kwargs", {})
                )
            )
            self._done[key] = payload
            while len(self._done) > _DONE_CAP:
                del self._done[next(iter(self._done))]
        else:
            # Duplicate delivery: the server replays calls until its result
            # is received, so a reconnect can re-send one we already ran.
            # Re-send the stored result instead of running it again.
            payload = done
        self._send(payload)

    async def _reconnect(self) -> None:
        await aio.sleep(_RETRY_DELAY)
        if not self._closed_by_user:
            self._connect()
