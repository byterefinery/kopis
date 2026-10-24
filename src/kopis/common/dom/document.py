"""The DOM document: a root element plus the brython-style access of
``browser.document``.

A :class:`Document` is a parsed HTML document: its root element
(typically ``<html>``) is the ``root`` attribute. Subscripting is by
element ``id`` (``KeyError`` when absent), :meth:`querySelector` /
:meth:`select` work by CSS selector over the whole document, the
``body``, ``head``, and ``title`` properties name the usual elements,
and ``<=`` appends to the body.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Self

from .element import Element
from .select import _matches_selector, _selector_parts

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
        el = self.select_one("body")
        if el is None:
            raise AttributeError("no <body> element in the document")
        return el

    @property
    def head(self) -> Element:
        """The ``<head>`` element (``AttributeError`` when absent)."""
        el = self.select_one("head")
        if el is None:
            raise AttributeError("no <head> element in the document")
        return el

    @property
    def title(self) -> str:
        """The text of the ``<title>`` element (``""`` when absent)."""
        el = self.select_one("title")
        return el.text if el is not None else ""

    @title.setter
    def title(self, value: str) -> None:
        el = self.select_one("title")
        if el is None:
            el = Element("title")
            self.head._add_element(el)
        el.text = value

    def _elements(self) -> list[Element]:
        """All elements of the document, in document order."""
        return [self.root, *self.root._descendants()]

    def querySelector(self, selector: str) -> Element:
        """The first element of the document matching ``selector``
        (``KeyError`` when absent)."""
        el = self.select_one(selector)
        if el is None:
            raise KeyError(f"no element matching {selector!r} in the document")
        return el

    def querySelectorAll(self, selector: str) -> list[Element]:
        """All elements of the document matching ``selector``, in
        document order."""
        parts = _selector_parts(selector)
        return [el for el in self._elements() if _matches_selector(el, parts)]

    def select(self, selector: str) -> list[Element]:
        """All elements of the document matching ``selector``, in
        document order."""
        return self.querySelectorAll(selector)

    def select_one(self, selector: str) -> Element | None:
        """The first element of the document matching ``selector``, or
        ``None``."""
        parts = _selector_parts(selector)
        for el in self._elements():
            if _matches_selector(el, parts):
                return el
        return None

    def get(
        self,
        *,
        name: str | None = None,
        tag: str | None = None,
        classname: str | None = None,
        id: str | None = None,
        selector: str | None = None,
    ) -> list[Element]:
        """Elements of the document matched by one criterion (brython's
        ``get``); without a criterion the result is empty."""
        if name is not None:
            return [el for el in self._elements() if el.attrs.get("name") == name]
        if tag is not None:
            return [el for el in self._elements() if el.tag == tag.lower()]
        if classname is not None:
            return [
                el
                for el in self._elements()
                if classname in el.attrs.get("class", "").split()
            ]
        if id is not None:
            return [el for el in self._elements() if el.attrs.get("id") == id]
        if selector is not None:
            return self.select(selector)
        return []

    def createElement(self, tag: str, **attrs: str) -> Element:
        """A new, not yet attached element of type ``tag``."""
        return Element(tag, **attrs)

    def getElementById(self, id: str) -> Element | None:
        """The element with the given ``id``, or ``None`` when absent."""
        for el in self._elements():
            if el.attrs.get("id") == id:
                return el
        return None

    def __getitem__(self, id: str) -> Element:
        """The element with the given ``id`` (``KeyError`` when absent)."""
        el = self.getElementById(id)
        if el is None:
            raise KeyError(f"no element with id {id!r} in the document")
        return el

    def __setitem__(self, id: str, value: object) -> None:
        """Assigning a brython Javascript ``null``/``undefined``
        (``javascript.NULL`` / ``javascript.UNDEFINED``) removes the
        element (the brython behavior); any other value is ignored (a
        document has no attributes)."""
        # Local import: side-dependent module (the stand-in package under
        # CPython, the built-in module under Brython).
        from javascript import NULL, UNDEFINED

        if value is NULL or value is UNDEFINED:
            del self[id]

    def __delitem__(self, id: str) -> None:
        """Remove the element with the given ``id`` (``KeyError`` when
        absent)."""
        el = self.getElementById(id)
        if el is None:
            raise KeyError(f"no element with id {id!r} in the document")
        if el.parent is not None:
            el.parent._nodes.remove(el)
        el.parent = None

    def __contains__(self, id: object) -> bool:
        return isinstance(id, str) and self.getElementById(id) is not None

    def __iter__(self) -> Iterator[Element | str]:
        """Iterate the document's child nodes (its root's children)."""
        return iter(self.root._nodes)

    def __len__(self) -> int:
        return len(self.root._nodes)

    def __le__(self, content: object) -> None:
        """Append ``content`` to the document (its ``<body>``)."""
        self.body <= content

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None

    def __str__(self) -> str:
        return str(self.root)

    def __repr__(self) -> str:
        return f"<Document {self.root.tag}>"
