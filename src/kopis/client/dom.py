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

Nothing else about the DOM changes: ``+`` still groups (a string
grouped with ``+`` is still a text node), ``del`` still removes, and
non-coroutine handlers are bound unchanged. As in brython, content
appended to the document goes to its body.
"""

from browser import DOMNode, aio, document
from inspect import iscoroutinefunction

__all__ = ["install"]


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

    DOMNode.attach = attach
    DOMNode.__le__ = le
    DOMNode.bind = bind
    DOMNode.addEventListener = bind
    DOMNode._kopis_extended = True
