"""A minimal pure-Python DOM library, shared by both sides.

Parses valid HTML code into a tree of :class:`Element` and serializes a
tree back to canonical, valid, prettified HTML. Both directions are
strict: only valid HTML is accepted, and only valid HTML is produced.
Everything a browser would only read with recovery — unclosed or
mismatched tags, broken attributes, dangling end tags — is rejected
with :class:`ParseError`.

The library mirrors the two classes of brython's ``browser`` package, so
the same application code works (and type-checks) on both sides of the
web stack: :class:`Document` mirrors ``browser.document`` and
:class:`Element` mirrors a brython DOM element. Where brython talks to a
live DOM (events, rendering geometry), the mirror degrades to a no-op or
is omitted: a pure tree has no live events, and the server never lays
out elements.

The modules:

- :mod:`~kopis.common.dom.element` — the :class:`Element` node class
  (children, attributes, ``append`` / ``<=`` / ``+`` / ``*``, ``select``,
  ``get``, ``closest``, ``index``, ``inside``, ``clone``, events).
- :mod:`~kopis.common.dom.parser` — the strict parser
  (:func:`parse_html`, :func:`parse_fragment`, :class:`ParseError`).
- :mod:`~kopis.common.dom.render` — serialization to prettified HTML.
- :mod:`~kopis.common.dom.select` — the small CSS selector subset behind
  ``querySelector`` and ``select``.
- :mod:`~kopis.common.dom.document` — the :class:`Document` class (the
  root element, ``body`` / ``head`` / ``title``, subscripting by ``id``,
  ``<=``).
- :mod:`~kopis.common.dom.util` — the shared tag sets and name grammar.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .document import Document
from .element import Element
from .parser import ParseError, parse_fragment, parse_html
from .util import VOID_TAGS

__all__ = [
    "VOID_TAGS",
    "Document",
    "Element",
    "ParseError",
    "bind",
    "parse_fragment",
    "parse_html",
]


def bind(
    target: Element | str,
    event: str,
    options: None | bool | dict[str, Any] = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Bind the decorated function to ``event`` on ``target`` (the
    brython ``browser.bind`` decorator).

    ``target`` is an element or a CSS selector string. A pure tree has
    no live DOM, so this is a no-op on the server; the handler takes
    effect when the same code runs in the browser.
    """

    def decorator(handler: Callable[..., Any]) -> Callable[..., Any]:
        if isinstance(target, Element):
            target.bind(event, handler, options)
        return handler

    return decorator
