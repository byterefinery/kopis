"""A minimal pure-Python DOM library, shared by both sides.

Parses valid HTML code into a tree of :class:`Element` and serializes a
tree back to canonical, valid, prettified HTML. Both directions are
strict: only valid HTML is accepted, and only valid HTML is produced.
Everything a browser would only read with recovery — unclosed or
mismatched tags, broken attributes, and dangling end tags — is rejected
with :class:`ParseError`. The library mirrors the two classes of
brython's ``browser`` package, so the same application code works (and
type-checks) on both sides of the web stack: :class:`Document` mirrors
``browser.document`` and :class:`Element` mirrors a brython DOM element,
including the event methods (recorded, never fired — a pure tree has no
live DOM) and the brython special values (``javascript.NULL`` /
``UNDEFINED`` remove elements on assignment).

The modules:

- :mod:`~kopis.common.dom.element` — the :class:`Element` node class
  (children, attributes, ``append`` / ``<=`` / ``+`` / ``*``,
  ``select``, ``get``, ``closest``, ``index``, ``inside``, ``clone``,
  events).
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

from .document import Document
from .element import Element
from .parser import ParseError, parse_fragment, parse_html
from .util import VOID_TAGS

__all__ = [
    "VOID_TAGS",
    "Document",
    "Element",
    "ParseError",
    "parse_fragment",
    "parse_html",
]
