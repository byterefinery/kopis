"""A dummy stand-in for objects the server side does not have.

The server-side stand-ins of the brython ``browser`` and ``javascript``
modules use :class:`Magic` for everything non-essential (``window``,
``ajax``, ``timer``, ``import_js``, ...), so unified code that touches
browser-only objects runs without complaint on the server and
type-checks: any attribute access, call, iteration, subscript, and
await on a ``Magic`` succeeds and yields another ``Magic``.

The brython DOM operators work the same way: ``<=`` (append), ``+``
(group), ``*`` (clone), and the ``with`` statement all succeed, but do
nothing — there is no live DOM on the server.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Self

__all__ = ["Magic"]


class Magic:
    """A stand-in for a browser/Javascript object on the server side.

    Stateless: attribute access, calls, iteration, subscripts, and
    awaits all succeed (returning another ``Magic``); truth testing and
    length are falsy/zero. The brython DOM operators work the same way
    (see below): there is no live DOM on the server.
    """

    def __getattr__(self, name: str) -> Magic:
        # Missing attributes are stand-ins as well. They are cached, so
        # e.g. ``window.location`` is one stable stand-in object, as in
        # brython (where ``document.body`` is the same element each time).
        if name.startswith("_"):
            raise AttributeError(name)
        child = Magic()
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

    def __le__(self, other: object) -> Magic:
        """Append ``other`` (the brython ``<=``, an alias of ``attach``).

        A string argument is first parsed as an HTML fragment on the
        client (the server is a no-op either way). Returns ``self`` as
        in brython, so calls can be chained."""
        return self

    def attach(self, other: object) -> Magic:
        """Append ``other`` as a child (the brython ``attach``, the method
        behind ``<=``). Returns ``self`` so calls can be chained."""
        return self

    def append(self, *items: object) -> Magic:
        """Append children — works the same way as ``<=`` (the brython
        ``append``). Returns ``self`` so calls can be chained."""
        return self

    def __add__(self, other: object) -> Magic:
        """Group with ``other`` at the same level (the brython ``+``)."""
        return Magic()

    def __radd__(self, other: object) -> Magic:
        return Magic()

    def __mul__(self, other: object) -> Magic:
        """A group of deep copies (the brython ``*``)."""
        return Magic()

    def __rmul__(self, other: object) -> Magic:
        return Magic()

    def __enter__(self) -> Self:
        """Support the brython ``with element:`` form."""
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None
