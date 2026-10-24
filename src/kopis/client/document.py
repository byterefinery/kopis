"""A live view of the browser document (client side).

Wraps the brython ``browser.document`` and the DOM elements behind it, so
unified application code runs the same operations on both sides of the
web stack. Everything not overridden here is delegated to the underlying
brython objects, so all DOM properties and methods (``html``, ``text``,
``attrs``, ``select``, ``bind``, ...) work as-is.

Elements are looked up by ``id`` (subscripting) or by CSS selector
(:meth:`querySelector`), and special elements (``body``, ``head``) by
attribute::

    with k.document.body as el:
        el.append("<button id=...></button>")
    k.document.querySelector("#btn0").addEventListener("click", handler)
"""

from typing import Any, Self

from .brython import DOMNode

__all__ = ["Document", "Element"]


class Element:
    """A reference to an element of the browser document.

    :meth:`append` adds HTML elements, ``<=`` adds content, and any other
    attribute is delegated to the underlying DOM element, so all DOM
    properties and methods (``id``, ``innerHTML``, ``value``, ...) work
    as-is.
    """

    def __init__(self, element: Any) -> None:
        self._element = element

    def append(self, *items: object) -> Element:
        """Append content as children of this element.

        Strings are parsed as HTML snippets; elements and iterables of
        them are added as-is. Returns ``self`` so calls can be chained::

            k.document.body.append("<a/>").append("<b/>")
        """
        for item in items:
            if isinstance(item, Element):
                item = item._element
            if isinstance(item, str):
                item = item.strip()
                if not item:
                    continue
                self._element.insertAdjacentHTML("beforeend", item)
            else:
                self._element <= item  # noqa: B015 (Brython's <= adds a child)
        return self

    def __le__(self, content: object) -> None:
        """Append ``content`` as a child of this element."""
        if isinstance(content, Element):
            content = content._element
        self._element <= content  # noqa: B015 (Brython's <= adds a child)

    def __iter__(self):
        """Iterate the element's children (delegates to the DOM)."""
        return iter(self._element)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None

    def __getattr__(self, name: str) -> Any:
        # Only called when normal attribute lookup fails. Dunder lookups
        # (pickle, copy, introspection) must keep failing as usual, and
        # ``_element`` is guarded to avoid infinite recursion on a
        # half-initialized instance.
        if name == "_element" or (name.startswith("__") and name.endswith("__")):
            raise AttributeError(name)
        return getattr(self._element, name)


class Document:
    """A live view of the browser document.

    Elements are looked up by ``id`` (subscripting, ``KeyError`` when
    absent) or by CSS selector (:meth:`querySelector`); the ``body`` and
    ``head`` elements and any other attribute of the browser document are
    accessed by name, and ``<=`` appends content to the document (its
    body).
    """

    def __init__(self, document: Any) -> None:
        self._document = document

    def querySelector(self, selector: str) -> Element | None:
        """Return the first element matching ``selector``, or ``None``."""
        element = self._document.querySelector(selector)
        return Element(element) if element is not None else None

    def querySelectorAll(self, selector: str) -> list[Element]:
        """Return all elements matching ``selector``, in document order."""
        return [
            Element(element) for element in self._document.querySelectorAll(selector)
        ]

    def __getitem__(self, id: str) -> Element:
        """The element with the given ``id`` (``KeyError`` when absent)."""
        return Element(self._document[id])

    def __getattr__(self, name: str) -> Any:
        # Only called when normal attribute lookup fails. Dunder lookups
        # (pickle, copy, introspection) must keep failing as usual, and
        # ``_document`` is guarded to avoid infinite recursion on a
        # half-initialized instance.
        if name == "_document" or (name.startswith("__") and name.endswith("__")):
            raise AttributeError(name)
        value = getattr(self._document, name)
        # Elements are wrapped so the unified element API (``append``,
        # context manager) works; anything else (``title``, ``forms``,
        # ...) is handed out as-is.
        return Element(value) if isinstance(value, DOMNode) else value

    def __le__(self, content: object) -> None:
        """Append ``content`` to the document (its body)."""
        self._document <= content  # noqa: B015 (Brython's <= adds to the document)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None
