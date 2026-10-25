"""The client-side ``Kopis`` application (Brython, in the browser).

No web server and no root directory: ``k.run()`` and
``k.add_static_file()`` are no-ops, and ``k.document`` is the browser
document itself (the live DOM, the brython ``browser.document``). The RPC client half lives here: calls and results
travel both ways over a single WebSocket connection per browser tab
(``/__kopis__/rpc``), re-opened automatically on disconnect; the calls
and ops in flight at the drop are re-sent on reconnect, and the server
runs each id at most once, so a dropped connection loses no work. The
browser's implicit event loop drives everything; ``aio.run`` starts a
coroutine without blocking.
"""

import itertools
import json
import uuid
from pathlib import Path
from typing import Any

from browser import DOMNode, aio, document, window, websocket

from ..common import KopisBase, RPCHandle, RpcError, WS_PATH, decode, encode
from .parser import parse_html

__all__ = ["Kopis"]

_RETRY_DELAY = 1.0  # pause before reopening a dropped connection
_DONE_CAP = 1000  # completed calls remembered, to deduplicate replayed calls


def _client_id() -> str:
    """A random identity of this tab (fresh on every page load).

    All tabs of a browser share the same session cookie, so a
    cookie-derived identity would make the tabs collide on the server;
    each tab therefore announces its own id with the WebSocket URL.
    """
    return uuid.uuid4().hex


def _ws_url(client_id: str) -> str:
    """The WebSocket URL of the server, derived from the page URL,
    carrying the tab's ``client_id``."""
    url = str(window.location.href)
    if url.startswith("http"):
        url = url.replace("http", "ws", 1)
    return url.rstrip("/") + WS_PATH + f"?client_id={client_id}"


class Kopis(KopisBase):
    """A kopis application, client side.

    Instantiate it in app code (the same code runs on the server, where
    :meth:`run` starts the web server, and in the browser, where it is a
    no-op). Values passed between the sides are pickled, so objects are
    restored on the other end as long as their type exists there. A value
    that cannot be pickled does not travel: sending it raises, and the
    developer wraps it in an explicit :class:`~kopis.common.RPCHandle`
    with ``k.get_handle`` instead — the live object stays alive on its
    side, and the other side operates on it through the handle::

        from kopis import Kopis
        k = Kopis()

        @k.rpc.register
        async def client_fn(x): ...         # callable from the server

        result = await k.rpc.server_fn(x)   # calls a server function

    Calls and results travel both ways over a single WebSocket connection
    per tab; when the connection drops, it is re-opened automatically
    and the calls in flight at the drop survive it: they are re-sent
    on reconnect (the server runs each id at most once, so nothing
    is done twice or lost).
    """

    side = "client"

    def __init__(
        self, root: str | Path | None = None, use: str | None = "brython"
    ) -> None:
        super().__init__(use)
        self._pending: dict[int, Any] = {}  # call id -> future of a client call
        self._pending_calls: dict[
            int, dict[str, Any]
        ] = {}  # call id -> the message sent (re-sent on reconnect)
        self._done: dict[
            tuple[str, int], dict[str, Any]
        ] = {}  # (instance, call id) -> result
        self._next_id = itertools.count(1)
        self._client_id = _client_id()  # this tab's identity on the server
        self._owner_id = self._client_id  # this tab's identity in the handles it makes
        self._ws: Any = None
        self._open = False
        self._closed_by_user = False
        self._connect()

    @property
    def document(self) -> DOMNode:
        """The browser document (the live DOM; the brython
        ``browser.document`` object)."""
        return document

    def __getattr__(self, name: str) -> Any:
        """The element of the document with that id, or — if no element
        has that id — the short way for ``k.rpc.name``.

        ``k.btn0`` is the element with id ``"btn0"`` (the same as
        ``k["btn0"]`` / ``k.document["btn0"]``); if no element has that
        id, ``k.name`` calls a function registered on the other side
        (the server), as in the base class. The client is the side with
        the live DOM, so element ids take precedence over RPC names
        (the server has no live DOM and resolves every name to the RPC
        call, where it stays a stand-in no-op).

        Only consulted for names that are not found the usual way, so
        the ``Kopis`` API (``register``, ``rpc``, ``document``, ...)
        is unaffected.
        """
        if name.startswith("_") or name == "rpc":
            raise AttributeError(name)
        try:
            return self.document[name]
        except KeyError:
            return super().__getattr__(name)

    def add_static_file(self, path: str, file_path: str | Path) -> None:
        """No-op on the client: files are served by the server."""

    def parse_html(self, html_str: str) -> list[DOMNode]:
        """Parse an HTML fragment into brython ``browser.html`` elements:
        the list of the fragment's top-level elements, in order (possibly
        empty).

        Standard HTML markup only — see ``kopis.client.parser`` for the
        parser. (Appending a string with ``<=`` or ``attach`` —
        ``element <= html_str`` or ``element.attach(html_str)`` — parses
        the fragment first and appends its top-level nodes; see
        ``kopis.client.dom``.)
        """
        return parse_html(html_str)

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
        """Call a function registered on the server and await its result.

        Raises if a value in the call cannot be serialized: the call is
        not sent.
        """
        call_id = next(self._next_id)
        self._send(
            {
                "type": "call",
                "id": call_id,
                "method": name,
                "args": list(args),
                "kwargs": kwargs,
            }
        )
        fut = aio.Future()
        self._pending[call_id] = fut
        return await fut

    def _connect(self) -> None:
        """Open (re-open) the WebSocket connection to the server."""
        ws = websocket.WebSocket(_ws_url(self._client_id))
        self._ws = ws
        self._open = False

        # Event handlers check that their socket is still the current one:
        # a stale close event from an abandoned socket can arrive after a
        # newer socket has opened, and must not clobber its state.

        def on_open(*event: object) -> None:
            if self._ws is not ws:
                return
            self._open = True
            # Re-send the calls and ops still awaiting a result: what
            # was sent before the connection dropped, and what was
            # queued while it was down. The server runs each id at most
            # once, so re-sending is safe.
            for call_id in list(self._pending_calls):
                call = self._pending_calls[call_id]
                try:
                    ws.send(encode(call))
                except Exception as exc:  # noqa: BLE001 - a value could not be serialized
                    # A value in the call can no longer be serialized:
                    # fail it instead of re-sending it forever.
                    del self._pending_calls[call_id]
                    fut = self._pending.pop(call_id, None)
                    if fut is not None and not fut.done():
                        fut.set_exception(RpcError(type(exc).__name__, str(exc)))

        def on_message(event: Any) -> None:
            if self._ws is not ws:
                return
            self._handle_message(event)

        def on_close(*event: object) -> None:
            if self._ws is not ws:
                return
            self._open = False
            self._ws = None
            print(
                "kopis: connection closed (code:",
                getattr(event[0], "code", "?"),
                ")",
            )
            if self._closed_by_user:
                # A deliberate close: in-flight calls can no longer
                # complete.
                for fut in self._pending.values():
                    if not fut.done():
                        fut.set_exception(
                            RpcError("ConnectionError", "connection was closed")
                        )
                self._pending.clear()
                self._pending_calls.clear()
                return
            # A dropped connection loses no work: in-flight calls are
            # kept and re-sent on reconnect (the server runs each id at
            # most once).
            print("kopis: reconnecting")
            aio.run(self._reconnect())

        ws.bind("open", on_open)
        ws.bind("message", on_message)
        ws.bind("close", on_close)

    def _send(self, message: dict[str, Any]) -> None:
        """Encode a message and send it, if the connection is open.

        Calls and ops are remembered by id and re-sent on reconnect,
        so a dropped connection loses no work (the server runs each id
        at most once). Results need no replay: when the sender of the
        original call reconnects, it re-asks, and this side re-sends
        the stored result.

        Raises if a value in the message cannot be pickled: such a value
        does not travel — the developer wraps it in an explicit
        ``RPCHandle`` (``k.get_handle``) if it should.
        """
        text = encode(message)
        if message.get("type") in ("call", "op"):
            self._pending_calls[message["id"]] = message
        if self._open and self._ws is not None:
            try:
                self._ws.send(text)
            except Exception as exc:  # noqa: BLE001 - the socket is dying
                # The call or op is remembered, and re-sent on reconnect.
                print("kopis: send failed:", exc)

    def _handle_message(self, event: Any) -> None:
        """Handle a message received from the server."""
        try:
            msg = decode(str(event.data), self)
        except Exception as exc:  # noqa: BLE001 - a bad message must not kill the connection
            self._report_bad_message(str(event.data), exc)
            return
        if not isinstance(msg, dict):
            return
        if msg.get("type") in ("call", "op"):
            aio.run(self._run_request(msg))
        elif msg.get("type") == "result":
            call_id = msg.get("id")
            self._pending_calls.pop(call_id, None)
            fut = self._pending.pop(call_id, None)
            if fut is not None:
                self._settle_result(fut, msg)

    def _report_bad_message(self, text: str, exc: Exception) -> None:
        """Reply with the error to a message whose pickled values could
        not be restored on this side."""
        try:
            raw = json.loads(text)
        except Exception:  # noqa: BLE001 - not even a JSON message
            return
        if isinstance(raw, dict) and raw.get("type") in ("call", "op") and "id" in raw:
            self._send(
                {
                    "type": "result",
                    "id": raw["id"],
                    "error": {"type": type(exc).__name__, "message": str(exc)},
                }
            )

    async def _run_request(self, msg: dict[str, Any]) -> None:
        """Run a call or op sent by the server and send the result."""
        call_id = msg["id"]
        # Call ids restart after a server restart, so they are remembered
        # together with the server instance that issued them.
        key = (msg.get("instance", ""), call_id)
        done = self._done.get(key)
        if done is None:
            payload: dict[str, Any] = {"type": "result", "id": call_id}
            if msg.get("type") == "op":
                payload.update(self._dispatch_op(msg))
            else:
                payload.update(
                    await self._dispatch(
                        msg.get("method"), msg.get("args", []), msg.get("kwargs", {})
                    )
                )
            try:
                self._send(payload)
            except Exception as exc:  # noqa: BLE001 - the result cannot be serialized
                # Report the failure as the error of the call: the value
                # stays alive on this side.
                payload = {
                    "type": "result",
                    "id": call_id,
                    "error": {"type": type(exc).__name__, "message": str(exc)},
                }
                self._send(payload)
            self._done[key] = payload
            while len(self._done) > _DONE_CAP:
                del self._done[next(iter(self._done))]
        else:
            # Duplicate delivery: the server replays calls until its result
            # is received, so a reconnect can re-send one we already ran.
            # Re-send the stored result instead of running it again.
            self._send(done)

    def _dispatch_op(self, msg: dict[str, Any]) -> dict[str, Any]:
        """Run an op the server sent for a handle this side owns, and
        build the ``result`` or ``error`` part of its payload."""
        handle = msg.get("handle")
        if (
            not isinstance(handle, RPCHandle)
            or handle._owner_side != self.side
            or handle._owner_id != self._client_id
        ):
            return {
                "error": {
                    "type": "LookupError",
                    "message": f"op for a handle this client does not own: {handle!r}",
                }
            }
        try:
            result = self._apply_op(
                handle,
                msg.get("op", ""),
                msg.get("name"),
                msg.get("args", []),
                msg.get("kwargs", {}),
            )
            return {"result": result}
        except Exception as exc:  # noqa: BLE001 - the owner decides; report the failure
            return {"error": {"type": type(exc).__name__, "message": str(exc)}}

    def _handle_op(
        self,
        handle: RPCHandle,
        op: str,
        name: str | None = None,
        args: tuple[object, ...] = (),
        kwargs: dict[str, object] | None = None,
    ) -> Any:
        """Perform ``op`` of ``handle`` and return a future of its
        result.

        If the live object is in this tab (the client owns the handle),
        the op is applied locally, and the future is settled with the
        (live) result itself. Otherwise the op is sent to the server —
        which owns the object, or relays the op to the tab that does —
        and the future is settled by its ``result`` — or with an
        :class:`~kopis.common.RpcError` if the owner could not perform
        the op. If a value in the op cannot be serialized, the op
        raises instead of being sent.
        """
        if kwargs is None:
            kwargs = {}
        if handle._owner_side == self.side and handle._owner_id == self._client_id:
            fut = aio.Future()
            try:
                fut.set_result(self._apply_op(handle, op, name, args, kwargs))
            except Exception as exc:  # noqa: BLE001 - the owner decides; report the failure
                fut.set_exception(RpcError(type(exc).__name__, str(exc)))
            return fut
        call_id = next(self._next_id)
        self._send(
            {
                "type": "op",
                "id": call_id,
                "handle": handle,
                "op": op,
                "name": name,
                "args": list(args),
                "kwargs": kwargs,
            }
        )
        fut = aio.Future()
        self._pending[call_id] = fut
        return fut

    async def _reconnect(self) -> None:
        await aio.sleep(_RETRY_DELAY)
        if not self._closed_by_user:
            self._connect()
