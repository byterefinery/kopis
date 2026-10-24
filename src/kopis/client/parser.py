"""Client-side HTML parsing (Brython, in the browser).

``parse_html`` parses an HTML fragment into brython ``browser.html``
elements and always returns a list of the fragment's top-level
elements (the caller picks the ones it wants, e.g. ``parse_html(...)[0]``).

The parser is deliberately simple. It understands standard HTML markup
— tags with attributes, nested elements, text nodes, comments, and the
void tags (``<br>``, ``<img>``, ...) that never have children — and
nothing more: no Brython template or reactive syntax is interpreted, so
a ``v-on:click`` in the source is kept as an ordinary DOM attribute.
Each standard tag is created from its ``browser.html`` class, looked up
by name in ``browser.html.tags``; tags the module does not know are
created with ``document.createElement`` (as plain elements). Attributes
are set as plain DOM attributes.
"""

import html as _stdlib
import re
from browser import DOMNode, document, html

__all__ = ["parse_html"]

#: Standard HTML void tags: elements that never have children.
#: (Uppercase, matching the tag names the parser works with.)
_VOID_TAGS = frozenset(
    {
        "AREA",
        "BASE",
        "BR",
        "COL",
        "EMBED",
        "HR",
        "IMG",
        "INPUT",
        "LINK",
        "META",
        "PARAM",
        "SOURCE",
        "TRACK",
        "WBR",
    }
)

#: Tags whose content is raw text (ended only by their closing tag).
_RAW_TEXT_TAGS = frozenset({"SCRIPT", "STYLE"})

_RAW_END = {
    tag: re.compile(rf"</{tag.lower()}\s*>", re.IGNORECASE) for tag in _RAW_TEXT_TAGS
}

# A start or end tag: optional closing slash, tag name, attribute string,
# and optional self-closing slash.
_TAG = re.compile(
    r"<"
    r"(/?)?"
    r"([a-zA-Z][a-zA-Z0-9:._-]*)"
    r"((?:\s+[a-zA-Z_:][a-zA-Z0-9:._-]*"
    r"(?:\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s>]+))?)*)"
    r"\s*(/?)>"
)

# One attribute in an attribute string: a name and an optional value
# (double-quoted, single-quoted, or bare).
_ATTR = re.compile(
    r"([a-zA-Z_:][a-zA-Z0-9:._-]*)"
    r"(?:\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+))?"
)


def parse_html(html_str: str) -> list[DOMNode]:
    """Parse an HTML fragment into brython ``browser.html`` elements.

    Returns the top-level elements of the fragment, in order (a list,
    possibly empty). Text outside of any element is ignored.
    """
    return _parse(html_str)


def _parse(html_str: str) -> list[DOMNode]:
    """The top-level elements of the fragment, in order."""
    nodes: list[DOMNode] = []
    stack: list[DOMNode] = []  # open elements, innermost last
    pos = 0
    n = len(html_str)
    while pos < n:
        lt = html_str.find("<", pos)
        if lt == -1:
            _text(stack, html_str[pos:])
            break
        if lt > pos:
            _text(stack, html_str[pos:lt])
        if html_str.startswith("<!--", lt):
            pos = _skip_to(html_str, "-->", lt + 4)
            continue
        if html_str[lt + 1 : lt + 2] in ("!", "?"):
            # A doctype or other ``<!...>``/``<?...>`` construct.
            pos = _skip_to(html_str, ">", lt + 2)
            continue
        m = _TAG.match(html_str, lt)
        if m is None:
            # Not a tag after all: the ``<`` is plain text.
            _text(stack, "<")
            pos = lt + 1
            continue
        pos = m.end()
        closing, name, attrs, self_closing = m.groups()
        name = name.upper()
        if closing:
            _close(stack, name)
            continue
        el = _element(name, attrs)
        if stack:
            stack[-1] <= el
        else:
            nodes.append(el)
        if self_closing or name in _VOID_TAGS:
            continue
        if name in _RAW_TEXT_TAGS:
            end = _raw_end(name, html_str, pos)
            if end > pos:
                el <= html_str[pos:end]
            pos = end
            continue
        stack.append(el)
    return nodes


def _element(name: str, attrs: str) -> DOMNode:
    """A new element of the (uppercased) tag ``name`` with the
    attributes of ``attrs`` (the raw attribute string of its opening
    tag).

    Standard tags use their ``browser.html`` class, looked up by name;
    other tags make a plain element with ``document.createElement``.
    """
    cls = html.tags.get(name)
    if cls is None:
        el = document.createElement(name.lower())
    else:
        el = cls()
    for attr, value in _attr_pairs(attrs):
        el.attrs[attr] = value
    return el


def _attr_pairs(attrs: str) -> list[tuple[str, str]]:
    """The (name, value) pairs of an attribute string, with quotes
    stripped and entities decoded."""
    pairs: list[tuple[str, str]] = []
    for m in _ATTR.finditer(attrs):
        value = m.group(2) or ""
        if len(value) > 1 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        pairs.append((m.group(1), _stdlib.unescape(value)))
    return pairs


def _text(stack: list[DOMNode], text: str) -> None:
    """Append the (decoded) text to the innermost open element.

    Whitespace-only text, and text outside of any element, is
    ignored.
    """
    if stack and text.strip():
        stack[-1] <= _stdlib.unescape(text)


def _close(stack: list[DOMNode], name: str) -> None:
    """Close the innermost open element of the (uppercased) tag
    ``name``.

    Unmatched closing tags are ignored (the parser is lenient).
    """
    for i in range(len(stack) - 1, -1, -1):
        if stack[i].tagName == name:
            del stack[i:]
            return


def _skip_to(s: str, end: str, pos: int) -> int:
    """The position just past the first occurrence of ``end`` at or
    after ``pos`` (the end of ``s`` if there is none)."""
    i = s.find(end, pos)
    return len(s) if i == -1 else i + len(end)


def _raw_end(name: str, s: str, pos: int) -> int:
    """The end of the raw content of the (uppercased) tag ``name``:
    where its closing tag starts, or the end of ``s``."""
    m = _RAW_END[name].search(s, pos)
    return m.start() if m is not None else len(s)
