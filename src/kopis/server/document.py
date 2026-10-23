"""A live view of the HTML document served at ``/`` (server side).

The document is stored as a string — assigned to ``k.document`` or read
from ``index.html`` in the root directory — and parsed with
:mod:`beautifulsoup4`. Look up an element by tag name with either
subscripting or attribute access, or by CSS selector with
:meth:`querySelector`; both return an :class:`Element`. Element
mutations edit the parsed tree, and the served document is always the
(re-)serialized tree, so the browser receives a canonical, valid form
of the document::

    k.document["head"].append('<meta name="viewport" content="...">')
    with k.document.body as el:
        el.append("<script src=...></script>")
"""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Self

from bs4 import BeautifulSoup, Tag
from bs4.builder import HTMLTreeBuilder

if TYPE_CHECKING:
    from .app import Kopis

__all__ = ["Document", "Element", "_Noop", "insert_into"]

#: Tags that never have children or an end tag.
_empty_tags = HTMLTreeBuilder.DEFAULT_EMPTY_ELEMENT_TAGS
_VOID_TAGS: frozenset[str] = (
    frozenset(_empty_tags) if _empty_tags is not None else frozenset()
)


def insert_into(tag: Tag, fragment: str, is_text: bool = False) -> None:
    """Insert ``fragment`` as children of ``tag``.

    ``fragment`` is an HTML snippet, parsed with Beautiful Soup to
    validate it and to confirm it actually contains elements; with
    ``is_text`` it is raw text, inserted as a text node (Beautiful Soup
    escapes it when the document is serialized).
    """
    if tag.name in _VOID_TAGS:
        raise ValueError(f"cannot add children to <{tag.name}>")
    if is_text:
        tag.append(fragment)
        return
    fragment = fragment.strip()
    if not fragment:
        return
    soup = BeautifulSoup(fragment, "html.parser")
    if not any(isinstance(c, Tag) for c in soup.children):
        return
    tag.extend(soup.children)


class Document:
    """A live view of the HTML document served at ``/``."""

    def __init__(self, owner: Kopis) -> None:
        self._owner = owner

    def _element(self, name: str) -> Element:
        tag = self._owner._parse().find(name)
        if tag is None:
            raise KeyError(f"no <{name}> element in the document")
        return Element(self, tag)

    def querySelector(self, selector: str) -> Element | None:
        """Return the first element matching ``selector``, or ``None``."""
        tags = self._owner._parse().select(selector)
        if not tags:
            return None
        return Element(self, tags[0])

    def __getitem__(self, name: str) -> Element:
        return self._element(name)

    def __getattr__(self, name: str) -> Element:
        # Only called when normal attribute lookup fails. Dunder lookups
        # (pickle, copy, introspection) must keep failing as usual, and
        # ``_owner`` is guarded to avoid infinite recursion on a
        # half-initialized instance.
        if name == "_owner" or (name.startswith("__") and name.endswith("__")):
            raise AttributeError(name)
        try:
            return self._element(name)
        except KeyError as exc:
            raise AttributeError(str(exc)) from exc

    def __str__(self) -> str:
        return str(self._owner._parse())

    def __le__(self, content: object) -> None:
        """Append ``content`` as text to the document (its body)."""
        self.body <= content  # noqa: B015 (<= appends to the document)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None


class Element:
    """A reference to an element of the document.

    The ``tag`` attribute is the underlying :class:`bs4.element.Tag`, so
    any Beautiful Soup method works on it.
    """

    def __init__(self, document: Document, tag: Tag) -> None:
        self._document = document
        self.tag = tag

    def append(self, *html: str) -> Element:
        """Append one or more HTML elements as children of this element.

        Returns ``self`` so calls can be chained::

            k.document["head"].append("<a/>").append("<b/>")
        """
        for fragment in html:
            insert_into(self.tag, fragment)
        return self

    def addEventListener(self, event: str, handler: Callable[..., Any]) -> Element:
        """Add an event listener to this element.

        The server has no live DOM, so this is a no-op; the handler takes
        effect when the same code runs in the browser.
        """
        return self

    def __le__(self, content: object) -> None:
        """Append ``content`` as text to this element."""
        insert_into(self.tag, str(content), is_text=True)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None


class _Noop:
    """A no-op stand-in for the document (and its elements) on the server.

    In brython mode the document is built in the browser, where the same
    application code runs under Brython. Document operations therefore do
    nothing on the server (but never fail), so the unified application
    code can run unmodified on both sides.
    """

    def append(self, *html: str) -> Self:
        return self

    def addEventListener(self, event: str, handler: Callable[..., Any]) -> Self:
        return self

    def querySelector(self, selector: str) -> Self:
        return self

    def __getitem__(self, name: object) -> Self:
        return self

    def __le__(self, content: object) -> None:
        return None

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None

    def __getattr__(self, name: str) -> Self:
        # Any attribute (e.g. ``body``, ``head``) resolves to the same
        # no-op, so chained lookups keep working. Dunder lookups must keep
        # failing as usual.
        if name.startswith("_"):
            raise AttributeError(name)
        return self
