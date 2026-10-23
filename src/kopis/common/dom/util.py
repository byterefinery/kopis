"""Shared grammar constants and name helpers of the DOM library.

This is the leaf module of :mod:`kopis.common.dom`: the tag sets and
the tag/attribute name grammar shared by the parser, the serializer,
and the selector matcher.
"""

from __future__ import annotations

__all__ = ["VOID_TAGS"]

#: Whitespace characters of the HTML grammar.
_WS = " \t\n\r\f\v"

#: Tags that never have children or an end tag.
VOID_TAGS: frozenset[str] = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)

#: Tags whose text is serialized as-is (no whitespace normalization,
#: no escaping).
_RAW_TAGS: frozenset[str] = frozenset({"pre", "script", "style", "textarea"})

#: Tags whose content is raw text: parsed verbatim up to the end tag
#: (``<`` is literal, entities are not decoded).
_RAW_TEXT_TAGS: frozenset[str] = frozenset({"script", "style", "textarea"})


def _is_name_start(char: str) -> bool:
    return "a" <= char <= "z" or "A" <= char <= "Z"


def _is_name_char(char: str) -> bool:
    return _is_name_start(char) or "0" <= char <= "9" or char in "-_.:"


def _check_name(name: str, what: str) -> str:
    """Validate a tag or attribute name and return it in lowercase."""
    if not name or not _is_name_start(name[0]):
        raise ValueError(f"invalid {what}: {name!r}")
    for char in name[1:]:
        if not _is_name_char(char):
            raise ValueError(f"invalid {what}: {name!r}")
    return name.lower()
