"""A small CSS selector subset for querying a DOM tree.

The subset mirrors what everyday app code needs: tag names and ``*``,
``#id`` and ``.class`` parts combined on one element (``div#id.foo``),
and parts joined by whitespace (descendants). This is the matcher
behind :meth:`Element.select`, :meth:`Element.select_one`, and
:meth:`Document.querySelector` / :meth:`Document.select`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .util import _is_name_start

if TYPE_CHECKING:
    from .element import Element

__all__ = []


def _selector_parts(selector: str) -> list[str]:
    """Split a selector into its simple parts (descendant combinators)."""
    parts = selector.split()
    if not parts:
        raise ValueError("empty selector")
    return parts


def _sel_name_char(char: str) -> bool:
    """A character of a CSS identifier (tag, id, or class part)."""
    return _is_name_start(char) or "0" <= char <= "9" or char in "_-"


def _matches_simple(element: Element, part: str) -> bool:
    """Match one part of a selector (no whitespace) against ``element``.

    A part is a tag name or ``*`` (optional) followed by any number of
    ``#id`` and ``.class`` parts, e.g. ``div#id.foo``, ``#main``, ``.box``.
    """
    if not part:
        raise ValueError("empty selector part")
    i = 0
    if part[0] == "*":
        i = 1
    elif _is_name_start(part[0]):
        start = i
        while i < len(part) and _sel_name_char(part[i]):
            i += 1
        if element.tag != part[start:i].lower():
            return False
    elif part[0] not in "#.":
        raise ValueError(f"bad selector: {part!r}")
    while i < len(part):
        if part[i] == "#":
            start = i + 1
            i = start
            while i < len(part) and _sel_name_char(part[i]):
                i += 1
            if i == start:
                raise ValueError(f"bad selector: {part!r}")
            if element.attrs.get("id") != part[start:i]:
                return False
        elif part[i] == ".":
            start = i + 1
            i = start
            while i < len(part) and _sel_name_char(part[i]):
                i += 1
            if i == start:
                raise ValueError(f"bad selector: {part!r}")
            if part[start:i] not in element.attrs.get("class", "").split():
                return False
        else:
            raise ValueError(f"bad selector: {part!r}")
    return True


def _matches_selector(element: Element, parts: list[str]) -> bool:
    """Match a chain of simple selectors (descendant combinators): the
    last part against ``element``, the rest against a chain of its
    ancestors."""
    if not _matches_simple(element, parts[-1]):
        return False
    if len(parts) == 1:
        return True
    rest = parts[:-1]
    ancestor = element.parent
    while ancestor is not None:
        if _matches_selector(ancestor, rest):
            return True
        ancestor = ancestor.parent
    return False
