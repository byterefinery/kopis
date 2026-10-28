"""The client-side ``Component`` (Brython, in the browser).

The :class:`~kopis.Component` of the client side, built by
:func:`kopis.common.component.make_component` over the brython
``browser.DOMNode`` class: the instance is created with
``document.createElement`` and reclassified into the component class,
so it **is its own root element** — the brython element interface works
on it directly (``<=``, ``+``, ``*``, attribute subscripts, event
handlers, iteration, and the ``with component:`` block form), and it is
usable everywhere an element is (``document.body <= button``, ``k.btn0``
by id, a child of another component).

The ``with component:`` block form appends the component to the
innermost enclosing block when it enters it — unless it was already
appended there when it was created (the auto-append of the
``document.createElement`` extension), in which case it is not appended
a second time.
"""

from browser import DOMNode, document

from ..common.component import make_component
from .dom import _scope

__all__ = ["Component"]


def _enter(self: DOMNode) -> DOMNode:
    """The ``with component:`` block form: open the block on the element
    (see the module docstring)."""
    if _scope and self.parentNode is _scope[-1]:
        # Already a child of the innermost enclosing block (the
        # auto-append of the creation): just open the block.
        _scope.append(self)
        return self
    return DOMNode.__enter__(self)


#: The client-side ``Component`` class.
Component = make_component(
    DOMNode,
    lambda tag: document.createElement(tag),
    _enter,
)
