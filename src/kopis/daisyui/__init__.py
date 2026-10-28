"""daisyUI components for kopis (both sides).

Each component is a subclass of :class:`~kopis.Component`: the class
attributes ``tag`` and ``classes`` fix its root element and its
daisyUI classes, and the constructor takes the children and the
attributes of the element in the standard DOM names (the W3C/MDN
names): ``id``, ``onclick`` (an event handler), ``disabled``,
``placeholder``, ``value``, ``class_`` (extra classes; ``class`` is a
Python keyword), ``data_x`` for ``data-x``, and so on. A component
instance is its own root element (a ``DOMNode``), so it is used
everywhere an element is::

    from kopis import Kopis
    from kopis.daisyui import Button, Card, CardBody, CardTitle

    k = Kopis()
    k.use("tailwindcss")
    k.use("daisyui")

    with k.document.body:
        with Card():
            CardTitle("Count")
            Button("Increment", id="inc", class_="btn-primary btn-sm",
                   onclick=increment)

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
    "Badge",
    "Button",
    "Card",
    "CardActions",
    "CardBody",
    "CardTitle",
    "Input",
    "Label",
]


class Button(Component):
    """A daisyUI button: ``<button class="btn">``.

    The daisyUI modifiers are the full class names, given in ``class_``
    (``btn-primary``, ``btn-sm``, ``btn-circle``, ...). The standard
    attributes of the ``<button>`` element pass through (``id``,
    ``onclick``, ``disabled``, ``type``, ``value``, ...).
    """

    tag = "button"
    classes = ("btn",)


class Badge(Component):
    """A daisyUI badge: ``<span class="badge">``.

    The daisyUI modifiers are the full class names, given in ``class_``
    (``badge-primary``, ``badge-lg``, ...).
    """

    tag = "span"
    classes = ("badge",)


class Card(Component):
    """A daisyUI card: ``<div class="card">``."""

    tag = "div"
    classes = ("card",)


class CardTitle(Component):
    """A daisyUI card title: ``<h2 class="card-title">``."""

    tag = "h2"
    classes = ("card-title",)


class CardBody(Component):
    """A daisyUI card body: ``<div class="card-body">``."""

    tag = "div"
    classes = ("card-body",)


class CardActions(Component):
    """A daisyUI card actions: ``<div class="card-actions">``."""

    tag = "div"
    classes = ("card-actions",)


class Input(Component):
    """A daisyUI input: ``<input class="input input-bordered">``.

    The standard attributes of the ``<input>`` element pass through
    (``type``, ``placeholder``, ``value``, ``disabled``, ``onclick``,
    ...). It is a void element: it takes no children.
    """

    tag = "input"
    classes = ("input", "input-bordered")


class Label(Component):
    """A daisyUI label: ``<label class="label">``.

    The ``for`` attribute (a Python keyword) is passed through a dict:
    ``Label("Name", **{"for": "in1"})``.
    """

    tag = "label"
    classes = ("label",)
