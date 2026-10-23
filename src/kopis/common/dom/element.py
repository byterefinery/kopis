"""Elements: the nodes a DOM tree is made of.

:class:`Element` mirrors a brython DOM element: ``tag``, ``attrs``,
``children``, ``parent``; properties ``html``, ``text``, ``class_name``,
and ``id``; ``append`` (HTML snippets), ``append_text`` (text nodes),
``<=`` (text, elements, or iterables of them), ``+`` (grouping elements
at the same level), ``select`` / ``select_one``, ``clone``, iteration,
``str()`` (the prettified tree), and ``repr()``.
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
    children: list[Element | str]
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
            # given as ``class_name`` (or ``Class``, brython style).
            self._set_attr("class" if name == "class_name" else name, value)
        self.children = []
        self.parent = None
        if content is not None:
            if isinstance(content, (str, Element)):
                self.append(content)
            else:
                self.extend(content)

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
    def class_name(self) -> str:
        """The ``class`` attribute (``""`` when absent)."""
        return self.attrs.get("class", "")

    @class_name.setter
    def class_name(self, value: str) -> None:
        self._set_attr("class", value)

    @property
    def html(self) -> str:
        """The HTML code inside this element (its children)."""
        return "".join(render_inline(child, self.tag) for child in self.children)

    @html.setter
    def html(self, value: str) -> None:
        # Local import: parser and element need each other at runtime.
        from .parser import parse_fragment

        self.clear()
        self.extend(parse_fragment(value))

    @property
    def text(self) -> str:
        """All the text inside this element, descendants included."""
        parts: list[str] = []
        for child in self.children:
            parts.append(child if isinstance(child, str) else child.text)
        return "".join(parts)

    @text.setter
    def text(self, value: str) -> None:
        self.clear()
        self.append_text(value)

    # -- children -------------------------------------------------------

    def _add_element(self, child: Element) -> None:
        if self.tag in VOID_TAGS:
            raise ValueError(f"cannot add children to <{self.tag}>")
        if child.parent is not None:
            child.parent.children.remove(child)
        child.parent = self
        self.children.append(child)

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
                self.extend(parse_fragment(item))
            elif isinstance(item, Iterable):
                self.extend(item)
            else:
                raise TypeError(f"cannot append {type(item).__name__} to <{self.tag}>")
        return self

    def extend(self, items: Iterable[object]) -> Element:
        """Append children that are already parsed (elements and text
        nodes). Returns ``self``."""
        for item in items:
            if isinstance(item, Element):
                self._add_element(item)
            elif isinstance(item, str):
                self.append_text(item)
            else:
                raise TypeError(
                    f"cannot extend <{self.tag}> with {type(item).__name__}"
                )
        return self

    def append_text(self, text: str) -> Element:
        """Append a text node (escaped when serialized)."""
        if self.tag in VOID_TAGS:
            raise ValueError(f"cannot add children to <{self.tag}>")
        if text:
            self.children.append(text)
        return self

    def clear(self) -> None:
        """Remove all children."""
        for child in self.children:
            if isinstance(child, Element):
                child.parent = None
        self.children.clear()

    def clone(self) -> Element:
        """A deep copy of this element and its children (detached)."""
        copy = Element(self.tag)
        copy.attrs.update(self.attrs)
        for child in self.children:
            if isinstance(child, Element):
                copy._add_element(child.clone())
            else:
                copy.children.append(child)
        return copy

    def __le__(self, item: object) -> None:
        """Add a child (Brython's ``<=``): text, an element, or an
        iterable of them."""
        if isinstance(item, str):
            self.append_text(item)
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

    def __iter__(self) -> Iterator[Element | str]:
        """Iterate the children (text nodes included)."""
        return iter(self.children)

    def __len__(self) -> int:
        return len(self.children)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None

    def addEventListener(self, event: str, handler: Callable[..., Any]) -> Element:
        """Add an event listener to this element.

        A pure tree has no live DOM, so this is a no-op; the handler
        takes effect when the same code runs in the browser.
        """
        return self

    # -- selecting (a small CSS selector subset) -----------------------

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

    def _descendants(self) -> Iterator[Element]:
        for child in self.children:
            if isinstance(child, Element):
                yield child
                yield from child._descendants()

    # -- serialization ---------------------------------------------------

    def __str__(self) -> str:
        return render_element(self)

    def __repr__(self) -> str:
        return f"<{self.tag}{_render_attrs(self.attrs)}>"
