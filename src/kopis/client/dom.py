"""Extensions of the brython DOM interface (client side).

In plain brython, a string appended with ``<=`` is added as a single
text node (its markup escaped as visible text), and an event handler
that is a coroutine function is called, returns a coroutine that is
never awaited, and never runs.

This module extends both, once, by monkey-patching the brython
``DOMNode`` class (installed by :func:`install`, called when
:mod:`kopis.client` is imported; pure Python, no Javascript):

- a string appended with ``<=`` or with ``attach`` is first parsed by
  the browser as an HTML fragment (nothing is executed), and the
  fragment's top-level nodes — elements, text, and comments — are
  appended, in order. A string without markup still appends a text
  node, so plain text keeps working as before. The native ``append``
  method is left untouched (a string appended with it is a text node,
  as in plain brython);
- a coroutine function passed to ``bind``, to ``addEventListener`` (or
  to the ``browser.bind`` decorator, which goes through them) is
  started with ``aio.run`` when the event fires, so ``await`` works
  inside it::

      async def click(event):
          value = await k.some_server_call(...)
          k.document <= value

      k.document["btn"].addEventListener("click", click)
- an event handler can also be bound with the attribute syntax
  ``element["on<event>"] = func`` (e.g. ``element["onclick"] = func``):
  it is the same as ``element.addEventListener("<event>", func)`` (a
  coroutine ``func`` is started with ``aio.run``); reading
  ``element["on<event>"]`` gives back the bound handler (the first one,
  if several are bound), and ``element["on<event>"] = None`` unbinds
  the handlers of ``<event>``. Any other subscript is a plain attribute
  get/set, as in brython::

      k.document["btn"]["onclick"] = click      # same as addEventListener
      k["btn"]["onclick"] = click              # k["id"] is k.document["id"]

Nothing else about the DOM changes: ``+`` still groups (a string
grouped with ``+`` is still a text node), ``del`` still removes, and
non-coroutine handlers are bound unchanged. As in brython, content
appended to the document goes to its body.
"""

from browser import DOMNode, aio, document
from inspect import iscoroutinefunction

__all__ = ["install"]


def _event_name(key: object) -> str | None:
    """The event name hidden behind an ``on<event>`` key (``None`` if
    ``key`` is not such a key)."""
    if isinstance(key, str) and key.startswith("on") and len(key) > 2:
        return key[2:]
    return None


def _append_fragment(self: DOMNode, html_str: str) -> DOMNode:
    """Append the top-level nodes of the HTML fragment ``html_str``
    (parsed by the browser; nothing is executed), in order."""
    tpl = document.createElement("template")
    tpl.innerHTML = html_str
    # A document node cannot take element children directly; brython's
    # own attach puts them in the body.
    target = self.body if self is document else self
    for node in list(tpl.content):
        target.appendChild(node)
    return self


def install() -> None:
    """Extend the DOM interface (a no-op if it is already extended)."""
    if getattr(DOMNode, "_kopis_extended", False):
        return

    _orig_le = DOMNode.__le__
    _orig_bind = DOMNode.bind
    _orig_events = DOMNode.events
    _orig_getitem = DOMNode.__getitem__
    _orig_setitem = DOMNode.__setitem__
    _orig_unbind = DOMNode.unbind

    def attach(self: DOMNode, other: object) -> DOMNode:
        if isinstance(other, str):
            return _append_fragment(self, other)
        target = self.body if self is document else self
        target.appendChild(other)
        return self

    def le(self: DOMNode, other: object) -> DOMNode:
        if isinstance(other, str):
            return _append_fragment(self, other)
        return _orig_le(self, other)

    def bind(self: DOMNode, event: str, func=None, options=None) -> object:
        if func is not None and iscoroutinefunction(func):
            target = func

            def wrapped(*args: object, **kwargs: object) -> None:
                aio.run(target(*args, **kwargs))

            func = wrapped
        return _orig_bind(self, event, func, options)

    def setitem(self: DOMNode, key: object, value: object) -> None:
        """Set an attribute, or — with an ``on<event>`` key — an event
        handler: ``element["on<event>"] = func`` is the same as
        ``element.addEventListener("<event>", func)`` (a coroutine
        ``func`` is started with ``aio.run`` when the event fires), and
        ``element["on<event>"] = None`` unbinds the handlers of
        ``<event>``. Any other key is a plain attribute set, as in
        brython."""
        event = _event_name(key)
        if event is not None:
            if value is None:
                _orig_unbind(self, event)
                return
            if callable(value):
                bind(self, event, value)
                return
        return _orig_setitem(self, key, value)

    def getitem(self: DOMNode, key: object) -> object:
        """Read an attribute, or — with an ``on<event>`` key — the
        handler bound with ``element["on<event>"] = func`` (the first
        one, if several are bound)."""
        event = _event_name(key)
        if event is not None:
            handlers = _orig_events(self, event)
            if handlers:
                return handlers[0]
        return _orig_getitem(self, key)

    DOMNode.attach = attach
    DOMNode.__le__ = le
    DOMNode.bind = bind
    DOMNode.addEventListener = bind
    DOMNode.__setitem__ = setitem
    DOMNode.__getitem__ = getitem
    DOMNode._kopis_extended = True
