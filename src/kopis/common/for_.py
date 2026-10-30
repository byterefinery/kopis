"""``For`` — a reactive ``for`` loop, in the spirit of solidjs's
``For`` component.

In solidjs, ``For(list, render)`` renders ``render(item, index)`` for
each item of ``list``, and re-renders when ``list`` changes. This is
the same primitive, in pure Python, so it runs unmodified on both sides
of the web stack (the server, under CPython, and the client, under
Brython): a ``For`` created in an application is a ``For`` on each side.

A :class:`For` is a context manager — not a component: the block of the
``with`` statement is the loop's body (solidjs's ``render``), and the
elements created in the block join the innermost enclosing block
(``with element:``) — ``For`` itself renders no element of its own::

    with For(get_profiles) as profile:      # k.for_(get_profiles) is
                                             # the app's way to make one
        with k.html.tr():
            k.html.th(profile.index)
            k.html.td(profile['name'])
            k.html.td(profile['dob'])

The argument is a *list function*: a function that returns the list to
iterate over — a signal's getter, a shared signal's getter, or any
function. In an effect scope (``with k.effect():``) the read of the list
function is tracked, as a signal read in a component is: a change of the
signal it reads re-renders the loop, in place (see
:mod:`kopis.client.for_` for the client's re-execution of the block, and
:mod:`kopis.common.effect` for the scope).

The ``as`` variable is the loop's item: ``item.index`` is the item's
index (0-based, as in solidjs) and ``item.item`` is the item itself;
any other access is passed through to the item — ``item['name']`` is
``item['name']`` of the item, ``item.name`` is ``item.name`` of the
item, and so on (see :class:`_Item`).

The block runs once at the entry of the ``with`` statement (a *template
pass* — the elements it creates are detached, and never appear in the
document); the client side then re-executes the block's source —
captured from the running code — once per item of the list, and the
elements created in the re-executions are the loop's children (the
server has no live DOM, so it renders nothing — see
:mod:`kopis.server.for_`).
"""

from __future__ import annotations

from typing import Any

__all__ = ["_Item"]


class _Item:
    """The ``as`` variable of a :class:`For` block: the current item,
    with its index attached (solidjs attaches an ``index`` property to
    the item).

    ``item.index`` is the item's index (0-based) and ``item.item`` is
    the item itself; any other access is passed through to the item:
    ``item['name']`` is ``item['name']``, ``item.name`` is ``item.name``,
    and so on. The template pass of the loop (the one run at the entry
    of the block, before the list is known) is given an item of
    ``None``: its accesses return empty strings, so the block's code
    runs without failing (its result is detached, and never rendered).
    """

    _index: int
    _item: Any

    def __init__(self, index: int, item: Any) -> None:
        object.__setattr__(self, "_index", index)
        object.__setattr__(self, "_item", item)

    @property
    def index(self) -> int:
        """The item's index (0-based, as in solidjs's ``For``)."""
        return self._index

    @property
    def item(self) -> Any:
        """The item itself."""
        return self._item

    def __getitem__(self, key: object) -> Any:
        """The item's ``item[key]`` (an empty string in the template
        pass, where the item is ``None``)."""
        item = self._item
        if item is None:
            return ""
        return item[key]

    def __getattr__(self, name: str) -> Any:
        """The item's ``item.name`` (an empty string in the template
        pass, where the item is ``None``)."""
        item = self._item
        if item is None:
            return ""
        return getattr(item, name)

    def __repr__(self) -> str:
        return f"<For item {self._index} {self._item!r}>"
