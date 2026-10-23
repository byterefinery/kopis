"""A live view of the HTML document served at ``/`` (server side).

The document is stored as a string — assigned to ``k.document`` or read
from ``index.html`` in the root directory — and parsed with the minimal
DOM library of :mod:`kopis.common.dom`. Look up an element by tag name
with either subscripting or attribute access, or by CSS selector with
:meth:`querySelector`; both return the
:class:`~kopis.common.dom.Element` of the parsed tree, so all of the
minimal DOM library works on it (``append``, ``<=``, ``attrs``,
``select``, ...). Element mutations edit the parsed tree, and the
served document is always the (re-)serialized tree, so the browser
receives a canonical, valid form of the document::

    k.document["head"].append('<meta name="viewport" content="...">')
    with k.document.body as el:
        el.append('<script type="text/javascript" src="app.js"></script>')
"""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Self

from ..common import dom

if TYPE_CHECKING:
    from .app import Kopis

__all__ = ["Document", "_Noop"]


class Document:
    """A live view of the HTML document served at ``/``.

    Elements are looked up by tag name (``k.document.body`` or
    ``k.document["body"]``) or by CSS selector (``querySelector``), and
    are the :class:`~kopis.common.dom.Element` objects of the parsed
    tree itself.
    """

    def __init__(self, owner: Kopis) -> None:
        self._owner = owner

    def _element(self, name: str) -> dom.Element:
        tag = self._owner._parse().querySelector(name)
        if tag is None:
            raise KeyError(f"no <{name}> element in the document")
        return tag

    def querySelector(self, selector: str) -> dom.Element | None:
        """Return the first element matching ``selector``, or ``None``."""
        return self._owner._parse().querySelector(selector)

    def __getitem__(self, name: str) -> dom.Element:
        return self._element(name)

    def __getattr__(self, name: str) -> dom.Element:
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
        """Append ``content`` to the document (its body)."""
        self.body <= content  # noqa: B015 (<= appends to the document)

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

    def append(self, *fragments: str) -> Self:
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
