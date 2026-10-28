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
explicit :class:`~kopis.common.RPCHandle` (``k.get_handle``) if it
should.

A signal also has observers, in the spirit of solidjs: a getter read
inside an :class:`~kopis.common.effect.Effect` scope that is tracking a
read (a getter child of a component — see
:mod:`kopis.common.component`) registers the read's update callback as
an observer of the signal, and an update of the signal's value (to a
value different from the current one) runs the observers, so the read
is re-done and its value re-rendered in place. See
:mod:`kopis.common.effect` for the scope.
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Iterator
from pickle import PicklingError
from typing import Any, NoReturn

__all__ = ["Signal"]

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


class _SignalGetter:
    """The getter half of a signal: calling it returns the signal's
    value.

    It has no name of its own: its ``__name__`` is the name the
    developer bound it to in their code (see :func:`_bound_name`), which
    is what :meth:`~kopis.common.KopisBase.register` uses as the RPC
    name. It does not travel: its value lives on the side where the
    signal was made, so pickling it raises (the developer wraps it in an
    explicit handle if it should travel).
    """

    _cell: list[Any]
    _fallback_name: str
    _signal: Signal

    def __init__(self, cell: list[Any], fallback_name: str, signal: Signal) -> None:
        object.__setattr__(self, "_cell", cell)
        object.__setattr__(self, "_fallback_name", fallback_name)
        object.__setattr__(self, "_signal", signal)

    def __call__(self) -> Any:
        """The signal's current value.

        A read in an active effect scope that is tracking a read (a
        getter child of a component — see
        :mod:`kopis.common.component`) registers the scope's update
        callback as an observer of the signal: a change of the signal
        re-runs the callback (which re-reads and re-renders the value).
        """
        scope = _scopes[-1] if _scopes else None
        if scope is not None and scope._tracking is not None:
            scope.observe(self._signal, scope._tracking)
        return self._cell[0]

    @property
    def __name__(self) -> str:
        """The name this getter is bound to in the calling scope (see
        :func:`_bound_name`)."""
        return _bound_name(self, self._fallback_name)

    def __repr__(self) -> str:
        return f"<signal getter {self._fallback_name!r}>"

    def __reduce__(self) -> NoReturn:
        raise PicklingError(
            "a signal getter cannot be pickled: its value lives on this side"
        )


class _SignalSetter:
    """The setter half of a signal: calling it with a value updates the
    signal.

    As with the getter, its ``__name__`` is the name the developer bound
    it to in their code, and it does not travel (pickling it raises).
    """

    _cell: list[Any]
    _fallback_name: str
    _signal: Signal
    _on_change: Callable[[Signal, Any], Any] | None

    def __init__(
        self,
        cell: list[Any],
        fallback_name: str,
        signal: Signal,
        on_change: Callable[[Signal, Any], Any] | None = None,
    ) -> None:
        object.__setattr__(self, "_cell", cell)
        object.__setattr__(self, "_fallback_name", fallback_name)
        object.__setattr__(self, "_signal", signal)
        object.__setattr__(self, "_on_change", on_change)

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
        current = self._cell[0]
        self._cell[0] = value
        try:
            changed = value != current
        except Exception:  # noqa: BLE001 - a broken == still updates the value
            changed = value is not current
        if changed:
            for observer in list(self._signal._observers):
                observer()
        on_change = self._on_change
        if on_change is not None:
            return on_change(self._signal, value)
        return None

    @property
    def __name__(self) -> str:
        """The name this setter is bound to in the calling scope (see
        :func:`_bound_name`)."""
        return _bound_name(self, self._fallback_name)

    def __repr__(self) -> str:
        return f"<signal setter {self._fallback_name!r}>"

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

    _cell: list[Any]
    _getter: _SignalGetter
    _setter: _SignalSetter
    _observers: list[Callable[[], Any]]

    def __init__(
        self,
        value: Any,
        on_change: Callable[[Signal, Any], Any] | None = None,
    ) -> None:
        cell: list[Any] = [value]
        object.__setattr__(self, "_cell", cell)
        object.__setattr__(self, "_observers", [])
        object.__setattr__(self, "_getter", _SignalGetter(cell, "get", self))
        object.__setattr__(
            self,
            "_setter",
            _SignalSetter(cell, "set", self, on_change),
        )

    def _observe(self, callback: Callable[[], Any]) -> None:
        """Register ``callback`` as an observer of the change (a no-op
        if it is already registered): an update of the value runs the
        observers (see the class docstring)."""
        if callback not in self._observers:
            self._observers.append(callback)

    def _forget(self, callback: Callable[[], Any]) -> None:
        """Remove the observer ``callback`` (a no-op if it is not
        registered)."""
        try:
            self._observers.remove(callback)
        except ValueError:
            pass

    def __iter__(self) -> Iterator[Any]:
        """The getter and the setter, in that order (so the pair can be
        unpacked::

            get_count, set_count = signal

        ``get_count`` is a :class:`_SignalGetter` (call it for the value)
        and ``set_count`` a :class:`_SignalSetter` (call it with a value);
        the element type is left as ``Any`` because the two halves are
        different callables).
        """
        yield self._getter
        yield self._setter

    def __repr__(self) -> str:
        return f"<Signal {self._cell[0]!r}>"
