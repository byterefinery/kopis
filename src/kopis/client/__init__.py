"""Kopis: pure-Python web development (client side).

This is the client-side half of the ``kopis`` package: it runs in the
browser under Brython. It shares its API with the server-side half
(the ``kopis.server`` subpackage); only the implementation differs: no
web server, no root directory. ``k.run()`` and ``k.add_static_file()``
are no-ops here; ``k.document`` is the browser document (the live DOM);
and ``k.register``/``k.rpc`` implement the RPC client half.

The brython objects the unified code works with — ``document``,
``window``, ``bind``, ``DOMNode``, ``DOMEvent``, ``html``, ``aio``,
``ajax``, ``timer``, and ``javascript`` — are the built-in ``browser``
and ``javascript`` modules, re-exported under the ``kopis`` names: app
code imports them from ``kopis``, never from ``browser`` directly.

Calls and results travel both ways over a single WebSocket connection
per browser tab (``/__kopis__/rpc``), re-opened automatically on
disconnect. The browser's implicit event loop drives everything;
``aio.run`` starts a coroutine without blocking.
"""

from browser import (
    aio,
    ajax,
    bind,
    DOMEvent,
    DOMNode,
    document,
    html,
    timer,
    window,
)
import javascript

from .app import Kopis
from .dom import install as _install_dom
from ..common import Placeholder, RpcError

__all__ = [
    "DOMEvent",
    "DOMNode",
    "Kopis",
    "Placeholder",
    "RpcError",
    "aio",
    "ajax",
    "bind",
    "document",
    "html",
    "javascript",
    "timer",
    "window",
]

# Extend the DOM (client side): a string appended with <= or attach is
# parsed as an HTML fragment first, and a coroutine function bound to an
# event is started with aio.run when the event fires.
_install_dom()
