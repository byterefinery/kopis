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
from collections.abc import Callable
from inspect import iscoroutine
from pathlib import Path
from typing import Any

from browser import DOMNode, aio, document, html, window, websocket

from ..common import (
    Client,
    KopisBase,
    RPCHandle,
    RpcError,
    SharedSignal,
    WS_PATH,
    decode,
    encode,
)
from ..common.handle import _HandleAttr
from ..common.magic import _on_decorator
from .dom import _Window
from .for_ import For
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
        self,
        root: str | Path | None = None,
        use: str | list[str] | tuple[str, ...] | None = ("brython"),
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
        self._window_view: _Window | None = None  # stand-in of the window
        self._ws: Any = None
        self._open = False
        self._closed_by_user = False
        self._connect()

    @property
    def document(self) -> DOMNode:
        """The browser document (the live DOM; the brython
        ``browser.document`` object)."""
        return document

    @property
    def window(self) -> _Window:
        """The browser window (the brython ``browser.window``
        object), as a stand-in whose ``on<event>`` read is the
        decorator of the decorator form (``@k.window.onload`` is the
        same as ``k.window.onload = load``), and whose ``<id>`` read is
        the stand-in of the element with that id
        (``k.window.btn0.onclick`` is the element's ``on<event>``
        handler — see :mod:`kopis.client.dom`). Everything else
        delegates to the window itself.
        """
        view = self._window_view
        if view is None:
            view = _Window(window)
            self._window_view = view
        return view

    @property
    def html(self) -> Any:
        """The brython ``browser.html`` builder (the maker of the live
        DOM elements)."""
        return html

    def __getattr__(self, name: str) -> Any:
        """The window's ``on<event>`` handler property (``k.onload``):
        the handler, if one is set (``k.onload`` after
        ``k.onload = handler``), the decorator of the decorator form
        otherwise — or — otherwise — the standard HTML5 tag name
        (``k.li`` is ``k.html.li``, via the base class), or —
        otherwise — the short way for ``k.rpc.name``.

        Elements of the document are not looked up by id on the app:
        ``k["btn0"]`` (``k.document["btn0"]``), ``k.window.btn0`` (the
        element with id ``"btn0"``, as a stand-in of the element —
        ``k.window.btn0.onclick`` is its ``on<event>`` handler, see
        :mod:`kopis.client.dom`), and ``k.document.btn0`` give the
        element with that id. Any other name calls a function
        registered on the other side (the server), as in the base
        class.

        Only consulted for names that are not found the usual way, so
        the ``Kopis`` API (``register``, ``rpc``, ``document``, ...)
        is unaffected.
        """
        if name.startswith("_") or name == "rpc":
            raise AttributeError(name)
        if name.startswith("on") and len(name) > 2:
            try:
                handler = getattr(window, name)
            except AttributeError:
                handler = None
            if handler:  # unset handlers are falsy (brython's null)
                return handler
            # Not set: the decorator of the decorator form, which binds
            # the window's on<event> handler property for real.
            return _on_decorator(window, name[2:])
        return super().__getattr__(name)

    def _handle_getattr(self, handle: RPCHandle, name: str) -> Any:
        """The result of ``handle.<name>``.

        For a handle this tab owns, the attribute is read at once: a
        value for a data attribute, a call stand-in for a method. For
        a remote handle, reading cannot block the browser's single
        thread, so a call stand-in is returned at once: await it to
        read the attribute, or call it to invoke a method.
        """
        if handle._owner_side == self.side and handle._owner_id == self._client_id:
            return self._handle_op(handle, "getattr", name)
        return _HandleAttr(handle, name)

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

    def for_(self, list_fn: Callable[[], Any]) -> For:
        """A client-side :class:`~kopis.client.for_.For` loop of the
        application (the app's way to make one — see the class for the
        loop's behaviour)."""
        return For(list_fn)

    def run(self, host: str = "0.0.0.0", port: int = 5000) -> None:
        """No-op on the client: the web server runs on the server side."""

    def _start_startup_hook(self, func: Callable[..., Any]) -> None:
        """Start a startup hook of the app (an element of
        ``k.on_startup``) at once: the client's startup is the app code
        itself (Brython runs it in the browser on load), so the hook
        starts when it is added — a coroutine hook is started with
        ``aio.run``."""
        result = func(self)
        if iscoroutine(result):
            aio.run(result)

    @property
    def clients(self) -> list[Client]:
        """Stand-in on the client: a client has no clients connected
        to it (only the server routes calls between clients), so the
        list is empty. Its only peer is the server — call it with
        ``k.rpc.<name>(...)`` (the short way ``k.<name>(...)``).
        """
        return []

    def close(self) -> None:
        """Close the connection to the server (without reconnecting)."""
        self._closed_by_user = True
        if self._ws is not None:
            self._ws.close()

    def call(self, client_id: str, method: str, *args: object, **kwargs: object) -> Any:
        """Stand-in on the client: only the server routes calls to
        clients, so there is no one here to call. The client's only
        peer is the server — call it with ``k.rpc.<name>(...)`` (the
        short way ``k.<name>(...)``).
        """
        raise RuntimeError(
            "k.call can only be used on the server side (only the server "
            "routes calls to clients); on the client, call the server "
            "with k.rpc.<name>(...)"
        )

    async def _sync_shared_signal(self, shared: SharedSignal, value: Any) -> None:
        """Send a change of a shared signal's value to the server (whose
        copy of the value is the shared one — it applies it, and pushes
        it to the other clients), and then apply it to this client's
        copy of the value (the observers of it run, and its
        ``on_change`` callback, if any, is called) — after the server's
        result, so a re-read of the value never fetches a value the
        server has not applied yet.
        """
        await self._rpc_call(shared._setter_name, (value,), {})
        result = shared._signal._setter(value)
        if iscoroutine(result):
            await result

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
            print("kopis: websocket opened")
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
                payload.update(await self._dispatch_op(msg))
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

    async def _dispatch_op(self, msg: dict[str, Any]) -> dict[str, Any]:
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
            if iscoroutine(result):
                result = await result
                return {"result": result, "awaited": True}
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
        the op is applied at once: a sync operation returns its value,
        and a coroutine method returns its coroutine (await it).
        Otherwise the op is sent to the server — which owns the
        object, or relays the op to the tab that does — and a future
        is returned, settled by its ``result`` — or with an
        :class:`~kopis.common.RpcError` if the owner could not perform
        the op: the browser is a single thread, so the call cannot
        block. If a value in the op cannot be serialized, the op
        raises instead of being sent.
        """
        if kwargs is None:
            kwargs = {}
        if handle._owner_side == self.side and handle._owner_id == self._client_id:
            return self._apply_op(handle, op, name, args, kwargs)
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
