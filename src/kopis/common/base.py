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
  ``k.name(...)`` is the short way for ``k.rpc.name(...)``, and
  ``k["id"]`` the short way for ``k.document["id"]`` (the element with
  that id);
- :meth:`_dispatch`, which runs a function called by the other side
  and builds the ``result`` or ``error`` part of its payload;
- :meth:`_settle_result`, which resolves the future of a pending call
  from its ``result`` message;
- the registry of live objects this side keeps for values wrapped in
  handles (:attr:`_handles`), and the ``RPCHandle``s that stand in for
  them on the other side (:meth:`handle`, :meth:`get_handle`,
  :meth:`_apply_op`).
"""

from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping, Sequence
from inspect import iscoroutine
from itertools import count
from pathlib import Path
from typing import Any

from .handle import RPCHandle
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
        # The live objects this side keeps for values it could not
        # serialize, and the handles that stand in for them on the
        # other side.
        self._handles: dict[int, Any] = {}
        self._next_handle_id = count(1)
        self._owner_id: str | None = (
            None  # this side's identity in the handles it makes
        )

    # -- unified API ------------------------------------------------------

    @property
    @abstractmethod
    def document(self) -> Any:
        """A live view of the document."""

    def __getitem__(self, key: object) -> Any:
        """The element of the document with that id: ``k["btn0"]`` is
        the same as ``k.document["btn0"]``.

        On the client (the live DOM) it is the element itself, and
        ``KeyError`` is raised if no element has that id, as in brython;
        on the server (no live DOM) it is a stand-in element, as with
        everything else on the document.
        """
        return self.document[key]

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

    def handle(self, value: object) -> RPCHandle:
        """Wrap ``value`` in an ``RPCHandle``: keep ``value`` alive on
        this side, and return the handle that stands in for it.

        This is the wrap behind :meth:`get_handle`. The live object
        stays in :attr:`_handles`, and the handle — which carries this
        side's identity — is what is sent to the other side.
        """
        handle_id = next(self._next_handle_id)
        self._handles[handle_id] = value
        try:
            true_repr = repr(value)
        except Exception as exc:  # noqa: BLE001 - the live repr is best effort
            true_repr = f"<unreprable {type(exc).__name__}>"
        handle = RPCHandle(handle_id, self.side, self._owner_id, true_repr)
        handle._kopis = self  # the handle is usable on this side at once
        return handle

    def get_handle(self, value: object) -> RPCHandle:
        """Get an ``RPCHandle`` to ``value``, to send to the other side.

        Works for any object — picklable or not: the live object stays
        on this side, and operations on the handle on the other side
        come back here. When the handle comes back to this side (as an
        argument or result of a call or op), it is unwrapped: this
        side passes the live ``value`` instead, since the object is
        already here.
        """
        return self.handle(value)

    @abstractmethod
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

        If this side owns the live object, the op is applied here, and
        the future is settled with the (live) result itself; otherwise
        the op is sent to the owner, and the future is settled by its
        ``result`` message — with an :class:`~kopis.common.RpcError` if
        the owner could not perform the op. If a value in the op cannot
        be serialized on this side, the op raises instead of being
        sent.
        """

    def _apply_op(
        self,
        handle: RPCHandle,
        op: str,
        name: str | None,
        args: Sequence[object],
        kwargs: Mapping[str, object],
    ) -> Any:
        """Apply ``op`` to the live object behind ``handle`` (this side
        owns it), and return its result.

        The owner side decides whether the op can be performed: any
        failure raises, and is reported to the other side as the error
        of the op's result.
        """
        obj = self._handles.get(handle._id)
        if obj is None:
            raise LookupError(f"no live object behind {handle!r}")
        if op == "getattr":
            if name is None:
                raise ValueError("getattr op requires a name")
            return getattr(obj, name)
        if op == "call":
            if name is None:
                return obj(*args, **kwargs)
            return getattr(obj, name)(*args, **kwargs)
        if op == "getitem":
            return obj[args[0]]
        if op == "setitem":
            obj[args[0]] = args[1]
            return None
        if op == "delitem":
            del obj[args[0]]
            return None
        if op == "setattr":
            if name is None:
                raise ValueError("setattr op requires a name")
            setattr(obj, name, args[0])
            return None
        if op == "iter":
            return list(obj)
        raise ValueError(f"unknown RPCHandle op {op!r}")

    @abstractmethod
    async def _rpc_call(
        self, name: str, args: tuple[object, ...], kwargs: dict[str, object]
    ) -> object:
        """Send a call to a function registered on the other side and
        await its result.

        Raises if a value in the call cannot be serialized on this
        side: the call is not sent.
        """

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
