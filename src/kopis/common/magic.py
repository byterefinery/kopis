"""A dummy stand-in for objects the server side does not have.

The fake ``browser`` and ``javascript`` packages shipped with kopis use
:class:`Magic` for everything non-essential (``window``, ``ajax``,
``timer``, ``import_js``, ...), so unified code that touches
browser-only objects runs without complaint on the server and
type-checks: any attribute access, call, iteration, subscript, and
await on a ``Magic`` succeeds and yields another ``Magic``.
"""

from __future__ import annotations

from collections.abc import Iterator

__all__ = ["Magic"]


class Magic:
    """A stand-in for a browser/Javascript object on the server side.

    Stateless: attribute access, calls, iteration, subscripts, and
    awaits all succeed (returning another ``Magic``); truth testing and
    length are falsy/zero.
    """

    def __getattr__(self, name: str) -> Magic:
        return Magic()

    def __setattr__(self, name: str, value: object) -> None:
        pass

    def __call__(self, *args: object, **kwargs: object) -> Magic:
        return Magic()

    def __iter__(self) -> Iterator[object]:
        return iter(())

    def __getitem__(self, key: object) -> Magic:
        return Magic()

    def __await__(self) -> Iterator[object]:
        return iter(())

    def __bool__(self) -> bool:
        return False

    def __len__(self) -> int:
        return 0

    def __str__(self) -> str:
        return "<magic>"

    __repr__ = __str__
