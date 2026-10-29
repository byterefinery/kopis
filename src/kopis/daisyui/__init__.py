"""daisyUI components for kopis (both sides).

Each component is a subclass of :class:`~kopis.Component`: the class
attributes ``tag`` and ``classes`` fix its root element and its
daisyUI classes, and the constructor takes the children and the
attributes of the element in the standard DOM names (the W3C/MDN
names): ``id``, ``onclick`` (an event handler), ``disabled``,
``placeholder``, ``value``, ``class_`` (extra classes; ``class`` is a
Python keyword), ``data_x`` for ``data-x``, and so on. A component
instance is its own root element (a ``DOMNode``).

The components use the real daisyUI class names: each fixes only the
classes of its root element (``btn``, ``badge``, ``card``, ...), and
every modifier (size, color, shape, ...) is given by the caller as the
full daisyUI class in ``class_``.
"""

from typing import Any

from kopis import Component as _Component

# ``kopis.Component`` is the client-side or the server-side class, resolved
# by the ``kopis`` package at import time. The union of the two is not a
# valid class base, so the name is widened for the subclasses below.
Component: Any = _Component


__all__ = [
    "Button",
]


class Button(Component):
    """A daisyUI button: ``<button class="btn">``."""

    tag = "button"
    classes = ("btn",)
