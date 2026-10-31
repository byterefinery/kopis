"""The client-side ``Component`` (Brython, in the browser).

The :class:`~kopis.Component` of the client side, built by
:func:`kopis.common.component.make_component` over the brython
``browser.DOMNode`` class: the instance is created with
``document.createElement`` and reclassified into the component class,
so it **is its own root element** — the brython element interface works
on it directly (``append``, ``+``, ``*``, attribute subscripts, event
handlers, iteration, and the ``with component:`` block form), and it is
usable everywhere an element is (``document.body.append(button)``,
``k.window.btn0`` by id, a child of another component).

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

A child that is a function in an active effect scope
(``with k.effect():``) is reactive, in the spirit of solidjs: the value
is read through the scope (a signal it reads registers the read as an
observer of the signal), and is held in the element's children — the
nodes of the current value, in order — that are replaced in place
whenever one of the signals it reads changes (the read is re-done, and
the new value — a value or the resolution of a new coroutine — takes
the value's place among the children). A call of a registered signal
getter in the read (``k.get_count()`` — a getter registered with
``k.register`` on this side) is a read of that getter, and is tracked
the same way (see :class:`~kopis.common.base._RpcCall`). A re-done read
supersedes the previous one, and a pending resolution of a superseded
read is dropped: the reads' resolutions are not ordered among
themselves, and the value of the newest read wins.
"""

from browser import DOMNode, aio, document
from inspect import iscoroutine
from typing import Any

from ..common.component import make_component
from ..common.signal import _effect_scope
from .dom import _fragment_nodes, _native_create_text_node, _scope
from .dom import install as _install_dom

__all__ = ["Component"]

# The DOM extension, before the Component class is built over the
# extended ``DOMNode`` (a no-op if the package's ``__init__`` already
# installed it).
_install_dom()


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
    self.append(placeholder)

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


def _reactive(self: DOMNode, child: object) -> None:
    """A function child in an active effect scope: the value is read
    through the scope (tracked), and is held in the element's children
    (the nodes of the current value, in order), replaced in place
    whenever one of the signals the child read changes (see the module
    docstring).

    A read supersedes the previous one: the resolutions of the reads
    are not ordered among themselves (they are round trips of their
    own), so a pending resolution of a superseded read is dropped —
    the value of the newest read wins."""
    scope = _effect_scope()
    # The nodes of the child's current value, in order (a single empty
    # text node at the start, the placeholder of the value to come).
    nodes: list[DOMNode] = [_native_create_text_node("")]
    self.append(nodes[0])
    # The generation of the read (a read is superseded by the next one):
    # a pending resolution of a superseded read is dropped, so a slow
    # value of an older read cannot overwrite the value of a newer one
    # (the reads' resolutions are not ordered among themselves).
    generation = [0]

    def replace(value: Any) -> None:
        """The new value takes the place of the current one among the
        element's children (the nodes of it are remembered, for the
        next value)."""
        if isinstance(value, str):
            new = _fragment_nodes(value)
        elif hasattr(value, "appendChild"):
            new = [value]
        else:
            new = [_native_create_text_node(str(value))]
        if not new:
            new = [_native_create_text_node("")]
        parent = nodes[0].parentNode
        if parent is None:
            return
        ref = nodes[-1].nextSibling
        for node in nodes:
            parent.removeChild(node)
        for node in new:
            parent.insertBefore(node, ref)
        nodes[:] = new

    def render(value: Any) -> None:
        """Render the value of the read (the read is a new generation:
        a coroutine is started with ``aio.run``, and the value takes
        its place when it resolves, unless a newer read has come).
        """
        generation[0] += 1
        gen = generation[0]
        if iscoroutine(value):

            async def resolve() -> None:
                try:
                    resolved = await value
                except Exception as exc:  # noqa: BLE001 - a failed child keeps the page alive
                    print(f"kopis: a child function failed: {exc}")
                    return
                if gen != generation[0]:
                    # Superseded by a newer read: the newer value wins.
                    return
                replace(resolved)

            aio.run(resolve())
            return
        replace(value)

    def update() -> None:
        """The observer of the change of a signal the child read: the
        read is re-done through the scope (re-tracked, as a solidjs
        effect re-tracks on every re-run), and the new value is
        rendered in place."""
        render(scope.track(child, update))

    render(scope.track(child, update))


#: The client-side ``Component`` class.
Component = make_component(
    DOMNode,
    lambda tag: document.createElement(tag),
    _enter,
    _resolve_async,
    _reactive,
)
