"""The base of the daisyUI components (both sides).

A daisyUI component is a subclass of the side's ``Component`` base
(the class the ``kopis`` package resolves at import time: the
client-side class under Brython, the server-side stand-in on
CPython). Its class attributes fix the element role it represents:

- ``tag`` — the tag of the root element (``"button"``, ``"li"``, ...);
- ``classes`` — the daisyUI classes the element always has
  (``("btn",)``, ``("list-row",)``);
- ``types`` — the daisyUI types and flags of the role, as keyword
  arguments mapped to the class name each adds (a template with
  ``{v}`` takes a string value — ``color="primary"`` adds
  ``btn-primary`` — a fixed name is a boolean flag — ``zebra=True``
  adds ``table-zebra``).

The added classes go into the root element's ``class`` after
``classes`` and before the classes the caller gives in ``class_``
(see :mod:`kopis.daisyui` for the principles and the component
modules).
"""

from typing import Any, ClassVar

from kopis import Component as _Base

__all__ = ["Component"]

# ``kopis.Component`` is the client-side or the server-side class,
# resolved by the ``kopis`` package at import time. The union of the
# two is not a valid class base, so the name is widened for the
# subclasses below.
Base: Any = _Base


class Component(Base):
    """A daisyUI component: the side's ``Component`` base with the
    daisyUI types and flags of the role as keyword arguments (see the
    module docstring)."""

    #: The daisyUI types and flags of the role: a keyword argument name
    #: mapped to the class name it adds — a template with ``{v}`` for
    #: a string value, a fixed name for a boolean flag.
    types: ClassVar[dict[str, str]] = {}

    def __init__(self, *children: Any, **attrs: Any) -> None:
        """Build the root element: the children and the attributes as
        in the ``Component`` base, plus the daisyUI types and flags
        (the ``types`` keyword arguments are mapped to their class
        names and added to the ``class`` attribute)."""
        extra = [
            template.format(v=value)
            for name, template in self.types.items()
            if (value := attrs.pop(name, None))
        ]
        if extra:
            class_ = attrs.pop("class_", None) or attrs.pop("class", None)
            if class_:
                extra += class_.split()
            attrs["class_"] = " ".join(extra)
        super().__init__(*children, **attrs)
