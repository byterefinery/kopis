"""``signal`` — a single value with a getter and a setter, in the spirit
of solidjs signals.

solidjs's ``createSignal(initial)`` returns a pair of functions — a
getter and a setter — through which one value is read and updated. This
is the same primitive, in pure Python, so it runs unmodified on both
sides of the web stack (the server, under CPython, and the client, under
Brython): a signal created at the module level of an application is a
signal on each side, holding that side's value.

The getter is a function in its own right, not a bound method of an
object: it can be registered with :meth:`~kopis.common.KopisBase.register`
and called from the other side over RPC, and — the python twist on the
solidjs shape — its ``__name__`` is the name you bound it to in your
code, resolved from the caller's scope when it is read (see
:func:`_bound_name`). So::

    get_count, set_count = signal(0)

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
"""

import sys
from pickle import PicklingError
from typing import Any, NoReturn

__all__ = ["signal"]

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

    def __init__(self, cell: list[Any], fallback_name: str) -> None:
        object.__setattr__(self, "_cell", cell)
        object.__setattr__(self, "_fallback_name", fallback_name)

    def __call__(self) -> Any:
        """The signal's current value."""
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

    def __init__(self, cell: list[Any], fallback_name: str) -> None:
        object.__setattr__(self, "_cell", cell)
        object.__setattr__(self, "_fallback_name", fallback_name)

    def __call__(self, value: Any) -> None:
        """Update the signal's value to ``value``."""
        self._cell[0] = value

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
    signal(0)``) are their names. Reading ``__name__`` therefore walks
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


def signal(value: Any) -> tuple[_SignalGetter, _SignalSetter]:
    """Create a signal: a single value with a getter and a setter, in
    the spirit of solidjs signals (its ``createSignal`` returns the same
    pair).

    The pair is a 2-tuple, so the natural form is::

        get_count, set_count = signal(0)

    ``get_count()`` returns the signal's current value, and
    ``set_count(new_value)`` updates it. Both work the same way on both
    sides of the web stack.

    The getter is a first-class function: it can be registered with
    ``k.register`` and called from the other side over RPC, and its
    ``__name__`` is the name it is bound to in the caller's scope, so
    ``get_count = k.register(get_count)`` registers it under
    ``"get_count"`` and the other side calls it as ``k.get_count()``
    (as with any registered function, the RPC name is the function's
    ``__name__``).
    """
    cell: list[Any] = [value]
    return _SignalGetter(cell, "get"), _SignalSetter(cell, "set")
