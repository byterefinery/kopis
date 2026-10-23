"""A strict parser of valid HTML code.

Parses valid HTML into a tree of :class:`~kopis.common.dom.element.Element`
and text nodes, rejecting everything a browser would only read with
recovery (unclosed or mismatched tags, broken attributes, dangling end
tags) with :class:`ParseError`. The content of raw-text elements
(``script``, ``style``, ``textarea``) is read verbatim up to the end
tag, so e.g. Python code inside a ``<script>`` tag may freely contain
``<``.

:func:`parse_html` parses a complete document (one root element, with an
optional leading ``<!DOCTYPE ...>``) and returns a
:class:`~kopis.common.dom.document.Document`; :func:`parse_fragment`
parses a snippet and returns its children (elements and text nodes).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, NoReturn

from .document import Document
from .util import _RAW_TEXT_TAGS, _WS, VOID_TAGS, _is_name_char, _is_name_start

if TYPE_CHECKING:
    from .element import Element

__all__ = ["ParseError", "parse_fragment", "parse_html"]


class ParseError(ValueError):
    """Raised when the input is not valid HTML."""


_NAMED_ENTITIES: dict[str, str] = {
    "amp": "&",
    "apos": "'",
    "gt": ">",
    "lt": "<",
    "quot": '"',
    "nbsp": "\u00a0",
    "copy": "\u00a9",
    "reg": "\u00ae",
    "trade": "\u2122",
    "laquo": "\u00ab",
    "raquo": "\u00bb",
    "lsaquo": "\u2039",
    "rsaquo": "\u203a",
    "lsquo": "\u2018",
    "rsquo": "\u2019",
    "ldquo": "\u201c",
    "rdquo": "\u201d",
    "mdash": "\u2014",
    "ndash": "\u2013",
    "hellip": "\u2026",
    "bull": "\u2022",
    "middot": "\u00b7",
    "times": "\u00d7",
    "divide": "\u00f7",
    "deg": "\u00b0",
    "plusmn": "\u00b1",
    "frac12": "\u00bd",
    "frac14": "\u00bc",
    "frac34": "\u00be",
    "cent": "\u00a2",
    "pound": "\u00a3",
    "yen": "\u00a5",
    "euro": "\u20ac",
    "sect": "\u00a7",
    "para": "\u00b6",
    "dagger": "\u2020",
    "Dagger": "\u2021",
    "iexcl": "\u00a1",
    "iquest": "\u00bf",
    "szlig": "\u00df",
    "ordf": "\u00aa",
    "ordm": "\u00ba",
    "sup1": "\u00b9",
    "sup2": "\u00b2",
    "sup3": "\u00b3",
}


def _decode_entities(text: str) -> str:
    """Decode the entities of ``text``, raising :class:`ParseError` on
    an invalid one (a bare ``&`` not starting an entity stays literal)."""
    out: list[str] = []
    i = 0
    end = len(text)
    while i < end:
        if text[i] != "&":
            out.append(text[i])
            i += 1
            continue
        semi = text.find(";", i + 1, i + 33)
        if semi == -1:
            out.append("&")
            i += 1
            continue
        body = text[i + 1 : semi]
        first = body[:1]
        if first == "#":
            value = _numeric_entity(body[1:])
            if value is None:
                raise ParseError(f"invalid numeric entity &{body};")
        elif _is_name_start(first):
            value = _NAMED_ENTITIES.get(body)
            if value is None:
                raise ParseError(f"unknown entity &{body};")
        else:
            out.append("&")
            i += 1
            continue
        out.append(value)
        i = semi + 1
    return "".join(out)


def _numeric_entity(digits: str) -> str | None:
    """The character of a numeric entity body (after ``#``), or ``None``
    if it is not a valid character reference."""
    if digits[:1] in ("x", "X"):
        radix, rest = 16, digits[2:]
    else:
        radix, rest = 10, digits
    if not rest:
        return None
    for char in rest:
        if not ("0" <= char <= "9" or (radix == 16 and "a" <= char.lower() <= "f")):
            return None
    code = int(rest, radix)
    if code == 0 or 0xD800 <= code <= 0xDFFF or code > 0x10FFFF:
        return None
    return chr(code)


class _Parser:
    """A strict, character-by-character parser of valid HTML."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.pos = 0
        self.end = len(text)

    def fail(self, message: str) -> NoReturn:
        line = self.text.count("\n", 0, self.pos) + 1
        column = self.pos - self.text.rfind("\n", 0, self.pos)
        raise ParseError(f"{message} (line {line}, column {column})")

    def skip_ws(self) -> None:
        while self.pos < self.end and self.text[self.pos] in _WS:
            self.pos += 1

    def peek(self) -> str:
        if self.pos >= self.end:
            self.fail("unexpected end of input")
        return self.text[self.pos]

    def read_name(self, what: str) -> str:
        if not _is_name_start(self.peek()):
            self.fail(f"expected a {what}")
        start = self.pos
        while self.pos < self.end and _is_name_char(self.text[self.pos]):
            self.pos += 1
        return self.text[start : self.pos].lower()

    def parse_document(self) -> Element:
        """Parse a complete document: one root element, with an optional
        leading ``<!DOCTYPE ...>`` and surrounding whitespace/comments."""
        self._skip_prolog()
        if self.text[self.pos : self.pos + 9].lower() == "<!doctype":
            close = self.text.find(">", self.pos)
            if close == -1:
                self.fail("unterminated <!DOCTYPE>")
            self.pos = close + 1
            self._skip_prolog()
        root = self._parse_element()
        self._skip_prolog()
        if self.pos != self.end:
            self.fail("unexpected content after the root element")
        return root

    def _skip_prolog(self) -> None:
        """Skip whitespace and comments (the document prolog)."""
        while True:
            self.skip_ws()
            if self.text.startswith("<!--", self.pos):
                self._skip_comment()
                continue
            break

    def parse_fragment(self) -> list[Element | str]:
        """Parse a fragment: a sequence of elements and text."""
        items: list[Element | str] = []
        text: list[str] = []
        while self.pos < self.end:
            if self.text[self.pos] == "<":
                if text:
                    items.append("".join(text))
                    text = []
                if self.text.startswith("<!--", self.pos):
                    self._skip_comment()
                elif self.text.startswith("</", self.pos):
                    self.fail("unexpected end tag in a fragment")
                elif self.text.startswith("<!", self.pos):
                    self.fail("invalid markup; only comments are allowed here")
                elif self.text.startswith("<?", self.pos):
                    self.fail("processing instructions are not allowed")
                else:
                    items.append(self._parse_element())
            else:
                text.append(self._read_text())
        if text:
            items.append("".join(text))
        return items

    def _read_text(self) -> str:
        """Read text up to the next ``<`` (entities decoded)."""
        start = self.pos
        while self.pos < self.end and self.text[self.pos] != "<":
            self.pos += 1
        return _decode_entities(self.text[start : self.pos])

    def _skip_comment(self) -> None:
        """Skip a ``<!-- ... -->`` comment (``pos`` is on the ``<``)."""
        close = self.text.find("-->", self.pos)
        abrupt = self.text.find("--!>", self.pos)
        if close == -1 and abrupt == -1:
            self.fail("unterminated comment")
        if close != -1 and (abrupt == -1 or close < abrupt):
            self.pos = close + 3
        else:
            self.pos = abrupt + 4

    def _parse_element(self) -> Element:
        """Parse one element, starting at its ``<``."""
        # Local import: element and parser need each other at runtime.
        from .element import Element

        if self.peek() != "<":
            self.fail("expected '<'")
        self.pos += 1
        tag = self.read_name("tag name")
        element = Element(tag)
        self_closing = False
        while True:
            self.skip_ws()
            char = self.peek()
            if char == ">":
                self.pos += 1
                break
            if char == "/":
                self.pos += 1
                self.skip_ws()
                if self.peek() != ">":
                    self.fail("expected '>' after '/'")
                self.pos += 1
                self_closing = True
                break
            name = self.read_name("attribute name")
            self.skip_ws()
            if self.peek() != "=":
                self.fail(f"expected '=' after attribute {name!r}")
            self.pos += 1
            self.skip_ws()
            value = self._read_value()
            if name in element.attrs:
                self.fail(f"duplicate attribute {name!r} in <{tag}>")
            element.attrs[name] = value
        if self_closing and tag not in VOID_TAGS:
            self.fail(f"<{tag}> cannot be closed with '/>'")
        if tag in _RAW_TEXT_TAGS:
            self._parse_raw_children(element)
        elif tag not in VOID_TAGS:
            self._parse_children(element)
        return element

    def _read_value(self) -> str:
        """Read an attribute value: quoted, or an unquoted token."""
        char = self.peek()
        if char in "\"'":
            start = self.pos + 1
            pos = start
            while pos < self.end and self.text[pos] != char:
                pos += 1
            if pos >= self.end:
                self.fail(f"unterminated attribute value (expected {char})")
            value = _decode_entities(self.text[start:pos])
            self.pos = pos + 1
            return value
        start = self.pos
        while self.pos < self.end:
            char = self.text[self.pos]
            if char in _WS or char in "\"'<>=`":
                break
            self.pos += 1
        if self.pos == start:
            self.fail("expected an attribute value")
        return _decode_entities(self.text[start : self.pos])

    def _parse_raw_children(self, element: Element) -> None:
        """Parse the raw text content of a raw-text element up to its
        end tag (``<`` is literal, entities are not decoded)."""
        target = f"</{element.tag}"
        lower = self.text.lower()
        search = self.pos
        while True:
            idx = lower.find(target, search)
            if idx == -1:
                self.fail(f"unclosed <{element.tag}>")
            k = idx + len(target)
            while k < self.end and self.text[k] in _WS:
                k += 1
            if k < self.end and self.text[k] == ">":
                element.children.append(self.text[self.pos : idx])
                self.pos = k + 1
                return
            search = k  # a different tag name; keep scanning

    def _parse_children(self, element: Element) -> None:
        """Parse the children of ``element`` up to its end tag."""
        while True:
            if self.pos >= self.end:
                self.fail(f"unclosed <{element.tag}>")
            if self.text.startswith("<!--", self.pos):
                self._skip_comment()
                continue
            if self.text.startswith("</", self.pos):
                self._read_end_tag(element.tag)
                return
            if self.text.startswith("<!", self.pos):
                self.fail("invalid markup; only comments are allowed here")
            if self.text.startswith("<?", self.pos):
                self.fail("processing instructions are not allowed")
            if self.text[self.pos] == "<":
                child = self._parse_element()
                child.parent = element
                element.children.append(child)
                continue
            text = self._read_text()
            if text:
                element.children.append(text)

    def _read_end_tag(self, expected: str) -> None:
        """Read ``</name>`` and check that ``name`` is ``expected``."""
        self.pos += 2
        name = self.read_name("tag name")
        if name != expected:
            self.fail(f"mismatched end tag </{name}>; expected </{expected}>")
        self.skip_ws()
        if self.peek() != ">":
            self.fail(f"expected '>' in </{name}>")
        self.pos += 1


def parse_html(text: str) -> Document:
    """Parse a complete HTML document and return it as a
    :class:`~kopis.common.dom.document.Document`.

    The document is a single root element (typically ``<html>``), with an
    optional leading ``<!DOCTYPE ...>`` and surrounding whitespace.
    Raises :class:`ParseError` if the input is not valid HTML.
    """
    return Document(_Parser(text).parse_document())


def parse_fragment(text: str) -> list[Element | str]:
    """Parse an HTML fragment (a sequence of elements and text).

    Raises :class:`ParseError` if the input is not valid HTML.
    """
    return _Parser(text).parse_fragment()
