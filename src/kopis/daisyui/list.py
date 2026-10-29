"""The daisyUI ``List`` component (both sides)."""

from typing import ClassVar

from ._component import Component

__all__ = ["List", "ListCell", "ListRow"]


class List(Component):
    """A daisyUI list: ``<ul class="list">``.

    The children are arbitrary: ``ListRow`` items, or any element (a
    plain ``k.html.li`` header row, for example).
    """

    tag = "ul"
    classes = ("list",)


class ListRow(Component):
    """An item of the ``List``: ``<li class="list-row">``.

    The children are the cells: arbitrary elements. The second cell
    fills the remaining space by default; ``list-col-grow`` (a
    ``ListCell`` with ``grow=True``, or ``class_="list-col-grow"`` on
    another element) makes a cell fill the remaining space instead,
    and ``list-col-wrap`` (``wrap=True`` / ``class_="list-col-wrap"``)
    moves a cell to the next line.
    """

    tag = "li"
    classes = ("list-row",)


class ListCell(Component):
    """A cell (a direct child of the ``ListRow``): a ``<div>``.

    ``grow`` makes the cell fill the remaining space
    (``list-col-grow``); ``wrap`` moves the cell to the next line
    (``list-col-wrap``).
    """

    tag = "div"
    types: ClassVar[dict[str, str]] = {
        "grow": "list-col-grow",
        "wrap": "list-col-wrap",
    }
