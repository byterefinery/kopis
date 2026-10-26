"""``KopisBase`` — the part of ``Kopis`` shared by both sides.

The server-side ``Kopis`` (``kopis.server``) and the client-side
``Kopis`` (``kopis.client``) both inherit from :class:`KopisBase` and
implement its abstract methods. The base class implements everything
the two sides do the same way:

- the ``use`` argument of the constructor — the client-side
  dependencies the app uses (:data:`~kopis.common.uses.USES`),
  ``"brython"`` by default — and :meth:`use`, which attaches them to
  the document head, one by one, as with any other dependency — a
  no-op on the server, where there is no live DOM;
- :meth:`addEventListener` and :meth:`removeEventListener`, the short
  forms for ``k.document.addEventListener`` and
  ``k.document.removeEventListener`` (direct document events) — a
  no-op on the server, where there is no live DOM;
- the ``window`` property — the browser window on the client, a
  stand-in on the server — and the ``on<event>`` namespace of the
  app: ``k.on<event> = handler`` binds the window's event handler
  property (``k.onload = handler`` is the same as
  ``k.window.onload = handler``, and ``k.on<event> = None`` removes
  it) — the window, not the document, has the handler properties for
  its events (there is no ``onDOMContentLoaded``), so the
  ``on<event>`` names never refer to document events — a no-op on
  the server, where there is no live window;
- :meth:`register` (the canonical way ``k.rpc.register``, and the
  short way ``k.register``), and the registry of the functions
  registered with it;
- the ``k.rpc`` proxy, which calls a function registered on the other
  side (the actual sending of the call is left to :meth:`_rpc_call`);
  ``k.name(...)`` is the short way for ``k.rpc.name(...)`` — on the
  client, which has the live DOM, ``k.name`` first resolves to the
  element with that id (``k["name"]``) and is the RPC call only if no
  element has that id — and ``k["id"]`` the short way for
  ``k.document["id"]`` (the element with that id);
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
from typing import Any, Self

from .handle import RPCHandle, _HandleAttr
from .uses import USES
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

    def is_server(self) -> bool:
        """Whether this ``Kopis`` runs on the server side (CPython).

        The side of the web stack this instance is running on — the
        instance-level companion of the module constant
        :data:`~kopis.IS_SERVER` (the two always agree), usable once the
        application object exists, before any request or event.
        """
        return self.side == "server"

    def is_client(self) -> bool:
        """Whether this ``Kopis`` runs on the client side (Brython, in
        the browser).

        The instance-level companion of the module constant
        :data:`~kopis.IS_CLIENT` (the two always agree), usable once the
        application object exists, before any request or event.
        """
        return self.side == "client"

    def __setattr__(self, name: str, value: Any) -> None:
        """Set an attribute of the application — except that an
        ``on<event>`` name is the window's event handler property for
        ``<event>``: ``k.onload = handler`` is the same as
        ``k.window.onload = handler`` (and ``k.onload = None``
        removes it). The window — not the document — has the handler
        properties for its events (there is no ``onDOMContentLoaded``),
        so the ``on<event>`` names of the app never refer to document
        events. On the client, a coroutine handler is started with
        ``aio.run`` when the event fires, and the window's ``onload``
        handler set after the ``load`` event has already been
        dispatched — which is always the case, since brython runs the
        application code on that event — is called at once with a
        synthetic event; on the server the binding is a no-op, as
        with everything else on the window."""
        if (
            not name.startswith("_")
            and name.startswith("on")
            and len(name) > 2
            and (value is None or callable(value))
        ):
            self._bind_window_on(name, value)
            return
        object.__setattr__(self, name, value)

    def __init__(
        self, use: str | list[str] | tuple[str, ...] | None = ("brython",)
    ) -> None:
        # The client-side dependencies the app uses (a string, a list
        # or tuple of strings, or None for none); ``"brython"`` by
        # default, as with any other dependency in
        # :data:`~kopis.common.uses.USES`.
        self._use: list[str] = (
            [] if use is None else [use] if isinstance(use, str) else list(use)
        )
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
        # The dependencies of the constructor, as with k.use(...).
        self.use(*self._use)

    # -- unified API ------------------------------------------------------

    @property
    @abstractmethod
    def document(self) -> Any:
        """A live view of the document."""

    @property
    @abstractmethod
    def window(self) -> Any:
        """The window (the brython ``browser.window`` object on the
        client; a stand-in on the server)."""

    def use(self, *names: str) -> Self:
        """Attach client-side dependencies to the document head.

        Each ``name`` is a short name from :data:`~kopis.common.uses.USES`
        (e.g. ``"brython"``, ``"alpinejs"``, ``"lodash"``); the
        dependency's ``<script>`` and ``<link>`` elements are attached
        to the document head, in order, each at most once — an element
        whose URL is already in the head is skipped, so a dependency
        shared between names (the Tailwind browser build behind
        ``"tailwindcss"`` and ``"daisyui"``) is loaded only once. Unknown
        names raise ``KeyError``. A no-op on the server (no live DOM):
        when the same code runs in the browser, the client does the
        real work. The constructor's ``use`` argument works the same
        way — a string or a list of strings, ``["brython"]`` by
        default — and applies each of them with this method.
        """
        for name in names:
            if name not in USES:
                known = ", ".join(f"{n!r}" for n in sorted(USES))
                raise KeyError(f"unknown use {name!r} (known: {known})")
        if self.is_server():
            return self
        head = self.document.head
        for name in names:
            for element in self.parse_html(USES[name]):
                tag = element.tagName  # 'SCRIPT' or 'LINK'
                url = element.src if tag == "SCRIPT" else element.href
                for other in head.getElementsByTagName(tag.lower()):
                    if (other.src if tag == "SCRIPT" else other.href) == url:
                        break  # already in the head (a shared dependency)
                else:
                    head.attach(element)
        return self

    def addEventListener(
        self, event: str, func: Callable[..., Any], options: Any = None
    ) -> None:
        """Bind ``func`` to ``event`` on the document: the short form
        of ``k.document.addEventListener(event, func, options)``.

        On the client (the live DOM) the binding is real — a coroutine
        ``func`` is started with ``aio.run`` when the event fires, and
        the document's ``DOMContentLoaded`` event, which has already
        been dispatched by then, calls ``func`` at once (the
        ``load`` event is a window event, not a document event) — see
        :mod:`kopis.client.dom`. On the server (no live DOM) the
        binding is a no-op.
        """
        self.document.addEventListener(event, func, options)

    def removeEventListener(self, event: str, *funcs: object) -> None:
        """Remove the handlers ``funcs`` from ``event`` on the document:
        the short form of ``k.document.removeEventListener(event,
        *funcs)`` (with no ``funcs``, all handlers of ``event``).

        A no-op on the server (no live DOM).
        """
        self.document.removeEventListener(event, *funcs)

    def _bind_window_on(self, name: str, value: Any) -> None:
        """Bind ``value`` to the window's ``on<event>`` property
        (``name`` is the ``on<event>`` name; ``None`` removes it).

        On the client the binding goes through the window's
        ``__setattr__`` extension (see :mod:`kopis.client.dom`): a
        coroutine is started with ``aio.run`` when the event fires,
        and an ``onload`` handler set after the ``load`` event has
        already been dispatched is called at once. On the server the
        window is a stand-in, so the binding is a no-op.
        """
        setattr(self.window, name, value)

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

    def __getattr__(self, name: str) -> Any:
        """The short way for ``k.rpc.name``: ``k.name(...)`` calls a
        function registered on the other side.

        On the client, :class:`kopis.client.Kopis` refines this: with
        the live DOM, ``k.name`` first resolves to the element with
        that id (``k["name"]``), and is the RPC call only if no element
        has that id. On the server (no live DOM) every name is the RPC
        call.

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
        """Perform ``op`` of ``handle`` and return its result.

        If this side owns the live object, the op is applied at once:
        a sync operation returns its value, and a coroutine method
        returns its coroutine (the caller awaits it). Otherwise the op
        goes to the owner: the server (which runs the calling code off
        its event loop) performs the round trip and blocks the calling
        thread — a sync operation returns its value, and a coroutine
        method returns an awaitable holding the result; the client
        (whose single browser thread cannot block) returns an
        awaitable future instead. A failure of the op — or of the
        round trip itself — raises an
        :class:`~kopis.common.RpcError` where the side can, and is
        reported as the error of the op's result otherwise. If a value
        in the op cannot be serialized on this side, the op raises
        instead of being sent.
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
        owns it), and return its result — a value, or a coroutine if a
        coroutine method was called (the caller awaits it).

        A ``getattr`` of a callable attribute returns a
        :class:`~kopis.common.handle._HandleAttr` stand-in: the method
        itself cannot travel, but the stand-in travels, and invoking
        it fires a ``call`` op. The owner side decides whether the op
        can be performed: any failure raises, and is reported to the
        other side as the error of the op's result.
        """
        obj = self._handles.get(handle._id)
        if obj is None:
            raise LookupError(f"no live object behind {handle!r}")
        if op == "getattr":
            if name is None:
                raise ValueError("getattr op requires a name")
            value = getattr(obj, name)
            if iscoroutine(value):
                raise ValueError(
                    f"attribute {name!r} is a coroutine object; it cannot travel"
                )
            if callable(value):
                return _HandleAttr(handle, name)
            return value
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

    def _handle_getattr(self, handle: RPCHandle, name: str) -> Any:
        """The result of ``handle.<name>``: the live value of a data
        attribute, or a :class:`~kopis.common.handle._HandleAttr`
        stand-in for a method (a ``getattr`` op performed by
        :meth:`_handle_op`, so it applies at once on this side and
        travels to the owner otherwise)."""
        return self._handle_op(handle, "getattr", name)

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
