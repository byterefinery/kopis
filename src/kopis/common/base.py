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
- the ``on_startup`` attribute — the app's list of startup hooks
  (``k.on_startup.append(main)``, or the decorator form
  ``@k.on_startup`` — the two have the same effect): a hook is a
  callable called with the app (a coroutine hook is awaited); on the
  server the hooks run when the web server starts, and on the client a
  hook is started at once when it is added (the client's startup is the
  app code itself, which Brython runs in the browser) — unlike the
  ``on<event>`` names (the window's handler properties), ``on_startup``
  is not a window event binding;
- the ``html`` property — the ``browser.html`` builder on the client,
  a stand-in on the server — and the app's resolution of a standard
  HTML5 tag name to it: ``k.li`` is ``k.html.li`` (see
  :meth:`KopisBase.__getattr__`);
- :meth:`signal` (the app's way to make a :class:`~kopis.common.Signal`),
  :meth:`shared_signal` (the app's way to make a
  :class:`~kopis.common.SharedSignal` — a signal whose value is shared
  between the server and the clients), and :meth:`effect` (the app's
  way to make an :class:`~kopis.common.Effect` scope) — the reactive
  primitives of the app, the same objects the classes make directly;
- :meth:`for_` (the app's way to make a ``For`` loop — the context
  manager whose ``with`` block is the loop's body, re-rendered on the
  client when the list's signal changes — see
  :mod:`~kopis.client.for_` and :mod:`~kopis.server.for_` for the sides);
- :meth:`register` (the canonical way ``k.rpc.register``, and the
  short way ``k.register``), and the registry of the functions
  registered with it;
- the ``k.rpc`` proxy, which calls a function registered on the other
  side (the actual sending of the call is left to :meth:`_rpc_call`);
  ``k.name(...)`` is the short way for ``k.rpc.name(...)`` — except
  that standard HTML5 tag names take precedence over the RPC names,
  resolving to ``k.html.<tag>`` (``k.li(...)`` is
  ``k.html.li(...)``), and ``on<event>`` names take precedence over
  them, resolving to the window's ``on<event>`` handler property (the
  handler, if one is set on the client; the decorator of the decorator
  form otherwise — the no-op one on the server); elements are not
  looked up by id on the app or on the document — the element with id
  ``"btn0"`` is ``k.window.btn0`` (the app's stand-in of the element —
  the only lookup of the document's elements by id) — and an
  ``on<event>`` read of an RPC name (``k.name.onclick``) raises
  ``AttributeError`` (the handlers of an element are bound on the
  element itself, not through the app);
- :meth:`_dispatch`, which runs a function called by the other side
  and builds the ``result`` or ``error`` part of its payload;
- the wiring of a :meth:`shared_signal`'s halves to the other side
  (the actual syncing of a shared signal's change is left to
  :meth:`_sync_shared_signal`);
- :meth:`_settle_result`, which resolves the future of a pending call
  from its ``result`` message;
- the registry of live objects this side keeps for values wrapped in
  handles (:attr:`_handles`), and the ``RPCHandle``s that stand in for
  them on the other side (:meth:`handle`, :meth:`get_handle`,
  :meth:`_apply_op`).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping, Sequence
from inspect import iscoroutine
from itertools import count
from pathlib import Path
from typing import Any, Self

from .effect import Effect
from .handle import RPCHandle, _HandleAttr
from .magic import _event_name, _on_decorator
from .signal import SharedSignal, Signal, _SignalGetter
from .tags import TAGS
from .uses import USES
from .wire import RpcError

__all__ = ["Client", "KopisBase"]


class _RpcCall:
    """``k.rpc.name`` (and the short way ``k.name``): a callable that
    calls the function ``name`` registered on the other side.

    When the function registered on this side under the same name is a
    signal getter, the call is also a read of that getter on this side
    (a local read for tracking: inside a tracked read — a reactive
    child of a component — it observes the signal, so a change of the
    signal re-runs the read and re-fetches the value; the value of the
    read still comes from the other side).

    The call has no attributes of its own: an ``on<event>`` read of it
    (``k.name.onclick``) raises ``AttributeError``, and an assignment
    to one raises as well — the handlers of an element are bound on the
    element itself (``k.window.name.onclick``), not through the app.
    """

    _owner: KopisBase
    _name: str

    def __init__(self, owner: KopisBase, name: str) -> None:
        object.__setattr__(self, "_owner", owner)
        object.__setattr__(self, "_name", name)

    def __call__(self, *args: object, **kwargs: object) -> object:
        # The local read of a getter registered on this side under the
        # same name: inside a tracked read (a reactive child of a
        # component) it observes the getter's signal, as any signal
        # read in the tracking scope does, so a change of the signal
        # re-runs the read (which re-fetches the value from the other
        # side); the local value itself is not used. Outside a
        # tracking scope the read has no effect.
        func = self._owner._bound.get(self._name)
        if isinstance(func, _SignalGetter):
            func()
        return self._owner._rpc_call(self._name, args, kwargs)

    def __getattr__(self, name: str) -> Any:
        raise AttributeError(name)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError(
            f"the RPC call {self._name!r} has no attribute {name!r}; "
            f"to bind the event handler of the element with that id, "
            f"use k.window.{self._name}.on<event>"
        )

    def __repr__(self) -> str:
        return f"<RPC call {self._name!r}>"


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

    def __getattr__(self, name: str) -> _RpcCall:
        """A callable that calls the function ``name`` registered on
        the other side (``k.rpc.name`` / ``k.name``)."""
        if name.startswith("_"):
            raise AttributeError(name)
        return _RpcCall(self._owner, name)


class Client:
    """A client connected to the server: an element of
    :attr:`KopisBase.clients` (server side).

    Attribute access makes a callable that calls the function ``<name>``
    that client registered, targeting that client — the high-level form
    of the server's ``k.call(client_id, name, ...)``::

        for client in k.clients:
            await client.update_count()

    The callable returns a future that resolves with the client's result
    (await it). On the client side, ``k.clients`` is empty (a stand-in),
    so a :class:`Client` only ever exists on the server.
    """

    _owner: KopisBase
    _client_id: str

    def __init__(self, owner: KopisBase, client_id: str) -> None:
        object.__setattr__(self, "_owner", owner)
        object.__setattr__(self, "_client_id", client_id)

    def __getattr__(self, name: str) -> Callable[..., Any]:
        """A callable that calls the function ``name`` the client
        registered, targeting that client, and returns a future that
        resolves with its result (await it)."""
        if name.startswith("_"):
            raise AttributeError(name)
        owner, client_id = self._owner, self._client_id

        def _call(*args: object, **kwargs: object) -> Any:
            return owner.call(client_id, name, *args, **kwargs)

        return _call

    def __repr__(self) -> str:
        return f"<client {self._client_id!r}>"


class _OnStartup(list):
    """The app's list of startup hooks (the ``k.on_startup`` attribute).

    Adding a hook — with :meth:`append`, or with the decorator form
    (:meth:`__call__`, ``@k.on_startup`` — the two have the same
    effect) — adds ``func`` to the list, and starts it at this side's
    startup: the server stores it, and starts it when the web server
    starts (the server drives its hooks, each called with the app — a
    coroutine hook is awaited); the client starts it at once (a
    coroutine ``func`` with ``aio.run``), since the client's startup is
    the app code itself, which Brython runs in the browser.
    """

    _owner: KopisBase

    def __init__(self, owner: KopisBase) -> None:
        self._owner = owner

    def append(self, func: Callable[..., Any]) -> None:
        """Add the startup hook ``func`` (and start it at this side's
        startup — see the class docstring)."""
        list.append(self, func)
        self._owner._start_startup_hook(func)

    def __call__(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """The decorator form of :meth:`append` (the two have the same
        effect): ``@k.on_startup`` adds ``func`` as a startup hook, and
        returns it unchanged."""
        self.append(func)
        return func


class KopisBase(ABC):
    """Base class of the unified ``Kopis`` application.

    The server-side and client-side ``Kopis`` classes both inherit from
    this class. It implements the parts of the unified API that are
    identical on both sides of the web stack (see the module docstring);
    the sides implement the platform-specific parts: the ``document``
    property, :meth:`run`, :meth:`add_static_file`, :meth:`parse_html`,
    :meth:`call`, :attr:`clients`, :meth:`_rpc_call`, and
    :meth:`_sync_shared_signal`.
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
            and name != "on_startup"  # not a window event (the hook list)
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
        # The app's startup hooks (the ``k.on_startup`` attribute):
        # the server runs them when the web server starts, and the
        # client starts them at once when they are added (its startup
        # is the app code itself).
        self.on_startup: _OnStartup = _OnStartup(self)
        self.rpc = _Rpc(self)
        # The live objects this side keeps for values it could not
        # serialize, and the handles that stand in for them on the
        # other side.
        self._handles: dict[int, Any] = {}
        self._next_handle_id = count(1)
        self._owner_id: str | None = (
            None  # this side's identity in the handles it makes
        )
        # The next number of a shared signal of the app (1-based; the
        # number is the shared signal's index in its internal RPC
        # names, and must match between the sides — the shared signals
        # are created by the unified code, in the same order, on both
        # sides).
        self._next_shared_signal = 1
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

    @property
    @abstractmethod
    def html(self) -> Any:
        """The ``browser.html`` builder (the brython module on the
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

    def signal(
        self,
        value: Any,
        on_change: Callable[[Signal, Any], Any] | None = None,
    ) -> Signal:
        """A :class:`~kopis.common.signal.Signal` of the application.

        The app's way to make a :class:`Signal` (the class can be used
        directly, and works the same way): ``signal = k.signal(0,
        count_changed)``, ``get_count, set_count = signal`` — see the
        class for the pair's behaviour. The signal holds this side's
        value, as with everything else on this side.
        """
        return Signal(value, on_change)

    def shared_signal(
        self,
        value: Any,
        on_change: Callable[[Signal, Any], Any] | None = None,
    ) -> SharedSignal:
        """A :class:`~kopis.common.signal.SharedSignal` of the
        application: a signal whose value is shared between the server
        and the clients (the class can be used directly, and works the
        same way) — see the class for the pair's behaviour and for how
        the two sides' copies of the value are synced.

        The call is unified code: it runs on both sides, and each side
        gets its half of the sharing (the server the shared side of
        the value, each client a copy of it), and wires its halves to
        the other side under the shared signal's internal RPC names:
        the server registers its getter (which serves the shared
        value) and its setter (which updates it, and then pushes the
        change to the other clients), and each client registers its
        push handler (which the server calls to notify it of a
        change, and which updates its copy of the value).
        """
        shared = SharedSignal(self, value, on_change)
        if self.is_server():
            self._bound[shared._getter_name] = shared._getter
            self._bound[shared._setter_name] = shared._setter
        else:
            self._bound[shared._setter_name] = shared._push_handler()
        return shared

    def effect(self) -> Effect:
        """An :class:`~kopis.common.effect.Effect` scope of the
        application (solidjs's ``createEffect``).

        The app's way to make an :class:`Effect` (the class can be used
        directly, and works the same way): ``with k.effect():`` makes
        the code of the block reactive — a signal read in the block
        (a getter child of a component) is observed, and is updated in
        place when the signal changes (see the class for the scope's
        behaviour).
        """
        return Effect()

    @abstractmethod
    def for_(self, list_fn: Callable[[], Any]) -> Any:
        """A ``For`` loop of the application (solidjs's ``For``
        component).

        The app's way to make a ``For`` (the class can be used directly,
        and works the same way): ``with k.for_(get_profiles) as profile:``
        makes the block of the ``with`` statement the loop's body — the
        elements created in it are the loop's children, in the innermost
        enclosing block — and, in an effect scope, a change of the list
        function's signal re-renders the loop, in place (see the class
        for the loop's behaviour: :class:`~kopis.client.for_.For` on the
        client, :class:`~kopis.server.for_.For` on the server).
        """

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

    def _start_startup_hook(self, func: Callable[..., Any]) -> None:
        """Start the startup hook ``func`` (an element of
        :attr:`on_startup`) at this side's startup.

        The default — the server — does nothing: the hook is stored in
        the list, and the server starts it when the web server starts
        (its web application's ``on_startup`` hook, each hook called
        with the app — see
        :meth:`~kopis.server.Kopis._run_startup_hooks`). The client
        overrides it: its startup is the app code itself, so the hook
        is started at once (a coroutine with ``aio.run``).
        """

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
        """A standard HTML5 tag name (``k.li``) is the short way for
        ``k.html.li``, an ``on<event>`` name (``k.onload``) is the
        window's ``on<event>`` handler property — the no-op decorator
        of the decorator form on this side, where there is no live
        window — and any other name is the short way for
        ``k.rpc.name``: ``k.name(...)`` calls a function registered on
        the other side. HTML5 tags and ``on<event>`` names take
        precedence over the RPC names.

        On the client, :class:`kopis.client.Kopis` refines this: with
        the live DOM, an ``on<event>`` name reads back the handler of
        the window's ``on<event>`` property, if one is set (and is the
        decorator of the decorator form otherwise), before the HTML5
        tag and the RPC call. On the server (no live DOM) every name
        that is neither an HTML5 tag nor an ``on<event>`` name is the
        RPC call.

        Only consulted for names that are not found the usual way, so
        the ``Kopis`` API (``register``, ``rpc``, ``document``, ...)
        is unaffected.
        """
        if name.startswith("_") or name == "rpc":
            # ``rpc`` is the proxy itself; failing here (instead of
            # dereferencing ``self.rpc``) also breaks any recursion if
            # this is consulted before ``__init__`` has set it.
            raise AttributeError(name)
        if name in TAGS:
            # The HTML5 tag takes precedence over the RPC call:
            # ``k.li(...)`` is ``k.html.li(...)``.
            return getattr(self.html, name)
        event = _event_name(name)
        if event is not None:
            # The window's ``on<event>`` handler property takes
            # precedence over the RPC call: on this side (no live
            # window) the decorator binds nothing and returns the
            # decorated handler.
            return _on_decorator(self.window, event)
        return self.rpc.__getattr__(name)

    @property
    @abstractmethod
    def clients(self) -> list[Client]:
        """The clients currently connected to this application (server
        side; a stand-in on the client side).

        Each element is a :class:`Client`: attribute access calls a
        function that client registered, targeting it::

            for client in k.clients:
                await client.update_count()
        """

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
    def call(self, client_id: str, method: str, *args: object, **kwargs: object) -> Any:
        """Queue a call to a function a client registered with
        :meth:`register`, targeted at a specific client (server side;
        a stand-in on the client side).

        The counterpart of the ``k.rpc.<name>`` call, which always
        targets the other side (the server): :meth:`call` picks the
        client it goes to by its id, and returns a future that resolves
        with the client's result. Its high-level form is
        ``client.<name>(...)`` for ``client`` in :attr:`clients`.
        """

    @abstractmethod
    async def _rpc_call(
        self, name: str, args: tuple[object, ...], kwargs: dict[str, object]
    ) -> object:
        """Send a call to a function registered on the other side and
        await its result.

        Raises if a value in the call cannot be serialized on this
        side: the call is not sent.
        """

    @abstractmethod
    async def _sync_shared_signal(self, shared: SharedSignal, value: Any) -> None:
        """Sync a change of a shared signal's value, made by the shared
        signal's setter: apply the change to this side's copy of the
        value (the observers of it run, and its ``on_change``
        callback, if any, is called with the signal and the value),
        and send the change to the other side. The server applies the
        change to the shared value first, and then pushes it to the
        other clients (the client that made the change is not
        notified — its copy of the value gets it when the server's
        result comes back); the client sends the change to the server
        first (whose copy of the value is the shared one, and which
        applies it and pushes it to the other clients), and applies
        it to its own copy afterwards.
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
