"""Client-side (Brython) Kopis: RPC to the server.

A much simpler class than the server-side ``Kopis``: it has no document,
root directory, or web app. It only provides :meth:`bind` (register a
local function so the server can call it) and the :attr:`rpc` proxy
(call a function the server registered with ``@k.bind``).

Calls from the server to functions registered with :meth:`bind` arrive
over a Server-Sent Events stream (``EventSource`` on
``/__kopis__/rpc/events``); their results are posted back to the server
(``/__kopis__/rpc/results``) as soon as they are ready. All HTTP goes
through ``browser.aio`` and the browser's implicit event loop drives
everything; ``aio.run`` starts a coroutine without blocking.
"""

import inspect
import platform
from collections.abc import Callable
from typing import Any

from .serialize import RpcError, decode, encode

if platform.python_implementation() != 'Brython':
    # Server: `aio` and `window` are Brython-only; stand-ins for type checkers.
    from unittest.mock import MagicMock

    aio = MagicMock()
    window = MagicMock()
else:
    from browser import aio, window  # ty: ignore[unresolved-import]

RPC_URL = "/__kopis__/rpc"
EVENTS_URL = "/__kopis__/rpc/events"
RESULTS_URL = "/__kopis__/rpc/results"
_JSON = {"Content-Type": "application/json"}
_RETRY_DELAY = 1.0  # pause before retrying a failed results POST
_DONE_CAP = 1000  # completed calls remembered, to deduplicate replayed calls


class _Rpc:
    """Proxy for ``k.rpc``: ``k.rpc.name(args)`` calls the server's function."""

    def __init__(self, owner: Kopis) -> None:
        self._owner = owner

    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)

        async def call(*args: object, **kwargs: object) -> object:
            body = encode({"method": name, "args": list(args), "kwargs": kwargs})
            req = await aio.post(RPC_URL, data=body, headers=_JSON)
            msg = decode(req.data)
            if "error" in msg:
                err = msg["error"]
                raise RpcError(err.get("type", "Error"), err.get("message", ""))
            return msg["result"]

        return call


class Kopis:
    """The client half of a kopis RPC pair.

    Instantiate it in client code::

        from kopis import Kopis
        k = Kopis()

        @k.bind
        async def client_fn(x): ...         # callable from the server

        result = await k.rpc.server_fn(x)   # calls a server function

    Calls to the functions registered with :meth:`bind` arrive over a
    Server-Sent Events stream; their results are posted back to the server
    as soon as they are ready.
    """

    def __init__(self, use: str | None = None) -> None:
        if use not in (None, "brython"):
            raise ValueError(f"unknown value for use: {use!r}")
        self._bound: dict[str, Callable[..., Any]] = {}
        self._results: list[dict] = []  # results not yet sent to the server
        self._done: dict[int, dict] = {}  # completed call id -> result payload
        self._sending = False
        self.rpc = _Rpc(self)
        # `.new` calls the JS constructor with the `new` operator.
        self._source = window.EventSource.new(EVENTS_URL)
        self._source.bind("call", self._on_call)
        self._source.bind("error", self._on_error)

    def bind(self, func) -> Callable[..., Any]:
        """Register a function so the server can call it by name."""
        self._bound[func.__name__] = func
        return func

    def close(self) -> None:
        """Close the event stream to the server."""
        self._source.close()

    def _on_call(self, event: Any) -> None:
        """Handle a ``call`` event pushed by the server."""
        try:
            call = decode(event.data)
        except Exception:  # noqa: BLE001 - a bad event must not kill the stream
            return
        done = self._done.get(call.get("id"))
        if done is None:
            aio.run(self._run_call(call))
        else:
            # Duplicate delivery: the server replays calls until their result
            # is received, so a reconnect can re-send one we already ran.
            # Re-send the stored result instead of running it again.
            self._results.append(done)
        aio.run(self._flush_results())

    def _on_error(self, event: Any) -> None:
        # EventSource reconnects on its own; the server replays any calls
        # still awaiting a result, so no call is lost.
        print("kopis: event stream error, reconnecting")

    async def _flush_results(self) -> None:
        """Post pending results to the server.

        One flush runs at a time; concurrent completions append to
        ``self._results`` and are picked up by the running loop.
        """
        if self._sending:
            return
        self._sending = True
        try:
            while self._results:
                n = len(self._results)
                body = encode({"results": self._results[:n]})
                try:
                    await aio.post(RESULTS_URL, data=body, headers=_JSON)
                except Exception as exc:  # noqa: BLE001 - retry until it goes through
                    print("kopis: sending results failed:", exc)
                    await aio.sleep(_RETRY_DELAY)
                    continue
                del self._results[:n]
        finally:
            self._sending = False
            if self._results:
                aio.run(self._flush_results())

    async def _run_call(self, call: dict) -> None:
        bound = self._bound.get(call.get("method"))
        if bound is None:
            payload = {
                "id": call["id"],
                "error": {
                    "type": "NameError",
                    "message": f"no function {call.get('method')!r} bound on the client",
                },
            }
        else:
            try:
                result = bound(*call.get("args", []), **call.get("kwargs", {}))
                if inspect.iscoroutine(result):
                    result = await result
                payload = {"id": call["id"], "result": result}
            except Exception as exc:  # noqa: BLE001 - report any failure to the server
                payload = {
                    "id": call["id"],
                    "error": {"type": type(exc).__name__, "message": str(exc)},
                }
        self._done[call["id"]] = payload
        while len(self._done) > _DONE_CAP:
            del self._done[next(iter(self._done))]
        self._results.append(payload)
        aio.run(self._flush_results())
