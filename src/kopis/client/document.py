"""A live view of the browser document (client side).

Look up an element by tag name with either subscripting or attribute
access, or by CSS selector with :meth:`querySelector`; both return an
:class:`Element`::

    with k.document.body as el:
        el.append("<button id=...></button>")
    k.document.querySelector("#btn0").addEventListener("click", handler)
"""

from collections.abc import Callable
from typing import Any, Self

__all__ = ["Document", "Element"]


class Element:
    """A reference to an element of the browser document.

    :meth:`append` adds HTML elements, ``<=`` adds content, and
    :meth:`addEventListener` attaches an event handler. Any other
    attribute is delegated to the underlying DOM element, so all DOM
    properties and methods (``id``, ``innerHTML``, ``value``, ...) work
    as-is.
    """

    def __init__(self, element: Any) -> None:
        self._element = element

    def append(self, *html: str) -> Element:
        """Append one or more HTML elements as children of this element.

        Each fragment is inserted as-is just before this element's end
        tag. Returns ``self`` so calls can be chained::

            k.document.body.append("<a/>").append("<b/>")
        """
        for fragment in html:
            fragment = fragment.strip()
            if not fragment:
                continue
            self._element.insertAdjacentHTML("beforeend", fragment)
        return self

    def addEventListener(self, event: str, handler: Callable[..., Any]) -> Any:
        """Add an event listener to this element (delegates to the DOM)."""
        return self._element.addEventListener(event, handler)

    def __le__(self, content: object) -> None:
        """Append ``content`` as a child of this element."""
        self._element <= content  # noqa: B015 (Brython's <= adds a child)

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

    :meth:`querySelector` returns the first element matching a CSS
    selector, or ``None``. ``<=`` appends content to the document (its
    body).
    """

    def __init__(self, document: Any) -> None:
        self._document = document

    def _element(self, name: str) -> Element:
        try:
            return Element(getattr(self._document, name))
        except AttributeError as exc:
            raise AttributeError(f"no <{name}> element in the document") from exc

    def querySelector(self, selector: str) -> Element | None:
        """Return the first element matching ``selector``, or ``None``."""
        element = self._document.querySelector(selector)
        if element is None:
            return None
        return Element(element)

    def __getitem__(self, name: str) -> Element:
        return self._element(name)

    def __getattr__(self, name: str) -> Element:
        # Only called when normal attribute lookup fails. Dunder lookups
        # (pickle, copy, introspection) must keep failing as usual, and
        # ``_document`` is guarded to avoid infinite recursion on a
        # half-initialized instance.
        if name == "_document" or (name.startswith("__") and name.endswith("__")):
            raise AttributeError(name)
        return self._element(name)

    def __le__(self, content: object) -> None:
        """Append ``content`` to the document (its body)."""
        self._document <= content  # noqa: B015 (Brython's <= adds to the document)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None
