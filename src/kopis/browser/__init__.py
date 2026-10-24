"""The ``browser`` package of kopis (server side).

In the browser under Brython, ``browser`` is a built-in package exposing
the live page: ``document``, ``window``, ``bind``, ``aio``, ... Under
CPython this package is aliased to the top-level name ``browser`` (see
:mod:`kopis`) so unified code can ``from browser import document, bind``
on both sides, with the real built-in module taking precedence in the
browser.

The essentials are real:

- :data:`document` — a lazy proxy of the document of the running
  application (the server-side DOM tree implementing the brython DOM
  interface; registered by :meth:`kopis.server.Kopis`);
- :data:`DOMNode` — the server-side element class;
- :func:`bind` — the brython ``browser.bind`` decorator (element, CSS
  selector string, or iterable of elements); handlers are recorded on
  the elements (see :meth:`kopis.common.dom.Element.bind`) but never
  fired: a pure tree has no live DOM.

Everything else is a :class:`~kopis.common.magic.Magic` dummy, so code
that touches browser-only objects does not complain on the server.
"""

from collections.abc import Callable, Iterable, Iterator
from typing import Any

from ..common.dom import Document, Element
from ..common.magic import Magic

__all__ = ["DOMEvent", "DOMNode", "bind", "document", "set_document"]

_document: Document | None = None


def set_document(doc: Document) -> None:
    """Register the document of the running application."""
    global _document
    _document = doc


class _Document:
    """A lazy proxy of ``browser.document``.

    Resolves to the document of the running application on first use, so
    ``from browser import document`` works before the application exists
    (and fails with a clear error if it is used before it is created).
    """

    def _resolve(self) -> Document:
        if _document is None:
            raise RuntimeError(
                "browser.document: no kopis application has been created"
            )
        return _document

    def __getattr__(self, name: str) -> Any:
        return getattr(self._resolve(), name)

    def __setattr__(self, name: str, value: object) -> None:
        setattr(self._resolve(), name, value)

    def __getitem__(self, key: str) -> Element:
        return self._resolve()[key]

    def __setitem__(self, key: str, value: object) -> None:
        self._resolve()[key] = value

    def __delitem__(self, key: str) -> None:
        del self._resolve()[key]

    def __le__(self, content: object) -> None:
        self._resolve() <= content

    def __iter__(self) -> Iterator[Element | str]:
        return iter(self._resolve())

    def __len__(self) -> int:
        return len(self._resolve())

    def __contains__(self, id: object) -> bool:
        return id in self._resolve()

    def __str__(self) -> str:
        return str(self._resolve())

    __repr__ = __str__


#: The document of the running application (the brython
#: ``browser.document``).
document = _Document()
#: The server-side element class (the brython ``browser.DOMNode``).
DOMNode = Element


class DOMEvent:
    """Stand-in for the brython ``browser.DOMEvent``.

    Never constructed on the server (events do not fire); it exists so
    unified code can name the type on both sides.
    """

    def __init__(self, type: str = "") -> None:
        self.type = type


def bind(
    target: Element | str | Iterable[Element],
    event: str,
    options: None | bool | dict[str, Any] = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Bind the decorated function to ``event`` on ``target`` (the
    brython ``browser.bind`` decorator).

    ``target`` is an element, a CSS selector string, or an iterable of
    elements. On the server the handlers are recorded on the elements
    (see :meth:`kopis.common.dom.Element.bind`) but never fired: there
    is no live DOM.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if isinstance(target, str):
            elements = document.querySelectorAll(target)
        elif isinstance(target, Element):
            elements = [target]
        else:
            elements = list(target)
        for element in elements:
            element.bind(event, func, options)
        return func

    return decorator


def __getattr__(name: str) -> Magic:
    # Any other (non-essential) name is a dummy stand-in.
    if name.startswith("_"):
        raise AttributeError(name)
    return Magic()
