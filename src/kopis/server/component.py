"""The server-side ``Component`` (a stand-in).

The stand-in of the client-side ``Component`` (see
:mod:`kopis.client.component`): the same interface, built by
:func:`kopis.common.component.make_component` over the stand-in
``browser.Node`` class — the instance is a stand-in element and every
operation on it does nothing, because the server has no live DOM, and
the browser builds the real elements by running the same code under
Brython. A function child is called to get its value, and a coroutine
result is discarded (there is nothing to render).
"""

from ..common.component import make_component
from .browser import Node, document

__all__ = ["Component"]

#: The server-side ``Component`` class (a stand-in).
Component = make_component(Node, lambda tag: document.createElement(tag))
