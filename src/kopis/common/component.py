"""The ``Component`` classes (the part shared by both sides).

A *component* is a class that builds a piece of the document. A
component instance is **its own root element**: each side builds its
:class:`~kopis.Component` class with :func:`make_component` over its own
``Node`` class, and the instance is created with
``document.createElement(tag)`` and reclassified into the component
class — so the brython element interface works on a component directly:
``append``, ``+`` (group), ``*`` (clone), attribute subscripts
(``component["id"]``), event handlers (``component.onclick`` or
``component["onclick"]``), iteration over the children, and the ``with
component:`` block form (children created in the block go into the
component). A component is therefore usable everywhere an element is:
``document.body.append(button)``, ``k.window.btn0`` (by id), or as a
child of another component.

The constructor takes the children and the attributes of the root
element, in the standard (W3C/MDN) names of the DOM — ``id``, ``onclick``
(an event handler), ``disabled``, ``placeholder``, ``class_`` (the
``class`` attribute; ``class`` is a Python keyword), ``data_x`` for
``data-x``, and so on (underscores map to hyphens, as in brython's
``html`` builder)::

    class Button(Component):          # a component is a class
        tag = "button"
        classes = ("btn",)

    with k.document.body:             # created in a block: appended there
        Button("Demo", id="btn0", class_="btn-primary", onclick=click)
        Button(get_count, id="btn1")   # a function is a child, too:
                                       # it is called to get the value
                                       # (in an effect scope it is
                                       # tracked, and follows the signal
                                       # — as does a call of a registered
                                       # signal getter in it)

    with Card():                      # a component block: the children of
        CardTitle("Count")           # the block go into the component
        Button("Increment")

The class attributes ``tag`` and ``classes`` fix the root element's tag
and the classes it always has (a component library like
``kopis.daisyui`` builds on them); the classes the caller gives in
``class_`` are merged with them.
"""

from collections.abc import Callable
from inspect import iscoroutine
from typing import Any

from .signal import _effect_scope

__all__ = ["make_component"]


def _attr_name(key: object) -> object:
    """The standard name of an attribute keyword argument: ``class_`` is
    the ``class`` attribute, and any other underscores map to hyphens
    (``data_theme`` is ``data-theme``), as in brython's ``html``
    builder."""
    if key == "class_":
        return "class"
    if isinstance(key, str):
        return key.replace("_", "-")
    return key


def _child_value(value: object) -> object:
    """A child's value, ready to be appended: a string or an element
    passes through as is, and any other value (a number, ...) becomes
    its ``str`` form as text."""
    if isinstance(value, str) or hasattr(value, "appendChild"):
        return value
    return str(value)


def make_component(
    base: type,
    create_element: Callable[[str], Any],
    enter: Callable[[Any], Any] | None = None,
    resolve_async: Callable[[Any, Any], Any] | None = None,
    reactive: Callable[[Any, Any], Any] | None = None,
) -> type:
    """Build a ``Component`` class over the ``Node`` class ``base``.

    ``create_element(tag)`` makes the root element (the side's
    ``document.createElement`` — the client's extension appends it to
    the innermost active ``with element:`` block, as with any other
    element), ``enter`` (the client side) overrides ``__enter__``
    with the ``with component:`` block form of the side,
    ``resolve_async`` (the client side) handles a child function that
    returns a coroutine (the client reserves the value's position with
    a placeholder and fills it when the coroutine resolves; without it,
    the server default, the coroutine is discarded, as the server has
    no live DOM), and ``reactive`` (the client side) handles a child
    function in an active effect scope (``with k.effect():``): the
    client reads the value through the scope (tracked), and updates it
    in place when the signal it reads changes — see
    :mod:`kopis.client.component`.

    The class is built with ``type`` and every method goes into its own
    namespace: under Brython a ``Node`` subclass resolves its dunders
    (``__iter__``, ...) only through the ``Node`` base, and an
    ``__init__`` found below it is never called — so the shared logic
    cannot live in a mixin between the class and its ``Node`` base.
    """

    def __new__(cls: Any, *args: object, **kwargs: object) -> Any:
        """Create the root element and turn it into a component.

        A ``Node`` instance cannot be built from Python (brython
        binds the element to the instance itself), so the instance is
        the element created for it, reclassified into the component
        class — the same way ``document`` gets its attribute access by
        id (see :mod:`kopis.client.dom`).
        """
        element = create_element(cls.tag)
        object.__setattr__(element, "__class__", cls)
        return element

    def __init__(self: Any, *children: Any, **attrs: Any) -> None:
        """Build the root element.

        ``children`` are appended to it, in order: a string is text or
        markup (parsed as a fragment on the client), a ``Node`` or
        another component is an element (one already elsewhere moves
        here, as in the DOM), and a function (or a coroutine function)
        is called, with no arguments, to get the value — a value it
        returns is appended as if it were given as a child (a number,
        for example, becomes its ``str`` form), and a coroutine it
        returns is resolved by ``resolve_async`` (the client reserves
        the value's position with a placeholder and fills it when the
        coroutine resolves; the server discards it, as it has no live
        DOM). A function child in an active effect scope
        (``with k.effect():``) is handled by ``reactive`` instead: the
        side reads the value through the scope (tracked — a signal read
        in the read registers the read as an observer of the signal, as
        does a call of a registered signal getter in it, see
        :class:`~kopis.common.base.RpcCall`), and updates the value in
        place when the signal it read changes (the client does; the
        server has no ``reactive``, and calls the function as usual).
        ``attrs`` are set on the element in the standard DOM
        names: an ``on<event>`` key (``onclick``, ...) is an event
        handler (bound on the client, a no-op on the server), and any
        other key is an attribute (underscores map to hyphens).
        ``class_`` (or ``class``) is the ``class`` attribute, merged
        after the component's own ``classes``.
        """
        given = attrs.pop("class_", None)
        if given is None:
            given = attrs.pop("class", None)
        classes = list(self.classes)
        if given:
            classes += given.split()
        if classes:
            attrs["class"] = " ".join(classes)
        for key, value in attrs.items():
            # The ``__setitem__`` of the ``Node`` base: an
            # ``on<event>`` key binds the event handler, any other key
            # sets the attribute.
            self[_attr_name(key)] = value
        for child in children:
            if callable(child):
                if reactive is not None and _effect_scope() is not None:
                    # A function child in an active effect scope: the
                    # side tracks the read, and updates the value in
                    # place when the signal it reads changes (see the
                    # ``reactive`` parameter of this function).
                    reactive(self, child)
                else:
                    value = child()
                    if iscoroutine(value):
                        # The value arrives later: the side resolves
                        # the coroutine (the client fills the element
                        # when it resolves; the server discards it, as
                        # it has no live DOM).
                        if resolve_async is not None:
                            resolve_async(self, value)
                        else:
                            value.close()
                    else:
                        self.append(_child_value(value))
            else:
                self.append(_child_value(child))

    def el(self: Any) -> Any:
        """The component's root element: the component itself (a
        component is its own element)."""
        return self

    namespace: dict[str, Any] = {
        "__doc__": (
            "A component of the document: a class whose instances are "
            "their own root elements (see kopis.common.component)."
        ),
        "tag": "div",
        "classes": (),
        "__new__": __new__,
        "__init__": __init__,
        "el": property(el),
    }
    if enter is not None:
        namespace["__enter__"] = enter
    return type("Component", (base,), namespace)
