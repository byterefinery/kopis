"""The daisyUI ``Table`` component (both sides)."""

from typing import ClassVar

from ._component import Component

__all__ = ["Table"]


class Table(Component):
    """A daisyUI table: ``<table class="table">``.

    The structure is native — ``k.html.thead``, ``k.html.tbody``,
    ``k.html.tr``, ``k.html.th``, ``k.html.td`` (daisyUI styles them
    by tag), ``class_="row-hover"`` on a ``k.html.tr`` row. Wrap the
    table in ``k.html.div(class_="overflow-x-auto")`` to scroll it on
    small screens.

    ``size`` is ``table-{size}`` (default ``md``); ``zebra``,
    ``pin_rows`` and ``pin_cols`` add ``table-zebra``,
    ``table-pin-rows`` and ``table-pin-cols`` (independent — they can
    be combined).
    """

    tag = "table"
    classes = ("table",)
    types: ClassVar[dict[str, str]] = {
        "size": "table-{v}",
        "zebra": "table-zebra",
        "pin_rows": "table-pin-rows",
        "pin_cols": "table-pin-cols",
    }
