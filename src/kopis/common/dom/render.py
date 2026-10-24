"""Serialization of a DOM tree to canonical, valid, prettified HTML.

Trees are serialized two ways: :func:`render_inline` renders a node on
one line (as the ``html`` property of its parent would), and
:func:`render_element` renders an element as an indented, prettified
tree (as ``str()`` of the element or of the document would). Text
whitespace is collapsed (single spaces at the edges in inline mode),
text and attribute values are escaped, and the content of raw tags
(``pre``, ``script``, ``style``, ``textarea``) is serialized as-is.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .util import VOID_TAGS, _RAW_TAGS, _WS

if TYPE_CHECKING:
    from .element import Element

__all__ = ["render_element", "render_inline"]

_INDENT = "    "


def _collapse_ws(text: str) -> str:
    """Collapse every run of whitespace to a single space (edges drop)."""
    return " ".join(text.split())


def _collapse_inline(text: str) -> str:
    """Collapse internal whitespace runs, keeping one space at each end
    that has whitespace (inline text must not swallow its gaps)."""
    if not text.strip():
        return " " if text else ""
    collapsed = _collapse_ws(text)
    if text[0] in _WS:
        collapsed = " " + collapsed
    if text[-1] in _WS:
        collapsed = collapsed + " "
    return collapsed


def _escape_text(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _escape_attr(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _render_attrs(attrs: dict[str, str]) -> str:
    if not attrs:
        return ""
    return " " + " ".join(
        f'{name}="{_escape_attr(value)}"' for name, value in attrs.items()
    )


def _render_text(tag: str, text: str, block: bool) -> str:
    """Serialize a text node of ``tag``.

    ``block`` mode (prettified tree) collapses whitespace fully; inline
    mode keeps single spaces at the edges. Raw tags are serialized as-is.
    """
    if tag in _RAW_TAGS:
        return text
    collapsed = _collapse_ws(text) if block else _collapse_inline(text)
    return _escape_text(collapsed)


def render_inline(node: Element | str, tag: str) -> str:
    """Serialize a child node of an element (``tag``) on one line.

    ``node`` is an element or a text node (a string); ``tag`` is the tag
    of the node's parent (it determines how a text node is collapsed).
    """
    if isinstance(node, str):
        return _render_text(tag, node, block=False)
    return _render_element_inline(node)


def _render_element_inline(element: Element) -> str:
    """Serialize an element on one line."""
    if element.tag in VOID_TAGS:
        return f"<{element.tag}{_render_attrs(element.attrs)}/>"
    inner = "".join(render_inline(child, element.tag) for child in element._nodes)
    return f"<{element.tag}{_render_attrs(element.attrs)}>{inner}</{element.tag}>"


def render_element(element: Element, indent: int = 0) -> str:
    """Serialize an element as a prettified (indented) tree."""
    pad = _INDENT * indent
    attrs = _render_attrs(element.attrs)
    if element.tag in VOID_TAGS:
        return f"{pad}<{element.tag}{attrs}/>"
    if not element._nodes:
        return f"{pad}<{element.tag}{attrs}></{element.tag}>"
    texts = [child for child in element._nodes if isinstance(child, str)]
    if len(texts) == len(element._nodes):
        text = _render_text(element.tag, "".join(texts), block=True)
        return f"{pad}<{element.tag}{attrs}>{text}</{element.tag}>"
    lines = [f"{pad}<{element.tag}{attrs}>"]
    child_pad = _INDENT * (indent + 1)
    for child in element._nodes:
        if isinstance(child, str):
            text = _render_text(element.tag, child, block=True)
            if text:
                lines.append(f"{child_pad}{text}")
        else:
            lines.append(render_element(child, indent + 1))
    lines.append(f"{pad}</{element.tag}>")
    return "\n".join(lines)
