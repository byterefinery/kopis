"""The DOM document: a root element plus the brython-style access of
``browser.document``.

A :class:`Document` is a parsed HTML document: its root element
(typically ``<html>``) is the ``root`` attribute. Subscripting is by
element ``id`` (``KeyError`` when absent), :meth:`querySelector` /
:meth:`select` work by CSS selector over the whole document, the
``body`` and ``head`` properties name the usual elements, and ``<=``
appends to the body.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .select import _matches_selector, _selector_parts

if TYPE_CHECKING:
    from .element import Element

__all__ = ["Document"]


class Document:
    """A parsed HTML document, with the brython-style access of
    ``browser.document``.

    The document is its root element (typically ``<html>``), available
    as the ``root`` attribute. Subscripting is by element ``id``
    (``KeyError`` when absent), :meth:`querySelector` / :meth:`select`
    work by CSS selector over the whole document, and ``<=`` appends to
    the body.
    """

    def __init__(self, root: Element) -> None:
        self.root = root

    @property
    def body(self) -> Element:
        """The ``<body>`` element (``AttributeError`` when absent)."""
        el = self.querySelector("body")
        if el is None:
            raise AttributeError("no <body> element in the document")
        return el

    @property
    def head(self) -> Element:
        """The ``<head>`` element (``AttributeError`` when absent)."""
        el = self.querySelector("head")
        if el is None:
            raise AttributeError("no <head> element in the document")
        return el

    def _elements(self) -> list[Element]:
        """All elements of the document, in document order."""
        return [self.root, *self.root._descendants()]

    def querySelector(self, selector: str) -> Element | None:
        """The first element of the document matching ``selector``, or
        ``None``."""
        parts = _selector_parts(selector)
        for el in self._elements():
            if _matches_selector(el, parts):
                return el
        return None

    def select(self, selector: str) -> list[Element]:
        """All elements of the document matching ``selector``, in
        document order."""
        parts = _selector_parts(selector)
        return [el for el in self._elements() if _matches_selector(el, parts)]

    def select_one(self, selector: str) -> Element | None:
        """The first element of the document matching ``selector``, or
        ``None``."""
        return self.querySelector(selector)

    def __getitem__(self, id: str) -> Element:
        """The element with the given ``id`` (``KeyError`` when absent)."""
        for el in self._elements():
            if el.attrs.get("id") == id:
                return el
        raise KeyError(f"no element with id {id!r} in the document")

    def __le__(self, content: object) -> None:
        """Append ``content`` to the document (its ``<body>``)."""
        self.body <= content  # noqa: B015 (<= appends to the document)

    def __str__(self) -> str:
        return str(self.root)

    def __repr__(self) -> str:
        return f"<Document {self.root.tag}>"
