"""Elements: the nodes a DOM tree is made of.

:class:`Element` mirrors a brython DOM element (a ``browser`` ``DOMNode``):
``tag``, ``attrs``, ``parent``, and the ``html``, ``text``, ``id``,
``children``, and ``child_nodes`` properties; ``append`` (HTML
snippets), ``<=`` (text, elements, or iterables of them), ``+`` and ``*``
(grouping elements at the same level), ``select`` / ``select_one`` /
``get`` / ``closest`` / ``index`` / ``inside``, ``clear`` and ``clone``,
the event methods (no-ops on a pure tree), iteration, ``str()`` (the
prettified tree), and ``repr()``.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from typing import Any, Self

from .render import _render_attrs, render_element, render_inline
from .select import _matches_selector, _selector_parts
from .util import VOID_TAGS, _check_name

__all__ = ["Element"]


class _Group:
    """A flat, ordered group of elements and text nodes (brython's
    ``TagSum``), produced by ``+`` and usable wherever children are
    expected."""

    def __init__(self, children: list[Element | str]) -> None:
        self.children = children

    def _concat(self, other: object) -> _Group:
        """A new group: ``self.children`` followed by ``other``."""
        items: list[Element | str] = list(self.children)
        if isinstance(other, _Group):
            items.extend(other.children)
        elif isinstance(other, (Element, str)):
            items.append(other)
        elif isinstance(other, Iterable):
            for item in other:
                if not isinstance(item, (Element, str)):
                    raise TypeError(f"cannot add {type(item).__name__} to a group")
                items.append(item)
        else:
            raise TypeError(f"cannot add {type(other).__name__} to a group")
        return _Group(items)

    def __add__(self, other: object) -> _Group:
        return self._concat(other)

    def __radd__(self, other: object) -> _Group:
        if isinstance(other, (Element, str)):
            return _Group([other, *self.children])
        if isinstance(other, _Group):
            return _Group(other.children + self.children)
        raise TypeError(f"cannot add {type(other).__name__} to a group")

    def __rmul__(self, other: int) -> _Group:
        if not isinstance(other, int) or other < 1:
            raise ValueError(f"cannot multiply a group by {other!r}")
        items: list[Element | str] = []
        for _ in range(other):
            items.extend(self.children)
        return _Group(items)

    def __iter__(self) -> Iterator[Element | str]:
        return iter(self.children)

    def __repr__(self) -> str:
        return f"<group of {len(self.children)}>"


class Element:
    """An element of an HTML tree.

    ``Element(tag, content, **attrs)`` creates ``<tag>`` with the given
    attributes; ``content`` is ``None``, an HTML snippet (a string), an
    element, or an iterable of them.
    """

    tag: str
    attrs: dict[str, str]
    parent: Element | None

    def __init__(
        self,
        tag: str,
        content: None | str | Element | _Group | Iterable[object] = None,
        **attrs: str,
    ) -> None:
        self.tag = _check_name(tag, "tag name")
        self.attrs = {}
        for name, value in attrs.items():
            # ``class`` is a Python keyword, so the ``class`` attribute is
            # given brython-style, as ``Class="..."`` or ``**{"class": "..."}``.
            self._set_attr(name, value)
        self._nodes: list[Element | str] = []
        self.parent = None
        if content is not None:
            if isinstance(content, (str, Element)):
                self.append(content)
            else:
                self._extend(content)

    # -- attributes and properties ------------------------------------

    def _set_attr(self, name: str, value: str) -> None:
        key = _check_name(name, "attribute name")
        value = str(value)
        if value:
            self.attrs[key] = value
        else:
            self.attrs.pop(key, None)

    @property
    def id(self) -> str:
        """The ``id`` attribute (``""`` when absent)."""
        return self.attrs.get("id", "")

    @id.setter
    def id(self, value: str) -> None:
        self._set_attr("id", value)

    @property
    def children(self) -> list[Element]:
        """The element's children of type element (not text nodes)."""
        return [child for child in self._nodes if isinstance(child, Element)]

    @property
    def child_nodes(self) -> list[Element | str]:
        """The element's children of any type (elements and text nodes)."""
        return list(self._nodes)

    @property
    def html(self) -> str:
        """The HTML code inside this element (its children)."""
        return "".join(render_inline(child, self.tag) for child in self._nodes)

    @html.setter
    def html(self, value: str) -> None:
        # Local import: parser and element need each other at runtime.
        from .parser import parse_fragment

        self.clear()
        self._extend(parse_fragment(value))

    @property
    def text(self) -> str:
        """All the text inside this element, descendants included."""
        parts: list[str] = []
        for child in self._nodes:
            parts.append(child if isinstance(child, str) else child.text)
        return "".join(parts)

    @text.setter
    def text(self, value: str) -> None:
        self.clear()
        self._append_text(value)

    # -- children -------------------------------------------------------

    def _add_element(self, child: Element) -> None:
        if self.tag in VOID_TAGS:
            raise ValueError(f"cannot add children to <{self.tag}>")
        if child.parent is not None:
            child.parent._nodes.remove(child)
        child.parent = self
        self._nodes.append(child)

    def append(self, *items: str | Element | _Group | Iterable[object]) -> Element:
        """Append children, parsing strings as HTML snippets.

        Returns ``self`` so calls can be chained.
        """
        # Local import: parser and element need each other at runtime.
        from .parser import parse_fragment

        for item in items:
            if isinstance(item, Element):
                self._add_element(item)
            elif isinstance(item, str):
                self._extend(parse_fragment(item))
            elif isinstance(item, Iterable):
                self._extend(item)
            else:
                raise TypeError(f"cannot append {type(item).__name__} to <{self.tag}>")
        return self

    def _extend(self, items: Iterable[object]) -> Element:
        """Append children that are already parsed (elements and text
        nodes). Returns ``self``."""
        for item in items:
            if isinstance(item, Element):
                self._add_element(item)
            elif isinstance(item, str):
                self._append_text(item)
            else:
                raise TypeError(
                    f"cannot extend <{self.tag}> with {type(item).__name__}"
                )
        return self

    def _append_text(self, text: str) -> Element:
        """Append a text node (escaped when serialized)."""
        if self.tag in VOID_TAGS:
            raise ValueError(f"cannot add children to <{self.tag}>")
        if text:
            self._nodes.append(text)
        return self

    def clear(self) -> None:
        """Remove all children."""
        for child in self._nodes:
            if isinstance(child, Element):
                child.parent = None
        self._nodes.clear()

    def clone(self) -> Element:
        """A deep copy of this element and its children (detached)."""
        copy = Element(self.tag)
        copy.attrs.update(self.attrs)
        for child in self._nodes:
            if isinstance(child, Element):
                copy._add_element(child.clone())
            else:
                copy._nodes.append(child)
        return copy

    def __le__(self, item: object) -> None:
        """Add a child (Brython's ``<=``): text, an element, or an
        iterable of them."""
        if isinstance(item, str):
            self._append_text(item)
        elif isinstance(item, Element):
            self._add_element(item)
        elif isinstance(item, Iterable):
            for sub in item:
                self.__le__(sub)
        else:
            raise TypeError(f"cannot append {type(item).__name__} to <{self.tag}>")

    def __add__(self, other: object) -> _Group:
        """Group ``self`` and ``other`` at the same level (Brython's
        ``+``)."""
        return _Group([self])._concat(other)

    def __radd__(self, other: object) -> _Group:
        if isinstance(other, (Element, str)):
            return _Group([other, self])
        if isinstance(other, _Group):
            return _Group(other.children + [self])
        raise TypeError(f"cannot add {type(other).__name__} to <{self.tag}>")

    def __mul__(self, other: int) -> _Group:
        """A group of ``other`` deep copies of this element (Brython's
        ``*``)."""
        if not isinstance(other, int) or other < 1:
            raise ValueError(f"cannot multiply <{self.tag}> by {other!r}")
        return _Group([self.clone() for _ in range(other)])

    __rmul__ = __mul__

    def __iter__(self) -> Iterator[Element | str]:
        """Iterate the children (text nodes included)."""
        return iter(self._nodes)

    def __len__(self) -> int:
        return len(self._nodes)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None

    # -- events -----------------------------------------------------------
    #
    # A pure tree has no live DOM, so the event methods below are no-ops;
    # handlers attached through them take effect when the same code runs
    # in the browser (where ``addEventListener`` is an alias of ``bind``,
    # exactly as in brython).

    def bind(
        self,
        event: str,
        handler: Callable[..., Any] | None = None,
        options: None | bool | dict[str, Any] = None,
    ) -> None:
        """Add an event listener to this element (no-op on the server)."""
        return None  # noqa: RET501 - an explicit no-op

    def unbind(self, event: str, handler: Callable[..., Any] | None = None) -> None:
        """Remove event listeners from this element (no-op on the server)."""
        return None  # noqa: RET501 - an explicit no-op

    def events(self, event: str) -> list[Callable[..., Any]]:
        """The handlers bound to ``event`` on this element (always empty
        on the server)."""
        return []

    addEventListener = bind
    removeEventListener = unbind

    # -- selecting (a small CSS selector subset) -----------------------

    def querySelector(self, selector: str) -> Element | None:
        """The first descendant matching ``selector``, or ``None``."""
        return self.select_one(selector)

    def querySelectorAll(self, selector: str) -> list[Element]:
        """All descendants matching ``selector``, in document order."""
        return self.select(selector)

    def get(
        self,
        *,
        id: str | None = None,
        name: str | None = None,
        tag: str | None = None,
        selector: str | None = None,
    ) -> list[Element]:
        """Descendants matched by one criterion (brython's ``get``).

        ``id`` matches the ``id`` attribute, ``name`` the ``name``
        attribute, ``tag`` the tag name, and ``selector`` a CSS selector;
        without a criterion the result is empty.
        """
        if name is not None:
            return [el for el in self._descendants() if el.attrs.get("name") == name]
        if tag is not None:
            return [el for el in self._descendants() if el.tag == tag.lower()]
        if id is not None:
            return [el for el in self._descendants() if el.attrs.get("id") == id]
        if selector is not None:
            return self.select(selector)
        return []

    def select(self, selector: str) -> list[Element]:
        """All descendants matching ``selector``, in document order.

        Supported subset: tag names and ``*``, ``#id`` and ``.class``
        parts combined on one element (``div#id.foo``), and parts joined
        by whitespace (descendants).
        """
        parts = _selector_parts(selector)
        return [el for el in self._descendants() if _matches_selector(el, parts)]

    def select_one(self, selector: str) -> Element | None:
        """The first descendant matching ``selector``, or ``None``."""
        matches = self.select(selector)
        return matches[0] if matches else None

    def closest(self, selector: str) -> Element:
        """This element or the first ancestor matching ``selector``
        (``KeyError`` when no element matches)."""
        parts = _selector_parts(selector)
        ancestor: Element | None = self
        while ancestor is not None:
            if _matches_selector(ancestor, parts):
                return ancestor
            ancestor = ancestor.parent
        raise KeyError(
            f"no element with selector {selector!r} in this element or its ancestors"
        )

    def index(self, selector: str | None = None) -> int:
        """The position of this element among its siblings
        (``-1`` when it has no parent, or — when ``selector`` is given —
        among its parent's descendants matching it)."""
        if self.parent is None:
            return -1
        if selector is None:
            siblings = self.parent._nodes
        else:
            siblings = self.parent.select(selector)
        for position, sibling in enumerate(siblings):
            if sibling is self:
                return position
        return -1

    def inside(self, other: Element) -> bool:
        """``True`` when this element is ``other`` or is contained inside
        it."""
        ancestor: Element | None = self
        while ancestor is not None:
            if ancestor is other:
                return True
            ancestor = ancestor.parent
        return False

    def _descendants(self) -> Iterator[Element]:
        for child in self._nodes:
            if isinstance(child, Element):
                yield child
                yield from child._descendants()

    # -- serialization ---------------------------------------------------

    def __str__(self) -> str:
        return render_element(self)

    def __repr__(self) -> str:
        return f"<{self.tag}{_render_attrs(self.attrs)}>"
