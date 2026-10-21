"""Client-side (Brython) Kopis: RPC to the server.

A much simpler class than the server-side ``Kopis``: it has no document,
root directory, or web app. It only provides :meth:`bind` (register a
local function so the server can call it) and the :attr:`rpc` proxy
(call a function the server registered with ``@k.bind``).

All HTTP goes through ``browser.aio`` and the browser's implicit event
loop drives everything; ``aio.run`` starts a coroutine without blocking.
"""

import inspect
import platform
from collections.abc import Callable
from typing import Any

from .serialize import RpcError, decode, encode

if platform.python_implementation() != 'Brython':
    # Server: `aio` is Brython-only; a stand-in for type checkers.
    from unittest.mock import MagicMock

    aio = MagicMock()
else:
    from browser import aio  # ty: ignore[unresolved-import]

RPC_URL = "/__kopis__/rpc"
POLL_URL = "/__kopis__/rpc/poll"
_POLL_INTERVAL = 0.5
_JSON = {"Content-Type": "application/json"}


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

    A background task polls the server for calls to the functions
    registered with :meth:`bind` and delivers their results back.
    """

    def __init__(self, use: str | None = None) -> None:
        if use not in (None, "brython"):
            raise ValueError(f"unknown value for use: {use!r}")
        self._bound: dict[str, Callable[..., Any]] = {}
        self._results: list[dict] = []
        self.rpc = _Rpc(self)
        aio.run(self._poll())

    def bind(self, func) -> Callable[..., Any]:
        """Register a function so the server can call it by name."""
        self._bound[func.__name__] = func
        return func

    async def _poll(self) -> None:
        """Poll the server for calls to functions registered with :meth:`bind`."""
        while True:
            try:
                body = encode({"results": self._results})
                req = await aio.post(POLL_URL, data=body, headers=_JSON)
                self._results = []
                for call in decode(req.data).get("calls", []):
                    aio.run(self._run_call(call))
            except Exception as exc:  # noqa: BLE001 - keep polling even if a round trip fails
                print("kopis: rpc poll failed:", exc)
            await aio.sleep(_POLL_INTERVAL)

    async def _run_call(self, call: dict) -> None:
        bound = self._bound.get(call.get("method"))
        if bound is None:
            self._results.append(
                {
                    "id": call["id"],
                    "error": {
                        "type": "NameError",
                        "message": f"no function {call.get('method')!r} bound on the client",
                    },
                }
            )
            return
        try:
            result = bound(*call.get("args", []), **call.get("kwargs", {}))
            if inspect.iscoroutine(result):
                result = await result
            self._results.append({"id": call["id"], "result": result})
        except Exception as exc:  # noqa: BLE001 - report any failure to the server
            self._results.append(
                {
                    "id": call["id"],
                    "error": {"type": type(exc).__name__, "message": str(exc)},
                }
            )
