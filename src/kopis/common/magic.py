"""A dummy stand-in for objects the server side does not have.

The server-side stand-ins of the brython ``browser`` and ``javascript``
modules use :class:`Magic` for everything non-essential (``window``,
``ajax``, ``timer``, ``import_js``, ...), so unified code that touches
browser-only objects runs without complaint on the server and
type-checks: any attribute access, call, iteration, subscript, and
await on a ``Magic`` succeeds and yields another ``Magic``.

The brython DOM interface works the same way: ``append``, ``+``
(group), ``*`` (clone), and the ``with`` statement all succeed, but do
nothing — there is no live DOM on the server.
"""

from collections.abc import Callable, Iterator
from typing import Any, Self

__all__ = ["Magic"]


def _event_name(key: object) -> str | None:
    """The event name hidden behind an ``on<event>`` key (``None`` if
    ``key`` is not such a key)."""
    if isinstance(key, str) and key.startswith("on") and len(key) > 2:
        return key[2:]
    return None


def _on_decorator(target: object, event: str) -> Callable[..., Any]:
    """The decorator behind the read of an ``on<event>`` attribute of
    ``target``: applying it to a handler is the same as
    ``target.on<event> = handler`` — the binding of the client (a
    coroutine handler is started with ``aio.run`` when the event
    fires), a no-op of the server (no live DOM) — and the decorated
    handler is returned."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        setattr(target, f"on{event}", func)
        return func

    return decorator


class Magic:
    """A stand-in for a browser/Javascript object on the server side.

    Stateless: attribute access, calls, iteration, subscripts, and
    awaits all succeed (returning another ``Magic``); truth testing and
    length are falsy/zero. The brython DOM interface works the same way
    (see below): there is no live DOM on the server. An ``on<event>``
    name (e.g. ``window.onload``) reads as the decorator of the
    decorator form: it binds nothing (no live DOM) and returns the
    decorated handler.
    """

    def __getattr__(self, name: str) -> Any:
        # Missing attributes are stand-ins as well. They are cached, so
        # e.g. ``window.location`` is one stable stand-in object, as in
        # brython (where ``document.body`` is the same element each
        # time) — except that an ``on<event>`` name is the decorator
        # of the decorator form (see :func:`_on_decorator`): it binds
        # nothing on the server and returns the decorated handler.
        if name.startswith("_"):
            raise AttributeError(name)
        event = _event_name(name)
        if event is not None:
            return _on_decorator(self, event)
        child = Magic()
        # via object.__setattr__: __setattr__ is a no-op
        object.__setattr__(self, name, child)
        return child

    def __setattr__(self, name: str, value: object) -> None:
        pass

    def __call__(self, *args: object, **kwargs: object) -> Magic:
        return Magic()

    def __iter__(self) -> Iterator[object]:
        return iter(())

    def __getitem__(self, key: object) -> Magic:
        return Magic()

    def __setitem__(self, key: object, value: object) -> None:
        pass

    def __delitem__(self, key: object) -> None:
        pass

    def __await__(self) -> Iterator[object]:
        return iter(())

    def __bool__(self) -> bool:
        return False

    def __len__(self) -> int:
        return 0

    def __str__(self) -> str:
        return "<magic>"

    __repr__ = __str__

    # -- the brython DOM append interface -----------------------------------
    #
    # They succeed, but do nothing on the server: there is no live DOM.

    def append(self, *items: object) -> Magic:
        """Append one or more children, in order (the brython
        ``append`` method, the way to add children to an element). A
        string argument is first parsed as an HTML fragment on the
        client (the server is a no-op either way). Returns ``self`` so
        calls can be chained."""
        return self

    def __enter__(self) -> Self:
        """Support the brython ``with element:`` form."""
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None
