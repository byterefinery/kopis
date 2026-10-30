"""The server-side ``For`` (a stand-in).

The stand-in of the client-side ``For`` (see
:mod:`kopis.client.for_`): the server has no live DOM, so the loop
renders nothing — the block runs once at the entry of the ``with``
statement (its elements are stand-ins, as with everything else on the
document), and the list is not fetched (the client fetches it, and
renders the loop).
"""

from __future__ import annotations

from collections.abc import Callable
from inspect import iscoroutine
from typing import Any

from ..common.for_ import _Item

__all__ = ["For"]


class For:
    """A ``for`` loop of the server: a stand-in of the client's
    :class:`~kopis.client.for_.For` (the server renders nothing — the
    block runs once at the entry of the ``with`` statement, and the
    list is not fetched)."""

    _list_fn: Callable[[], Any]

    def __init__(self, list_fn: Callable[[], Any]) -> None:
        object.__setattr__(self, "_list_fn", list_fn)

    def __enter__(self) -> _Item:
        """Enter the loop: read the list function (a coroutine result is
        discarded — the list is not fetched, as the server renders
        nothing), and hand out the template pass's item."""
        value = self._list_fn()
        if iscoroutine(value):
            value.close()
        return _Item(0, None)

    def __exit__(self, *exc_info: object) -> bool:
        return False

    def __repr__(self) -> str:
        return "<For>"
