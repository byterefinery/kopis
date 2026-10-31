"""Stand-ins for the brython ``browser`` module (server side).

In the browser under Brython, ``browser`` is a built-in package exposing
the live page: ``document``, ``window``, ``bind``, ``DOMNode``,
``DOMEvent``, ``html``, ``aio``, ``ajax``, ``timer``, and more. The
server has no live DOM — the browser parses the served HTML and runs
the application code on it — so these stand-ins let unified code run
unmodified, with the brython semantics where they matter:

- :class:`DOMNode` is the stand-in of the brython ``DOMNode`` class
  (the class of every element, and of the document itself): the brython
  element interface works on it — ``append``, ``bind``, ``clone``,
  attribute subscripts, ``+`` / ``*``, ``with`` — but everything is a
  no-op;
- :class:`DOMEvent` is the stand-in of the brython ``DOMEvent`` class
  (events never fire on the server);
- :func:`bind` is the stand-in of the brython ``browser.bind``
  decorator (handlers are never fired);
- :data:`html` is the stand-in of the brython ``browser.html`` builder
  (every call makes a new :class:`DOMNode`);
- :data:`document` is a lazy stand-in of the brython
  ``browser.document`` object: a :class:`DOMNode` of the raw HTML string
  the running application serves;
- :data:`window`, :data:`ajax`, and :data:`timer` are plain
  :class:`~kopis.common.magic.Magic` dummies.

:data:`document` is registered by :meth:`kopis.server.Kopis` through
:func:`set_document`.
"""

from collections.abc import Callable, Iterable, Iterator
from typing import Any

from ..common.magic import Magic, _event_name, _on_decorator

__all__ = [
    "DOMEvent",
    "DOMNode",
    "ajax",
    "bind",
    "document",
    "html",
    "set_document",
    "timer",
    "window",
]


class DOMNode(Magic):
    """A stand-in for a brython ``DOMNode`` (a browser DOM element).

    The brython element interface works on it — ``append`` (the way to
    add children), ``bind``, ``clone``, attribute subscripts, ``+`` /
    ``*``, ``with`` — but everything is a no-op:
    there is no live DOM on the server, so handlers are never fired and
    nothing is rendered. An ``on<event>`` read (``element.onclick``) is
    the no-op decorator of the decorator form: it binds nothing and
    returns the decorated handler.
    """

    _html: str

    def __init__(self, html: str = "") -> None:
        object.__setattr__(self, "_html", html)

    def __getattr__(self, name: str) -> Any:
        # Unknown attributes are stand-in elements as well, so chained
        # DOM code (``document.body.select(...)``) stays a DOMNode. They
        # are cached, so e.g. ``document.body`` is one stable stand-in
        # element, as in brython — except that an ``on<event>`` name is
        # the no-op decorator of the decorator form (see
        # :func:`~kopis.common.magic._on_decorator`): it binds nothing
        # on the server and returns the decorated handler.
        if name.startswith("_"):
            raise AttributeError(name)
        event = _event_name(name)
        if event is not None:
            return _on_decorator(self, event)
        child = DOMNode()
        object.__setattr__(self, name, child)
        return child

    def __str__(self) -> str:
        return self._html if self._html else "<magic DOMNode>"

    __repr__ = __str__

    def __getitem__(self, key: object) -> DOMNode:
        """The value of that attribute (the brython subscript; a
        stand-in on the server: there is no live DOM, so the result is
        always a stand-in element)."""
        return DOMNode()

    def clone(self) -> DOMNode:
        """A stand-in copy of this element (the brython ``clone``)."""
        return DOMNode()

    def createElement(self, tag: str, **attrs: object) -> DOMNode:
        """A new, not yet attached element of type ``tag`` (the brython
        ``createElement``)."""
        return DOMNode()

    def bind(
        self,
        event: str,
        func: Callable[..., Any] | None = None,
        options: None | bool | dict[str, Any] = None,
    ) -> DOMNode | Callable[[Callable[..., Any]], DOMNode]:
        """Add an event listener (the brython ``bind``; no-op on the
        server: there is no live DOM).

        With ``func`` given, returns ``self``; with ``func`` ``None``,
        returns a decorator that binds (does nothing) and, as in
        brython, returns the element itself.
        """
        if func is None:

            def decorator(f: Callable[..., Any]) -> DOMNode:
                self.bind(event, f, options)
                return self

            return decorator
        return self

    def unbind(
        self,
        event: str | None = None,
        *funcs: Callable[..., Any],
    ) -> None:
        """Remove event listeners (the brython ``unbind``; no-op on the
        server)."""
        return

    def events(self, event: str) -> list[Callable[..., Any]]:
        """The handlers bound to ``event`` (empty on the server)."""
        return []

    def bindings(self) -> dict[str, tuple[Callable[..., Any], ...]]:
        """A map of event name to its handlers (empty on the server)."""
        return {}

    def trigger(self, event: str) -> None:
        """Dispatch ``event`` (no-op on the server: there is no live
        DOM)."""
        return

    def reset(self) -> None:
        """Reset a form (no-op on the server)."""
        return

    # The brython aliases of the event methods.
    addEventListener = bind
    removeEventListener = unbind


class DOMEvent(Magic):
    """A stand-in for the brython ``DOMEvent`` class (a browser DOM
    event).

    Never constructed on the server (events do not fire); it exists so
    unified code can name and build the type on both sides.
    """

    type: str

    def __init__(self, type: str = "") -> None:
        object.__setattr__(self, "type", type)


_document: DOMNode | None = None


class _Document(DOMNode):
    """A lazy stand-in of the brython ``browser.document`` object.

    Delegates everything to the document of the running application
    (registered by :func:`set_document`), so ``document`` is one stable
    object that always refers to the current application document, even
    before the application has been created (it fails with a clear
    error then).
    """

    def __init__(self) -> None:
        super().__init__("")

    def _resolve(self) -> DOMNode:
        if _document is None:
            raise RuntimeError("document: no kopis application has been created yet")
        return _document

    def __getattr__(self, name: str) -> Any:
        return getattr(self._resolve(), name)

    def __setattr__(self, name: str, value: object) -> None:
        setattr(self._resolve(), name, value)

    def __getitem__(self, key: object) -> Any:
        return self._resolve()[key]

    def __setitem__(self, key: object, value: object) -> None:
        self._resolve()[key] = value

    def __delitem__(self, key: object) -> None:
        del self._resolve()[key]

    def __iter__(self) -> Iterator[Any]:
        return iter(self._resolve())

    def __len__(self) -> int:
        return len(self._resolve())

    def __contains__(self, id: object) -> bool:
        return id in self._resolve()

    def __str__(self) -> str:
        return str(self._resolve())

    __repr__ = __str__


#: The document of the running application (the brython
#: ``browser.document`` object; a :class:`DOMNode` of the raw HTML
#: string the application serves).
document = _Document()


def set_document(html: str) -> None:
    """Register the document (its raw HTML string) of the running
    application."""
    global _document
    _document = DOMNode(html)


def bind(
    target: DOMNode | str | Iterable[DOMNode],
    event: str,
    options: None | bool | dict[str, Any] = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Bind the decorated function to ``event`` on ``target`` (the
    brython ``browser.bind`` decorator).

    ``target`` is an element, a CSS selector string, or an iterable of
    elements. On the server the binding is a no-op: there is no live
    DOM, so handlers are never fired.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        return func

    return decorator


class _Html:
    """A stand-in for the brython ``browser.html`` builder.

    Every tag call (``html.BUTTON("hi", id="x")``) makes a new
    stand-in :class:`DOMNode`, as in brython; ``html.maketag`` works the
    same way.
    """

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        if name == "tags":
            return {}

        def tag(*args: object, **kwargs: object) -> DOMNode:
            return DOMNode()

        return tag


#: The stand-in of the brython ``browser.html`` builder.
html = _Html()

#: The browser window (a stand-in: the server has no window).
window = Magic()
#: Ajax requests (a stand-in: the server talks HTTP directly).
ajax = Magic()
#: Timers (a stand-in: the server uses asyncio).
timer = Magic()
