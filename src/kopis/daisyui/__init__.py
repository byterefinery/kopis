"""daisyUI components for kopis (both sides).

A daisyUI component is a class built over the side's ``Component``
base (the class the ``kopis`` package resolves at import time: the
client-side class under Brython, the server-side stand-in on
CPython — see :mod:`kopis.common.component`): the class attributes
fix the element role the component represents, and the constructor
takes the children of the element and its attributes in the standard
DOM names (``id``, ``onclick`` (an event handler), ``disabled``,
``placeholder``, ``class_`` (extra classes; ``class`` is a Python
keyword), ``data_x`` for ``data-x``, and so on). A component
instance is its own root element.

Principles
==========

*One class per element role.* Every daisyUI class that names an
element role is a component class of its own: the root role of the
component (``btn``, ``list``, ``table``, ...) and each of its parts
(``list-row``, ...). The class attributes ``tag`` and ``classes``
fix the tag of the element and the daisyUI classes it always has.

*Types and flags are keyword arguments.* The daisyUI types and flags
of the role (``color``, ``size``, ``style``, ``zebra``, ...) are
keyword arguments mapped by the class attribute ``types`` to the
class name each adds — after ``classes``, before the caller's
``class_``: a template with ``{v}`` takes a string value (``color=
"primary"`` adds ``btn-primary``), a fixed name is a boolean flag
(``zebra=True`` adds ``table-zebra``). One class per type; the flags
combine.

*Native tags are ``k.html``.* Everything that is not a daisyUI role
is built with the ``browser.html`` builder of the app (``k.html.div``,
``k.html.tr``, ... — every W3C tag): the real builder on the client,
a stand-in on the server. A daisyUI class that goes on a native
element (``row-hover`` on a ``tr``, ``list-col-grow`` on a cell) is
given in its ``class_``.

*Children are never constrained.* A component takes any children:
elements and components, strings (text or markup), and functions
(called for the value; in an effect scope, tracked and updated with
the signal it reads).

*Building style.* Pass the children directly to the constructor (a
component appends them all), or create them in a ``with ...:`` block
of the parent: entering a block over an element appends it to the
innermost active block, and every element created in a block joins
the block's element as it is created (a node given to a deeper
element as a child moves there). A ``k.html.<tag>(...)`` call, in
contrast, appends at most one child — several positional arguments
are not appended (the brython ``html`` factory takes at most one),
so a native element with several children is built in a block. The
DOM operators (``<=`` and friends) still work, but the constructor
and the block are the readable ways.

Each component lives in its own module named after it, and this
package re-exports them all: :class:`Button` is
:mod:`kopis.daisyui.button`, :class:`List` and friends are
:mod:`kopis.daisyui.list`, :class:`Table` is
:mod:`kopis.daisyui.table`.

To use the components, attach the styles (``k.use("tailwindcss")``
and ``k.use("daisyui")``) and set the theme (``data-theme`` on the
document element).
"""

from ._component import Component
from .button import Button
from .list import List, ListCell, ListRow
from .table import Table

__all__ = [
    "Button",
    "Component",
    "List",
    "ListCell",
    "ListRow",
    "Table",
]
