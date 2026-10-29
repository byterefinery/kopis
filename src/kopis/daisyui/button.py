"""The daisyUI ``Button`` component (both sides)."""

from typing import ClassVar

from .daisyui_component import DaisyUIComponent

__all__ = ["Button"]


class Button(DaisyUIComponent):
    """A daisyUI button: ``<button class="btn">``.

    The daisyUI types are keyword arguments (one class name per
    type)::

        color     btn-neutral btn-primary btn-secondary btn-accent
                  btn-info btn-success btn-warning btn-error
        style     btn-outline btn-dash btn-soft btn-ghost btn-link
        behavior  btn-active btn-disabled
        size      btn-xs btn-sm btn-md btn-lg btn-xl
        modifier  btn-wide btn-block btn-square btn-circle

    The ``btn`` class also works on a ``k.html.a`` or a
    ``k.html.input`` (``class_="btn"``); the native ``disabled``
    attribute gives the disabled look of ``behavior="disabled"``.
    """

    tag = "button"
    classes = ("btn",)
    types: ClassVar[dict[str, str]] = {
        name: "btn-{v}" for name in ("color", "style", "behavior", "size", "modifier")
    }
