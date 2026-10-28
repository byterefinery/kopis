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
            Button("Increment", id="inc", class_="btn-primary",
                   onclick=increment)
"""

from typing import Any

from kopis import Component as _Component

# ``kopis.Component`` is the client-side or the server-side class, resolved
# by the ``kopis`` package at import time (a component instance is its own
# root element on either side). The union of the two is not a valid class
# base, so the name is widened for the subclasses below.
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

    ``variant`` (``primary``, ``secondary``, ``accent``, ``success``,
    ``warning``, ``error``, ``ghost``, ``link``, ``outline``) adds
    ``btn-<variant>``, ``size`` (``xs``, ``sm``, ``md``, ``lg``, ``xl``)
    adds ``btn-<size>``, and ``shape`` (``circle``, ``box``, ``wide``,
    ``soft``) adds ``btn-<shape>``. The standard attributes of the ``<button>``
    element pass through (``id``, ``onclick``, ``disabled``, ``type``,
    ``value``, ...).
    """

    tag = "button"
    classes = ("btn",)

    def __init__(
        self,
        *children: object,
        variant: object = None,
        size: object = None,
        shape: object = None,
        **attrs: object,
    ) -> None:
        mods = [f"btn-{v}" for v in (variant, size, shape) if v is not None]
        if mods:
            given = attrs.pop("class_", None)
            if given is None:
                given = attrs.pop("class", None)
            attrs["class_"] = Component.join_classes(mods, given)
        Component.__init__(self, *children, **attrs)


class Badge(Component):
    """A daisyUI badge: ``<span class="badge">``.

    ``variant`` (``primary``, ``secondary``, ``accent``, ``success``,
    ``warning``, ``error``, ``ghost``, ``outline``) adds
    ``badge-<variant>``, and ``size`` (``xs``, ``sm``, ``lg``) adds
    ``badge-<size>``.
    """

    tag = "span"
    classes = ("badge",)

    def __init__(
        self,
        *children: object,
        variant: object = None,
        size: object = None,
        **attrs: object,
    ) -> None:
        mods = [f"badge-{v}" for v in (variant, size) if v is not None]
        if mods:
            given = attrs.pop("class_", None)
            if given is None:
                given = attrs.pop("class", None)
            attrs["class_"] = Component.join_classes(mods, given)
        Component.__init__(self, *children, **attrs)


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
