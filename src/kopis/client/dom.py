"""Extensions of the brython DOM interface (client side).

In plain brython, a string appended with ``<=`` is added as a single
text node (its markup escaped as visible text), and an event handler
that is a coroutine function is called, returns a coroutine that is
never awaited, and never runs.

This module extends both, once, by monkey-patching the brython
``DOMNode`` class (installed by :func:`install`, called when
:mod:`kopis.client` is imported; pure Python, no Javascript):

- a string appended with ``<=`` or with ``attach`` is first parsed by
  the browser as an HTML fragment, and the fragment's top-level nodes
  — elements, text, and comments — are appended, in order. A string
  without markup still appends a text node, so plain text keeps working
  as before. A ``<script>`` among them (or a script element appended
  directly with ``<=`` or ``attach``) is recreated as a fresh script
  element with the same attributes and text, so that it runs when it
  is inserted: a script moved out of a parsed fragment keeps the
  browser's "already started" mark and would never execute, while a
  freshly created script runs. The native ``append`` method is left
  untouched (a string appended with it is a text node, as in plain
  brython);
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
- the same, with the attribute syntax ``element.on<event> = func``
  (e.g. ``element.onclick = func``): it sets the element's native
  ``on<event>`` handler (as in brython: one handler, readable back, and
  ``element.on<event> = None`` removes it), except that a coroutine
  ``func`` is wrapped so that it is started with ``aio.run`` when the
  event fires — in plain brython it would be called, return a
  coroutine that is never awaited, and never run::

      k.btn0.onclick = click                    # k.btn0 is k["btn0"]
      k.document.btn0.onclick = click

  (All of the above are the same operation on the client side, which
  has the live DOM: the subscripts, the attribute, and ``bind`` /
  ``addEventListener`` all work as described; on the server they are
  stand-in no-ops, as with everything else on the document.)
- ``document.<id>`` gives the element with that id (the attribute way
  for ``document["<id>"]``, the brython subscript): ``document.btn0``
  is the element with id ``"btn0"``. ``document`` gets this by being
  reclassified into a ``DOMNode`` subclass whose ``__getattr__`` falls
  back to the subscript (the brython ``DOMNode.__getattribute__``
  cannot be patched from Python, so the subclass is the only way in);
  a real document property (``document.body``, ``document.title``, ...)
  still resolves as in brython, and an id with no element raises
  ``AttributeError``, as in brython.

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


def _is_script(node: object) -> bool:
    """Whether ``node`` is a ``<script>`` element."""
    return isinstance(node, DOMNode) and getattr(node, "tagName", None) == "SCRIPT"


def _runnable_script(node: DOMNode) -> DOMNode:
    """A fresh script element with the attributes and text of ``node``.

    A ``<script>`` moved out of a parsed fragment (a ``<template>``) or
    built with the ``browser.html`` classes carries the browser's
    "already started" mark and never executes when it is inserted into
    the live document; a script created with ``document.createElement``
    does run when inserted, so the script is recreated before it is
    attached."""
    fresh = document.createElement("script")
    for name, value in node.attrs.items():
        fresh.attrs[name] = value
    fresh.text = node.text
    return fresh


def _append_fragment(self: DOMNode, html_str: str) -> DOMNode:
    """Append the top-level nodes of the HTML fragment ``html_str``
    (parsed by the browser), in order; a top-level ``<script>`` among
    them is recreated, so that it runs when it is inserted."""
    tpl = document.createElement("template")
    tpl.innerHTML = html_str
    # A document node cannot take element children directly; brython's
    # own attach puts them in the body.
    target = self.body if self is document else self
    for node in list(tpl.content):
        if _is_script(node):
            node = _runnable_script(node)
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
    _orig_setattr = DOMNode.__setattr__
    _orig_unbind = DOMNode.unbind

    def attach(self: DOMNode, other: object) -> DOMNode:
        if isinstance(other, str):
            return _append_fragment(self, other)
        target = self.body if self is document else self
        if _is_script(other):
            other = _runnable_script(other)
        target.appendChild(other)
        return self

    def le(self: DOMNode, other: object) -> DOMNode:
        if isinstance(other, str):
            return _append_fragment(self, other)
        if _is_script(other):
            other = _runnable_script(other)
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

    def setattr(self: DOMNode, attr: str, value: object) -> None:
        """Set an attribute, as in brython — except that a coroutine
        function set with an ``on<event>`` attribute (e.g. a
        ``element.onclick = func`` where ``func`` is ``async def``)
        is wrapped so that it is started with ``aio.run`` when the
        event fires: in plain brython it would be called, return a
        coroutine that is never awaited, and never run. The handler
        itself is the element's native ``on<event>`` handler, as in
        brython (one handler; reading it back gives the handler,
        ``element.on<event> = None`` removes it)."""
        if _event_name(attr) is not None and iscoroutinefunction(value):
            target = value

            def wrapped(*args: object, **kwargs: object) -> None:
                aio.run(target(*args, **kwargs))

            value = wrapped
        return _orig_setattr(self, attr, value)

    class _Document(DOMNode):
        """The brython ``document``, with attribute access by element
        id: ``document.btn0`` is the element with id ``"btn0"`` (the
        attribute way for ``document["btn0"]``).

        A subclass of ``DOMNode`` whose ``__getattr__`` is consulted
        only when the ``DOMNode.__getattribute__`` of the base raises
        ``AttributeError`` (brython combines the two when it builds the
        class), and that falls back to the subscript — the brython
        id lookup. A real document property (``body``, ``title``, ...)
        resolves before ``__getattr__`` is consulted, and an id with no
        element keeps raising ``AttributeError``.
        """

        def __getattr__(self, name: str) -> DOMNode:
            if name.startswith("_"):
                raise AttributeError(name)
            try:
                return _orig_getitem(self, name)
            except KeyError:
                raise AttributeError(name)

    DOMNode.attach = attach
    DOMNode.__le__ = le
    DOMNode.bind = bind
    DOMNode.addEventListener = bind
    DOMNode.__setitem__ = setitem
    DOMNode.__getitem__ = getitem
    DOMNode.__setattr__ = setattr
    # Give document the attribute-by-id access. A plain
    # ``document.__class__ = _Document`` goes through the patched
    # ``__setattr__`` above and is lost, so the object protocol is used.
    object.__setattr__(document, "__class__", _Document)
    DOMNode._kopis_extended = True
