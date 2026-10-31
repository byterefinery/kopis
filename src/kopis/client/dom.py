"""Extensions of the brython DOM interface (client side).

In plain brython, a string appended with ``append`` is added as a single
text node (its markup escaped as visible text), and an event handler
that is a coroutine function is called, returns a coroutine that is
never awaited, and never runs.

This module extends both, once, by monkey-patching the brython
``DOMNode`` class (installed by :func:`install`, called when
:mod:`kopis.client` is imported; pure Python, no Javascript):

- a string appended with ``append`` is first parsed by the browser as
  an HTML fragment, and the fragment's top-level nodes — elements,
  text, and comments — are appended, in order. A string without markup
  still appends a text node, so plain text keeps working as before. A
  ``<script>`` among them (or a script element appended directly) is
  recreated as a fresh script element with the same attributes and
  text, so that it runs when it is inserted: a script moved out of a
  parsed fragment keeps the browser's "already started" mark and would
  never execute, while a freshly created script runs. ``append`` takes
  any number of children, in order;
- a coroutine function passed to ``bind``, to ``addEventListener`` (or
  to the ``browser.bind`` decorator, which goes through them) is
  started with ``aio.run`` when the event fires, so ``await`` works
  inside it::

      async def click(event):
          value = await k.some_server_call(...)
          k.document.append(value)

      k.window.btn.addEventListener("click", click)
- an event handler can also be bound with the attribute syntax
  ``element["on<event>"] = func`` (e.g. ``element["onclick"] = func``):
  it is the same as ``element.addEventListener("<event>", func)`` (a
  coroutine ``func`` is started with ``aio.run``); reading
  ``element["on<event>"]`` gives back the bound handler (the first one,
  if several are bound), and ``element["on<event>"] = None`` unbinds
  the handlers of ``<event>``. Any other subscript is a plain attribute
  get/set, as in brython::

      k.window.btn["onclick"] = click           # same as addEventListener
- the same, with the attribute syntax ``element.on<event> = func``
  (e.g. ``element.onclick = func``): it sets the element's native
  ``on<event>`` handler (as in brython: one handler, readable back, and
  ``element.on<event> = None`` removes it), except that a coroutine
  ``func`` is wrapped so that it is started with ``aio.run`` when the
  event fires — in plain brython it would be called, return a
  coroutine that is never awaited, and never run::

      k.window.btn0.onclick = click             # k.window.btn0 is the
                                                # element with id "btn0"

  (All of the above are the same operation on the client side, which
  has the live DOM: the subscripts, the attribute, and ``bind`` /
  ``addEventListener`` all work as described; on the server they are
  stand-in no-ops, as with everything else on the document.)
- the same, with the decorator form ``@element.on<event>``, read
  through the app's stand-in of the element (``k.window.<id>``;
  :class:`_StandIn`): the read returns a decorator, and applying it to
  a handler is the same as the ``element.on<event> = func`` assignment
  above (a coroutine handler is started with ``aio.run`` when the
  event fires), and the decorated handler is returned::

      @k.window.btn0.onclick
      async def click(event):
          ...                                   # same as k.window.btn0.onclick = click

  The same, for the window itself, through the app's stand-in of the
  window (``k.window``): ``@k.window.onload`` is the same as
  ``k.window.onload = load`` (a coroutine ``load`` is wrapped as above,
  and — set after the ``load`` event has already been dispatched, which
  is always the case, since brython runs the application code on the
  ``load`` event — is called at once, with a synthetic ``Event`` of
  the ``load`` type, as if the event fired at the binding), and the
  decorated handler is returned::

      @k.window.onload
      async def load(event):
          ...                                   # same as k.window.onload = load

  (On the server the same reads — on the stand-in element, the window,
  or an RPC name — return the no-op decorator, as with everything else
  on the stand-ins.)
- the same coroutine wrapping, for the ``on<event>`` attributes of
  Javascript objects (the brython ``JSObject`` class, e.g. the
  ``window``): ``window.on<event> = func`` with a coroutine ``func``
  is wrapped so that it is started with ``aio.run`` when the event
  fires. And the window's ``onload`` handler set after the ``load``
  event has already been dispatched — which is always the case,
  since brython runs the application code on the ``load`` event — is
  called at once, with a synthetic ``Event`` of the ``load`` type,
  as if the event fired at the binding::

      k.window.onload = window_load       # fires at once
      k.onload = window_load              # the same, on the app
- a handler bound to the document's ``DOMContentLoaded`` event after
  it has already been dispatched is called at once, with a synthetic
  ``Event`` of that type — with ``bind`` /
  ``addEventListener`` on the document (as with
  ``k.addEventListener``, the short form for
  ``k.document.addEventListener``), using the event's exact name
  (there is no ``onDOMContentLoaded`` handler property, so the
  ``on<event>`` ways do not apply to it): brython runs the
  application code on the ``load`` event, which comes after
  ``DOMContentLoaded``, so a listener bound from the app code would
  never be called otherwise. As the DOM docs recommend for scripts
  that may run after the event, the decision is made by checking
  ``document.readyState``: if the event has already been dispatched,
  the handler is called once (no listener is registered); otherwise
  the listener is registered as usual. The ``load`` event, by
  contrast, is a window event — it fires on the window, never on the
  document — so it is not a document event at all: it is bound on the
  window (``k.window.onload``, ``k.onload``), not here::

      async def ready(e):
          ...                                     # runs at once

      k.addEventListener("DOMContentLoaded", ready)
- the ``with element:`` block form: entering a ``with`` block appends
  the block's element to the innermost enclosing block element (if
  any), and while the block is active, every element or text node
  created in it — a ``browser.html`` tag call, ``html.text``, or any
  ``document.createElement`` / ``document.createTextNode`` — is
  appended to the block's element as it is created, so an indented
  block of element creation builds the corresponding fragment::

      with document.body:
          with html.BUTTON(id="btn0", class_="btn btn-primary"):
              html.text("Demo 1")

      # is the same as

      document.body.append(
          '<button id="btn0" class="btn btn-primary">Demo 1</button>')

  (On the server the block and the tag calls are stand-in no-ops, as
  with everything else on the document.)
- the ``browser.html`` builder, three additions: a tag name the
  module does not define resolves to its class (``html.button`` is
  ``html.BUTTON``); ``html.text(s)`` makes a text node (the
  ``document.createTextNode`` way, appended to the innermost
  ``with element:`` block element if a block is active); and the
  ``class_`` keyword argument of a tag call is mapped to the
  ``class`` attribute (``class`` is a Python keyword, as in brython's
  ``Class``).

Nothing else about the DOM changes: ``+`` still groups (a string
grouped with ``+`` is still a text node), ``del`` still removes, and
non-coroutine handlers are bound unchanged. As in brython, content
appended to the document goes to its body.
"""

import builtins

from browser import DOMEvent as Event, DOMNode as Node, aio, document, html, window
from collections.abc import Callable, Iterator
from inspect import iscoroutinefunction
from typing import Any

from ..common.magic import _event_name, _on_decorator

__all__ = ["install"]

# The stack of the active ``with element:`` blocks (innermost last):
# entering a block appends the block's element to the innermost
# enclosing block element (if any), and nodes created while a block is
# active (a ``browser.html`` tag call, ``html.text``, or any
# ``document.createElement`` / ``document.createTextNode``) are appended
# to the block's element.
_scope: list[Node] = []

# The original (unpatched) ``document.createElement`` and
# ``document.createTextNode`` — read before the extension patches them:
# ``createElement`` makes the nodes that must not join the innermost
# active ``with element:`` block (the ``<template>`` that parses a
# fragment, a fresh ``<script>`` that replaces a parsed one), and
# ``createTextNode`` makes the placeholder of a coroutine child (see
# :mod:`kopis.client.component`), which is appended to its own element,
# not to the innermost active block.
_native_create_element = document.createElement
_native_create_text_node = document.createTextNode

# The original (unpatched) ``Node.__getitem__`` — read before the
# extension patches it: the window stand-in looks up the document's
# elements by id through it (the patched subscript of the document no
# longer does the id lookup).
_native_getitem = Node.__getitem__


class _StandIn:
    """The app's stand-in of an element of the document
    (``k.window.<id>``).

    It delegates everything to the wrapped element, except that an
    ``on<event>`` read (``k.window.btn0.onclick``) returns the decorator
    of the decorator form: applying it to a handler is the same as the
    corresponding ``on<event>`` assignment (see the module docstring),
    and the decorated handler is returned.
    """

    _target: Any

    def __init__(self, target: Any) -> None:
        object.__setattr__(self, "_target", target)

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        event = _event_name(name)
        if event is not None:
            return _on_decorator(self._target, event)
        return getattr(self._target, name)

    def __setattr__(self, name: str, value: object) -> None:
        setattr(self._target, name, value)

    def __getitem__(self, key: object) -> Any:
        return self._target[key]

    def __setitem__(self, key: object, value: object) -> None:
        self._target[key] = value

    def __delitem__(self, key: object) -> None:
        del self._target[key]

    # The brython DOM operators and protocols, delegated to the wrapped
    # object.

    def __add__(self, other: object) -> Any:
        return self._target + other

    def __mul__(self, other: object) -> Any:
        return self._target * other

    def __iter__(self) -> Iterator[Any]:
        return iter(self._target)

    def __len__(self) -> int:
        return len(self._target)

    def __str__(self) -> str:
        return str(self._target)

    def __repr__(self) -> str:
        return repr(self._target)


class _Window(_StandIn):
    """The app's stand-in of the window (``k.window``).

    As :class:`_StandIn`, an ``on<event>`` read (``k.window.onload``)
    is the decorator of the decorator form. In addition, a name that is
    the id of an element of the document resolves to the stand-in of
    that element (``k.window.btn0`` — the only lookup of the
    document's elements by id); any other name delegates to the window
    (``k.window.location``, ...). The window itself remains available
    as ``browser.window``.
    """

    _elements: dict[str, _StandIn]  # id -> stand-in of the element

    def __init__(self, target: Any) -> None:
        super().__init__(target)
        object.__setattr__(self, "_elements", {})

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        event = _event_name(name)
        if event is not None:
            return _on_decorator(self._target, event)
        # The original (unpatched) brython subscript: the id lookup of
        # the document (the patched subscript of the document no longer
        # does it).
        try:
            element = _native_getitem(document, name)
        except KeyError:
            element = None
        if element is not None:
            view = self._elements.get(name)
            if view is None:
                view = _StandIn(element)
                self._elements[name] = view
            return view
        return getattr(self._target, name)


# ``DOMContentLoaded`` of the document, once dispatched, never fires
# again, and brython runs the application code on the ``load`` event
# — after ``DOMContentLoaded``. A handler bound from app code to it is
# therefore called at once, with a synthetic event, so that it behaves
# as if the event fired at the binding. The ``load`` event, by
# contrast, is a window event: it fires on the window, never on the
# document (a document listener for it never fires), so it is handled
# on the window — ``window.onload`` — and never here.


def _domcontentloaded_passed() -> bool:
    """Whether the document's ``DOMContentLoaded`` event has already
    been dispatched (once the document is no longer loading)."""
    try:
        return document.readyState != "loading"
    except Exception:  # noqa: BLE001 - no live readyState: assume not passed
        return False


def _window_load_passed() -> bool:
    """Whether the window's ``load`` event has already been dispatched
    (once the document is complete)."""
    try:
        return document.readyState == "complete"
    except Exception:  # noqa: BLE001 - no live readyState: assume not passed
        return False


def _synthetic_event(event: str) -> Event:
    """An ``Event`` standing in for an event that has already
    fired."""
    return Event(event)


def _wrap_async(func: Callable[..., Any]) -> Callable[..., Any]:
    """Start a coroutine ``func`` with ``aio.run`` when it is called
    (a plain ``func`` is returned unchanged): in plain brython a
    coroutine handler would be called, return a coroutine that is
    never awaited, and never run."""
    if iscoroutinefunction(func):
        target = func

        def wrapped(*args: object, **kwargs: object) -> None:
            aio.run(target(*args, **kwargs))

        return wrapped
    return func


def _is_script(node: object) -> bool:
    """Whether ``node`` is a ``<script>`` element."""
    return isinstance(node, Node) and getattr(node, "tagName", None) == "SCRIPT"


def _runnable_script(node: Node) -> Node:
    """A fresh script element with the attributes and text of ``node``.

    A ``<script>`` moved out of a parsed fragment (a ``<template>``) or
    built with the ``browser.html`` classes carries the browser's
    "already started" mark and never executes when it is inserted into
    the live document; a script created with ``document.createElement``
    does run when inserted, so the script is recreated before it is
    attached."""
    fresh = _native_create_element("script")
    for name, value in node.attrs.items():
        fresh.attrs[name] = value
    fresh.text = node.text
    return fresh


# The patched ``append`` of :func:`install` (``None`` before it runs):
# nodes created outside the patched creation paths (a fragment's
# elements, a clone) need it as an own property, and are made at
# runtime, after the extension is installed.
_patched_append: Callable[..., Node] | None = None


def _own_append(element: Node) -> None:
    """Set ``append`` as an own property of ``element``, pointing to
    the patched ``append``.

    For an attribute the element's Javascript object already has
    (like ``append``), brython resolves it to the Javascript one,
    whatever class the element has — an own property set on the
    element itself always wins, and brython gives back the original
    Python object when a Python function is read from a Javascript
    object. A no-op before :func:`install` runs."""
    patched = _patched_append
    if patched is None:
        return
    element.append = lambda *args: patched(element, *args)


def _fragment_nodes(html_str: str) -> list[Node]:
    """The top-level nodes of the HTML fragment ``html_str`` (parsed by
    the browser), in order; a top-level ``<script>`` among them is
    recreated, so that it runs when it is inserted."""
    tpl = _native_create_element("template")
    tpl.innerHTML = html_str
    nodes: list[Node] = []
    for node in list(tpl.content):
        if _is_script(node):
            node = _runnable_script(node)
        nodes.append(node)
    for node in nodes:
        # The nodes are created by the browser (not through the patched
        # creation paths): give them the patched append.
        _own_append(node)
    return nodes


def _append_fragment(self: Node, html_str: str) -> Node:
    """Append the top-level nodes of the HTML fragment ``html_str``
    (parsed by the browser), in order; a top-level ``<script>`` among
    them is recreated, so that it runs when it is inserted."""
    # A document node cannot take element children directly; they go
    # to the body.
    target = self.body if self is document else self
    for node in _fragment_nodes(html_str):
        target.append(node)
    return self


def install() -> None:
    """Extend the DOM interface (a no-op if it is already extended)."""
    if getattr(Node, "_kopis_extended", False):
        return

    # The original (unpatched) ``Node.__le__`` — the native brython
    # append of a single child (its ``attach``, which ``<=`` maps to):
    # read before the extension patches the operator.
    _orig_le = Node.__le__
    _orig_bind = Node.bind
    _orig_events = Node.events
    _orig_setitem = Node.__setitem__
    _orig_setattr = Node.__setattr__
    _orig_unbind = Node.unbind
    _orig_clone = Node.clone
    # The class of the Javascript objects (e.g. the window): brython
    # dispatches their attribute sets through its ``__setattr__`, so
    # the same monkey-patch way works for them.
    _jsobj = type(window)
    _orig_jsobj_setattr = _jsobj.__setattr__

    def append(self: Node, *others: object) -> Node:
        """Append one or more children, in order (the brython
        ``append`` method, the way to add children to an element): a
        string is first parsed as an HTML fragment (see the module
        docstring), and a ``<script>`` among the children is
        recreated, so that it runs when it is inserted. Returns
        ``self`` so calls can be chained."""
        for other in others:
            if isinstance(other, str):
                _append_fragment(self, other)
            elif _is_script(other):
                _orig_le(self, _runnable_script(other))
            else:
                _orig_le(self, other)
        return self

    global _patched_append
    _patched_append = append

    def le(self: Node, other: object) -> Node:
        raise TypeError(
            "unsupported operator on an element: use "
            "element.append(child) to append children"
        )

    def clone(self: Node) -> Node:
        """A copy of this element (the brython ``clone``), with the
        patched ``append`` of its own (a copy is a new element)."""
        copy = _orig_clone(self)
        _own_append(copy)
        return copy

    def bind(self: Node, event: str, func=None, options=None) -> object:
        if func is None:
            # The decorator form: the handler is bound when the
            # decorator is applied, through this function again.
            return _orig_bind(self, event, func, options)
        func = _wrap_async(func)
        # The document's ``DOMContentLoaded`` event, once dispatched,
        # never fires again — and brython runs the application code on
        # the ``load`` event, which comes after it: as the DOM docs
        # recommend for scripts that may run after the event (checking
        # ``document.readyState``), call the handler once, with a
        # synthetic event, as if the event fired at the binding.
        # (The ``load`` event is a window event, not a document event:
        # it fires on the window, never on the document, so a
        # document listener for it is registered as usual and never
        # called for the page load.)
        if (
            self is document
            and event == "DOMContentLoaded"
            and _domcontentloaded_passed()
        ):
            func(_synthetic_event(event))
            return self
        return _orig_bind(self, event, func, options)

    def setitem(self: Node, key: object, value: object) -> None:
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

    def getitem(self: Node, key: object) -> object:
        """Read an attribute, or — with an ``on<event>`` key — the
        handler bound with ``element["on<event>"] = func`` (the first
        one, if several are bound)."""
        event = _event_name(key)
        if event is not None:
            handlers = _orig_events(self, event)
            if handlers:
                return handlers[0]
        if self is document and isinstance(key, str):
            # No id lookup on the document: the element with id <key>
            # is k.window.<key> (the app's stand-in of the window).
            raise KeyError(key)
        return _native_getitem(self, key)

    def setattr(self: Node, attr: str, value: object) -> None:
        """Set an attribute, as in brython — except that a coroutine
        function set with an ``on<event>`` attribute (e.g. a
        ``element.onclick = func`` where ``func`` is ``async def``)
        is wrapped so that it is started with ``aio.run`` when the
        event fires: in plain brython it would be called, return a
        coroutine that is never awaited, and never run. The handler
        itself is the element's native ``on<event>`` handler, as in
        brython (one handler; reading it back gives the handler,
        ``element.on<event> = None`` removes it). The document has no
        handler property for ``DOMContentLoaded`` (there is no
        ``onDOMContentLoaded``), and the ``load`` event is a window
        event (it fires on the window, never on the document), so
        ``document.on<event>`` for those remains a plain attribute
        set, as in brython."""
        if _event_name(attr) is not None and iscoroutinefunction(value):
            target = value

            def wrapped(*args: object, **kwargs: object) -> None:
                aio.run(target(*args, **kwargs))

            value = wrapped
        return _orig_setattr(self, attr, value)

    def jsobj_setattr(self: object, attr: str, value: object) -> None:
        """Set an attribute of a Javascript object (a brython
        ``JSObject``, e.g. the ``window``), as in brython — except
        that a coroutine function set with an ``on<event>`` attribute
        is wrapped so that it is started with ``aio.run`` when the
        event fires, and the window's ``onload`` handler set after the
        ``load`` event has already been dispatched — which is always
        the case, since brython runs the application code on the
        ``load`` event — is called at once, with a synthetic event, as
        if the event fired at the binding."""
        if _event_name(attr) is not None and iscoroutinefunction(value):
            value = _wrap_async(value)
        _orig_jsobj_setattr(self, attr, value)
        if (
            self is window
            and attr == "onload"
            and callable(value)
            and _window_load_passed()
        ):
            value(_synthetic_event("load"))

    def enter(self: Node) -> Node:
        """Enter a ``with element:`` block: append ``self`` to the
        innermost enclosing block element (if any), and make ``self``
        the innermost block element, so that the nodes created in the
        block's body are appended to it (see the module docstring)."""
        if _scope:
            _scope[-1].append(self)
        _scope.append(self)
        return self

    def exit(self: Node, *exc_info: object) -> bool:
        """Leave a ``with element:`` block: ``self`` is no longer the
        innermost block element. Exceptions are not suppressed."""
        if _scope and _scope[-1] is self:
            _scope.pop()
        return False

    _orig_create_element = _native_create_element

    def create_element(tag: str, *args: object) -> Node:
        """Create an element (the brython
        ``document.createElement``), appended to the innermost
        ``with element:`` block element if a block is active."""
        element = _orig_create_element(tag, *args)
        _own_append(element)
        if _scope:
            _scope[-1].append(element)
        return element

    def create_text_node(text: str) -> Node:
        """Create a text node (the brython
        ``document.createTextNode``), appended to the innermost
        ``with element:`` block element if a block is active."""
        node = _native_create_text_node(str(text))
        if _scope:
            _scope[-1].append(node)
        return node

    _orig_attribute_mapper = html.attribute_mapper

    def attribute_mapper(attr: str) -> str:
        """Map a tag-call keyword argument to an attribute name (the
        brython ``html.attribute_mapper``), except that the ``class_``
        keyword workaround (``class`` is a Python keyword) is mapped
        to the ``class`` attribute, as brython's ``Class``.
        """
        if attr == "class_":
            return "class"
        return _orig_attribute_mapper(attr)

    def html_getattr(name: str) -> Any:
        """The ``browser.html`` module's attribute fallback: a tag name
        the module does not define (e.g. the lowercase ``html.button``)
        resolves to its class (``html.BUTTON``), if it has one."""
        if not isinstance(name, str) or name.startswith("_"):
            raise AttributeError(name)
        tag = html.tags.get(name.upper())
        if tag is not None:
            return tag
        raise AttributeError(name)

    # The tag classes of the html builder: each is replaced by a
    # subclass that gives the instances it creates the patched
    # ``append`` as an own property. The subclass pretends to live in
    # the ``browser.html`` module, so that the attribute resolution of
    # its instances (including the ones brython itself wraps, which
    # take their class from the live ``html.tags`` mapping) is exactly
    # the one of the original class. The ``__init__`` is a no-op: the
    # tag class's own init already ran inside ``__new__``.
    def wrap_tag_class(cls: Any) -> Any:
        original = cls

        def __new__(cls_: type, *args: object, **kwargs: object) -> Any:
            element = original(*args, **kwargs)
            _own_append(element)
            return element

        def __init__(self: Any, *args: object, **kwargs: object) -> None:
            # ``original``'s init already ran in ``__new__``.
            return

        wrapped: Any = type(
            cls.__name__,
            (cls,),
            {
                "__new__": __new__,
                "__init__": __init__,
            },
        )
        wrapped.__module__ = "browser.html"
        return wrapped

    for _name, _cls in list(html.tags.items()):
        if _name == "IFRAME":
            continue  # the html factory returns a proxy, not an element
        _wrapped = wrap_tag_class(_cls)
        html.tags[_name] = _wrapped
        builtins.setattr(html, _name, _wrapped)

    Node.append = append
    Node.attach = append
    Node.__le__ = le
    Node.bind = bind
    Node.addEventListener = bind
    Node.__setitem__ = setitem
    Node.__getitem__ = getitem
    Node.__setattr__ = setattr
    Node.__enter__ = enter
    Node.__exit__ = exit
    Node.clone = clone
    document.createElement = create_element
    document.createTextNode = create_text_node
    html.attribute_mapper = attribute_mapper
    html.text = create_text_node
    html.__getattr__ = html_getattr
    _jsobj.__setattr__ = jsobj_setattr

    # The elements of the initial document predate the extension: give
    # them the patched ``append`` as well (the document node itself,
    # and every element of the document element's subtree).
    _own_append(document)

    def patch_existing(node: Node) -> None:
        _own_append(node)
        for child in node.child_nodes():
            if child.nodeType == 1:
                patch_existing(child)

    patch_existing(document.documentElement)
    Node._kopis_extended = True
