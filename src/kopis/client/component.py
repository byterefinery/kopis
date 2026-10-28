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

A child that is a function (or a coroutine function) is called, with no
arguments, to get the value: a value it returns is appended as if it
were given as a child (a string is parsed as a fragment, an element is
appended, anything else becomes text), and a coroutine it returns is
started with ``aio.run`` — an empty text node reserves the value's
position among the element's children, and when the coroutine resolves,
the placeholder is replaced with the value.
"""

from browser import DOMNode, aio, document

from ..common.component import make_component
from .dom import _fragment_nodes, _native_create_text_node, _scope

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


def _resolve_async(self: DOMNode, coro) -> None:
    """Resolve a child function that returned a coroutine: the value
    arrives when it resolves (see the module docstring)."""
    placeholder = _native_create_text_node("")
    self.appendChild(placeholder)

    async def fill() -> None:
        try:
            value = await coro
        except Exception as exc:  # noqa: BLE001 - a failed child keeps the page alive
            print(f"kopis: a child function failed: {exc}")
            return
        parent = placeholder.parentNode
        if parent is None:
            return
        if isinstance(value, str):
            for node in _fragment_nodes(value):
                parent.insertBefore(node, placeholder)
            parent.removeChild(placeholder)
        elif hasattr(value, "appendChild"):
            parent.replaceChild(value, placeholder)
        else:
            parent.replaceChild(_native_create_text_node(str(value)), placeholder)

    aio.run(fill())


#: The client-side ``Component`` class.
Component = make_component(
    DOMNode,
    lambda tag: document.createElement(tag),
    _enter,
    _resolve_async,
)
