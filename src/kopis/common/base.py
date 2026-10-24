"""``KopisBase`` — the part of ``Kopis`` shared by both sides.

The server-side ``Kopis`` (``kopis.server``) and the client-side
``Kopis`` (``kopis.client``) both inherit from :class:`KopisBase` and
implement its abstract methods. The base class implements everything
the two sides do the same way:

- validation of the ``use`` argument;
- :meth:`register` (the canonical way ``k.rpc.register``, and the
  short way ``k.register``), and the registry of the functions
  registered with it;
- the ``k.rpc`` proxy, which calls a function registered on the other
  side (the actual sending of the call is left to :meth:`_rpc_call`);
  ``k.name(...)`` is the short way for ``k.rpc.name(...)``;
- :meth:`_dispatch`, which runs a function called by the other side
  and builds the ``result`` or ``error`` part of its payload;
- :meth:`_settle_result`, which resolves the future of a pending call
  from its ``result`` message.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from inspect import iscoroutine
from pathlib import Path
from typing import Any

from .wire import RpcError

__all__ = ["KopisBase"]


class _Rpc:
    """Proxy for ``k.rpc``: ``k.rpc.name(args)`` calls a function
    registered on the other side.

    ``k.rpc.register`` is the canonical way to register a function so
    that the other side can call it; it delegates to the owner's
    :meth:`KopisBase.register` (the short way for which is
    ``k.register``).

    The proxy is identical on both sides; the actual sending of the
    call is done by :meth:`KopisBase._rpc_call`, which each side
    implements.
    """

    def __init__(self, owner: KopisBase) -> None:
        self._owner = owner

    @property
    def register(self) -> Callable[..., Any]:
        """Register a function so that the other side can call it.

        The owner's :meth:`KopisBase.register`; ``k.register`` is the
        short way for ``k.rpc.register``.
        """
        return self._owner.register

    def __getattr__(self, name: str) -> Callable[..., Any]:
        if name.startswith("_"):
            raise AttributeError(name)

        async def call(*args: object, **kwargs: object) -> object:
            return await self._owner._rpc_call(name, args, kwargs)

        return call


class KopisBase(ABC):
    """Base class of the unified ``Kopis`` application.

    The server-side and client-side ``Kopis`` classes both inherit from
    this class. It implements the parts of the unified API that are
    identical on both sides of the web stack (see the module docstring);
    the sides implement the platform-specific parts: the ``document``
    property, :meth:`run`, :meth:`add_static_file`, :meth:`parse_html`,
    and :meth:`_rpc_call`.
    """

    #: Name of this side of the wire, used in error messages.
    side: str

    def __init__(self, use: str | None = "brython") -> None:
        if use not in (None, "brython"):
            raise ValueError(f"unknown value for use: {use!r}")
        self.use = use
        self._bound: dict[str, Callable[..., Any]] = {}
        self.rpc = _Rpc(self)

    # -- unified API ------------------------------------------------------

    @property
    @abstractmethod
    def document(self) -> Any:
        """A live view of the document."""

    def register(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """Register a function so that the other side can call it via
        ``k.rpc`` (canonical way ``k.rpc.register``, short way
        ``k.register``)::

            @k.rpc.register
            async def add(x, y):
                return x + y
        """
        self._bound[func.__name__] = func  # ty: ignore[unresolved-attribute] - a named function is required
        return func

    def __getattr__(self, name: str) -> Callable[..., Any]:
        """The short way for ``k.rpc.name``: ``k.name(...)`` calls a
        function registered on the other side.

        Only consulted for names that are not found the usual way, so
        the ``Kopis`` API (``register``, ``rpc``, ``document``, ...)
        is unaffected.
        """
        if name.startswith("_") or name == "rpc":
            # ``rpc`` is the proxy itself; failing here (instead of
            # dereferencing ``self.rpc``) also breaks any recursion if
            # this is consulted before ``__init__`` has set it.
            raise AttributeError(name)
        return self.rpc.__getattr__(name)

    @abstractmethod
    def add_static_file(self, path: str, file_path: str | Path) -> None:
        """Serve a file at a URL (server side); no-op on the client side."""

    @abstractmethod
    def parse_html(self, html_str: str) -> list[Any]:
        """Parse an HTML fragment into brython elements: the list of the
        fragment's top-level elements, in order (possibly empty)."""

    @abstractmethod
    def run(self, host: str = "0.0.0.0", port: int = 5000) -> None:
        """Start the web server (server side); no-op on the client side."""

    # -- RPC ----------------------------------------------------------------

    @abstractmethod
    async def _rpc_call(
        self, name: str, args: tuple[object, ...], kwargs: dict[str, object]
    ) -> object:
        """Send a call to a function registered on the other side and
        await its result."""

    async def _dispatch(
        self, method: str | None, args: list[object], kwargs: dict[str, object]
    ) -> dict[str, Any]:
        """Run a function called by the other side and build the
        ``result`` or ``error`` part of its payload.

        ``method`` is the name of a function registered with
        :meth:`register` (or ``None`` if the call is malformed); ``args``
        and ``kwargs`` are the arguments sent by the other side,
        restored from their pickles.
        """
        func = self._bound.get(method) if isinstance(method, str) else None
        if func is None:
            return {
                "error": {
                    "type": "NameError",
                    "message": f"no function {method!r} registered on the {self.side}",
                }
            }
        if not isinstance(args, list) or not isinstance(kwargs, dict):
            return {
                "error": {
                    "type": "TypeError",
                    "message": "bad RPC call: args must be a list, kwargs a dict",
                }
            }
        try:
            result = func(*args, **kwargs)
            if iscoroutine(result):
                result = await result
            return {"result": result}
        except Exception as exc:  # noqa: BLE001 - report any failure to the other side
            return {"error": {"type": type(exc).__name__, "message": str(exc)}}

    def _settle_result(self, future: Any, msg: dict[str, Any]) -> None:
        """Resolve the future of a pending call from its ``result``
        message.

        ``future`` is an ``asyncio.Future`` on the server and an
        ``aio.Future`` on the client; both are resolved the same way.
        """
        if "error" in msg:
            err = msg["error"]
            future.set_exception(
                RpcError(err.get("type", "Error"), err.get("message", ""))
            )
        else:
            future.set_result(msg.get("result"))
