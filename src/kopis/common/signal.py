"""``Signal`` — a single value with a getter and a setter, in the spirit
of solidjs signals.

solidjs's ``createSignal(initial)`` returns a pair of functions — a
getter and a setter — through which one value is read and updated. This
is the same primitive, in pure Python, so it runs unmodified on both
sides of the web stack (the server, under CPython, and the client, under
Brython): a signal created in an application is a signal on each side,
holding that side's value.

A :class:`Signal` unpacks to its getter and setter::

    signal = Signal(0)
    get_count, set_count = signal

The getter is a function in its own right, not a bound method of an
object: it can be registered with :meth:`~kopis.common.KopisBase.register`
and called from the other side over RPC, and — the python twist on the
solidjs shape — its ``__name__`` is the name you bound it to in your
code, resolved from the caller's scope when it is read (see
:func:`_bound_name`). So::

    signal = Signal(0)
    get_count, set_count = signal

    get_count = k.register(get_count)     # registered under "get_count",
                                           # the name it is bound to

    @k.register
    async def inc_count():
        count = get_count()
        count += 1
        set_count(count)
        return count

and the other side calls it as ``await k.get_count()`` (the RPC name is
the getter's ``__name__``, as with any registered function). The setter
is the same kind of object, bound to the name you gave it
(``set_count.__name__`` is ``"set_count"``).

Like any other value, a getter or setter that cannot be pickled does not
travel: sending one over RPC raises, and the developer wraps it in an
explicit :class:`~kopis.common.Handle` (``k.get_handle``) if it
should.

A signal also has observers, in the spirit of solidjs: a getter read
inside an :class:`~kopis.common.effect.Effect` scope that is tracking a
read (a getter child of a component — see
:mod:`kopis.common.component`) registers the read's update callback as
an observer of the signal, and an update of the signal's value (to a
value different from the current one) runs the observers, so the read
is re-done and its value re-rendered in place. See
:mod:`kopis.common.effect` for the scope.

A :class:`SharedSignal` is a :class:`Signal` whose value is shared
between the server and the clients (the app's way to make one is
``k.shared_signal``): the server holds the shared side of the value,
each client a copy of it, and the two are synced — a change made on
either side reaches the other, and the observers of each side's copy
run on it. Both halves of a shared signal are awaitable (calling one
returns a coroutine), so the unified code reads and writes the value
the same way on both sides.
"""

import sys
from collections.abc import Callable, Iterator
from inspect import iscoroutine
from pickle import PicklingError
from typing import Any, NoReturn

__all__ = ["SharedSignal", "Signal"]

#: The stack of the active effect scopes (innermost last): the scope a
#: signal read runs in (see :class:`~kopis.common.effect.Effect`).
_scopes: list[Any] = []


def _effect_scope() -> Any:
    """The innermost active effect scope, else ``None`` (see
    :class:`~kopis.common.effect.Effect`)."""
    return _scopes[-1] if _scopes else None


#: How far up the stack :func:`_bound_name` looks for the name the object
#: is bound to (a search that goes past the application's own frames is
#: looking for a bug, not a name).
_MAX_FRAMES = 64


class SignalGetter:
    """The getter half of a signal: calling it returns the signal's
    value.

    It has no name of its own: its ``__name__`` is the name the
    developer bound it to in their code (see :func:`_bound_name`), which
    is what :meth:`~kopis.common.KopisBase.register` uses as the RPC
    name. It does not travel: its value lives on the side where the
    signal was made, so pickling it raises (the developer wraps it in an
    explicit handle if it should travel).
    """

    cell: list[Any]
    fallback_name: str
    signal: Signal

    def __init__(self, cell: list[Any], fallback_name: str, signal: Signal) -> None:
        self.cell = cell
        self.fallback_name = fallback_name
        self.signal = signal

    def __call__(self) -> Any:
        """The signal's current value.

        A read in an active effect scope that is tracking a read (a
        getter child of a component — see
        :mod:`kopis.common.component`) registers the scope's update
        callback as an observer of the signal: a change of the signal
        re-runs the callback (which re-reads and re-renders the value).
        """
        scope = _scopes[-1] if _scopes else None
        if scope is not None and scope.tracking is not None:
            scope.observe(self.signal, scope.tracking)
        return self.cell[0]

    @property
    def __name__(self) -> str:
        """The name this getter is bound to in the calling scope (see
        :func:`_bound_name`)."""
        return _bound_name(self, self.fallback_name)

    def __repr__(self) -> str:
        return f"<signal getter {self.fallback_name!r}>"

    def __reduce__(self) -> NoReturn:
        raise PicklingError(
            "a signal getter cannot be pickled: its value lives on this side"
        )


class SignalSetter:
    """The setter half of a signal: calling it with a value updates the
    signal.

    As with the getter, its ``__name__`` is the name the developer bound
    it to in their code, and it does not travel (pickling it raises).
    """

    cell: list[Any]
    fallback_name: str
    signal: Signal
    on_change: Callable[[Signal, Any], Any] | None

    def __init__(
        self,
        cell: list[Any],
        fallback_name: str,
        signal: Signal,
        on_change: Callable[[Signal, Any], Any] | None = None,
    ) -> None:
        self.cell = cell
        self.fallback_name = fallback_name
        self.signal = signal
        self.on_change = on_change

    def __call__(self, value: Any) -> Any:
        """Update the signal's value to ``value``, and notify the
        signal's observers of the change.

        The observers (the reads of the value that an
        :class:`~kopis.common.effect.Effect` scope registered, in the
        solidjs way) are run when the value actually changed (to a
        value different from the current one), before the
        ``on_change`` callback — the local updates first, then the
        broadcast of the change, if any. If the signal was given an
        ``on_change`` callback, it is called with the signal and
        ``value`` after the update, and its result is returned: a
        synchronous callback returns ``None``, and an async one returns
        its coroutine, so the caller drives it with
        ``await set_count(value)``.
        """
        current = self.cell[0]
        self.cell[0] = value
        try:
            changed = value != current
        except Exception:  # noqa: BLE001 - a broken == still updates the value
            changed = value is not current
        if changed:
            for observer in list(self.signal.observers):
                observer()
        on_change = self.on_change
        if on_change is not None:
            return on_change(self.signal, value)
        return None

    @property
    def __name__(self) -> str:
        """The name this setter is bound to in the calling scope (see
        :func:`_bound_name`)."""
        return _bound_name(self, self.fallback_name)

    def __repr__(self) -> str:
        return f"<signal setter {self.fallback_name!r}>"

    def __reduce__(self) -> NoReturn:
        raise PicklingError(
            "a signal setter cannot be pickled: its value lives on this side"
        )


def _bound_name(obj: object, fallback: str) -> str:
    """The name ``obj`` is bound to in the nearest frame outside the
    ``kopis`` package, else ``fallback``.

    A signal's getter and setter have no names of their own; the names
    the developer gives them by binding (``get_count, set_count =
    signal``) are their names. Reading ``__name__`` therefore walks
    up the stack from the reader's caller — the reader itself, e.g.
    ``Kopis.register``, is inside the ``kopis`` package and is skipped,
    as are all the other ``kopis`` frames — and returns the first local
    name (else the first global name) of the first non-kopis frame that
    is bound to the object. The frame's own parameters are not
    considered: a getter passed to a helper function (``def reg(f):
    return k.register(f)``) is still bound to the name the caller gave
    it, not to the helper's parameter. When no such name is found (the
    object is not bound anywhere reachable, or frames are unavailable),
    the ``fallback`` is returned.
    """
    try:
        frame = sys._getframe(1)
    except AttributeError, ValueError:
        return fallback
    seen = 0
    while frame is not None and seen < _MAX_FRAMES:
        seen += 1
        module = frame.f_globals.get("__name__", "")
        if not isinstance(module, str) or not module.startswith("kopis"):
            # The frame's parameters (the leading entries of its code
            # object's ``co_varnames``). In Brython a missing attribute of
            # a code object comes back as ``None``-like rather than
            # raising, so the values are type-checked, not caught.
            code = frame.f_code
            varnames = getattr(code, "co_varnames", None)
            argcount = getattr(code, "co_argcount", None)
            kwonly = getattr(code, "co_kwonlyargcount", None)
            if (
                isinstance(varnames, (list, tuple))
                and isinstance(argcount, int)
                and isinstance(kwonly, int)
            ):
                params = set(varnames[: argcount + kwonly])
            else:
                params = set()
            for namespace in (frame.f_locals, frame.f_globals):
                try:
                    names = list(namespace)
                except TypeError:
                    continue
                for name in names:
                    if name in params:
                        continue
                    try:
                        if namespace[name] is obj:
                            return name
                    except KeyError, TypeError:
                        continue
        frame = frame.f_back
    return fallback


class Signal:
    """A single value with a getter and a setter, in the spirit of
    solidjs signals (its ``createSignal`` returns the same pair).

    A :class:`Signal` unpacks to the pair::

        signal = Signal(0)
        get_count, set_count = signal

    ``get_count()`` returns the signal's current value, and
    ``set_count(new_value)`` updates it. Both work the same way on both
    sides of the web stack.

    ``on_change`` is optional: when given, it is called with the signal
    and the new value on every update of the signal. The setter returns
    the callback's result, so an async ``on_change`` is driven by
    awaiting the setter::

        async def count_changed(signal: Signal, new_value: int):
            print("count_changed", new_value)

        signal = Signal(0, count_changed)
        get_count, set_count = signal
        await set_count(new_value)

    The getter is a first-class function: it can be registered with
    ``k.register`` and called from the other side over RPC, and its
    ``__name__`` is the name it is bound to in the caller's scope, so
    ``get_count = k.register(get_count)`` registers it under
    ``"get_count"`` and the other side calls it as ``k.get_count()``
    (as with any registered function, the RPC name is the function's
    ``__name__``).

    The signal has observers, in the spirit of solidjs: a getter read
    inside an :class:`~kopis.common.effect.Effect` scope that is
    tracking a read (a getter child of a component — see
    :mod:`kopis.common.component`) registers the read's update callback
    as an observer, and an update of the value (to a value different
    from the current one) runs the observers, so the read is re-done
    and its value re-rendered in place.
    """

    cell: list[Any]
    getter: SignalGetter
    setter: SignalSetter
    observers: list[Callable[[], Any]]

    def __init__(
        self,
        value: Any,
        on_change: Callable[[Signal, Any], Any] | None = None,
    ) -> None:
        cell: list[Any] = [value]
        self.cell = cell
        self.observers = []
        self.getter = SignalGetter(cell, "get", self)
        self.setter = SignalSetter(cell, "set", self, on_change)

    def _observe(self, callback: Callable[[], Any]) -> None:
        """Register ``callback`` as an observer of the change (a no-op
        if it is already registered): an update of the value runs the
        observers (see the class docstring)."""
        if callback not in self.observers:
            self.observers.append(callback)

    def _forget(self, callback: Callable[[], Any]) -> None:
        """Remove the observer ``callback`` (a no-op if it is not
        registered)."""
        try:
            self.observers.remove(callback)
        except ValueError:
            pass

    def __iter__(self) -> Iterator[Any]:
        """The getter and the setter, in that order (so the pair can be
        unpacked::

            get_count, set_count = signal

        ``get_count`` is a :class:`SignalGetter` (call it for the value)
        and ``set_count`` a :class:`SignalSetter` (call it with a value);
        the element type is left as ``Any`` because the two halves are
        different callables).
        """
        yield self.getter
        yield self.setter

    def __repr__(self) -> str:
        return f"<Signal {self.cell[0]!r}>"


class SharedSignalGetter:
    """The getter half of a shared signal (see
    :class:`SharedSignal`): calling it returns a coroutine that
    resolves to the signal's value.

    As with a plain signal's getter, a read in an active effect scope
    that is tracking a read (a getter child of a component) registers
    the read's update callback as an observer of this side's copy of
    the value, so an update of the copy re-runs the read. The value
    itself, on the client side, always comes from the server (the
    shared side of the signal); on the server, it is the shared value
    itself. Calling the getter therefore always returns an awaitable,
    on both sides, so the unified code can ``await get_count()``
    unmodified.
    """

    shared: SharedSignal

    def __init__(self, shared: SharedSignal) -> None:
        self.shared = shared

    def __call__(self) -> Any:
        """A coroutine that resolves to the signal's value (see the
        class docstring for where the value comes from, and what a
        read in a tracking scope registers)."""
        scope = _scopes[-1] if _scopes else None
        if scope is not None and scope.tracking is not None:
            scope.observe(self.shared.signal, scope.tracking)
        if self.shared.kopis.is_server():
            signal = self.shared.signal

            async def _get() -> Any:
                return signal.getter()

            return _get()
        kopis = self.shared.kopis
        name = self.shared.getter_name

        async def _get() -> Any:
            return await kopis._rpc_call(name, (), {})

        return _get()

    @property
    def __name__(self) -> str:
        """The name this getter is bound to in the calling scope (see
        :func:`_bound_name`)."""
        return _bound_name(self, "get")

    def __repr__(self) -> str:
        return f"<shared signal getter {self.shared.getter_name!r}>"

    def __reduce__(self) -> NoReturn:
        raise PicklingError(
            "a shared signal getter cannot be pickled: its value lives on the server"
        )


class SharedSignalSetter:
    """The setter half of a shared signal (see
    :class:`SharedSignal`): calling it with a value returns a
    coroutine that updates the signal.

    Awaiting the coroutine syncs the change to the other side (the
    side's :meth:`~kopis.common.KopisBase._sync_shared_signal`
    drives it) and updates this side's copy of the value (the local
    observers run, and the ``on_change`` callback, if any, is called
    with the signal and the value). The server applies the change to
    the shared value first, and then pushes it to the other clients;
    the client sends the change to the server first (which applies it
    and pushes it to the other clients), and updates its own copy
    after — so a re-read of the value (a re-done read of a tracked
    getter, for example) never fetches a value the server has not
    applied yet. The setter therefore always returns an awaitable,
    on both sides, so the unified code can ``await set_count(value)``
    unmodified.
    """

    shared: SharedSignal

    def __init__(self, shared: SharedSignal) -> None:
        self.shared = shared

    def __call__(self, value: Any) -> Any:
        """A coroutine that updates the signal to ``value`` and syncs
        the change to the other side (see the class docstring)."""
        shared = self.shared

        async def _set() -> Any:
            await shared.kopis._sync_shared_signal(shared, value)

        return _set()

    @property
    def __name__(self) -> str:
        """The name this setter is bound to in the calling scope (see
        :func:`_bound_name`)."""
        return _bound_name(self, "set")

    def __repr__(self) -> str:
        return f"<shared signal setter {self.shared.setter_name!r}>"

    def __reduce__(self) -> NoReturn:
        raise PicklingError(
            "a shared signal setter cannot be pickled: its value lives on the server"
        )


class SharedSignal:
    """A :class:`Signal` whose value is shared between the server and
    the clients.

    ``k.shared_signal(value, on_change)`` is the app's way to make one
    (the call is unified code: it runs on both sides, and each side
    gets its half of the sharing) — the server gets the shared side of
    the value, and every client gets a client-side copy of it. The
    two are synced: whatever a client sets, the server's value gets,
    and the change is then notified to the other clients, whose
    copies get it too (and whose observers run, as with a plain
    signal on each side). The value is always the server's: a
    client's getter reads the server's current value, and a client's
    setter sends the change to the server (which applies it and
    notifies the other clients), and then updates its own copy (so
    its own observers run, and a re-read of the value never fetches a
    value the server has not applied yet).

    A :class:`SharedSignal` unpacks to the getter and the setter, in
    that order (as a :class:`Signal` does)::

        get_count, set_count = k.shared_signal(0, count_changed)

    Both halves are awaitable (calling one returns a coroutine), so
    the unified code reads and writes the value the same way on both
    sides::

        count = await get_count()
        count += 1
        await set_count(count)

    A getter read inside an
    :class:`~kopis.common.effect.Effect` scope that is tracking a
    read (a getter child of a component) registers the read as an
    observer of this side's copy of the value, so an update of the
    copy (a local update, or a notification of a change made on the
    other side) re-runs the read and re-renders the value in place,
    as with a plain signal.

    The halves travel over RPC under internal names
    (``__kopis_shared_get_<n>`` and ``__kopis_shared_set_<n>``,
    ``n`` being the shared signal's number, counted from the app's
    first ``k.shared_signal``), so a shared signal is created by the
    unified code, in the same order, on both sides (as every other
    line of the app is). The names the developer binds the halves to
    (``get_count``, ``set_count``) are their ``__name__`` (as with a
    plain signal's halves), and either half can be registered with
    ``k.register`` like any other function.
    """

    kopis: Any
    signal: Signal
    index: int
    getter_name: str
    setter_name: str
    getter: SharedSignalGetter
    setter: SharedSignalSetter

    def __init__(
        self,
        kopis: Any,
        value: Any,
        on_change: Callable[[Signal, Any], Any] | None = None,
    ) -> None:
        self.index = kopis.next_shared_signal
        kopis.next_shared_signal += 1
        self.getter_name = f"__kopis_shared_get_{self.index}"
        self.setter_name = f"__kopis_shared_set_{self.index}"
        self.kopis = kopis
        # This side's copy of the value: the shared one on the server,
        # a per-client copy on the client.
        self.signal = Signal(value, on_change)
        self.getter = SharedSignalGetter(self)
        self.setter = SharedSignalSetter(self)

    def _push_handler(self) -> Callable[..., Any]:
        """The function this client registers so the server can push a
        change of the value to it (the other side of the setter's
        sync): it updates this client's copy of the value (the
        observers and the ``on_change`` callback run, as with a local
        update), and returns a coroutine that drives them."""

        def push(value: Any) -> Any:
            async def _run() -> Any:
                result = self.signal.setter(value)
                if iscoroutine(result):
                    return await result

            return _run()

        return push

    def __iter__(self) -> Iterator[Any]:
        """The getter and the setter, in that order (so the pair can be
        unpacked::

            get_count, set_count = k.shared_signal(0)

        ``get_count`` is a :class:`SharedSignalGetter` (call it and
        await it for the value) and ``set_count`` a
        :class:`SharedSignalSetter` (call it with a value and await
        it); the element type is left as ``Any`` because the two
        halves are different callables).
        """
        yield self.getter
        yield self.setter

    def __repr__(self) -> str:
        return f"<SharedSignal {self.signal.cell[0]!r}>"
