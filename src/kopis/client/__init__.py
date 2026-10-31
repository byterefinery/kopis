"""Kopis: pure-Python web development (client side).

This is the client-side half of the ``kopis`` package: it runs in the
browser under Brython. It shares its API with the server-side half
(the ``kopis.server`` subpackage); only the implementation differs: no
web server, no root directory. ``k.run()`` and ``k.add_static_file()``
are no-ops here; ``k.document`` is the browser document (the live DOM);
and ``k.register``/``k.rpc`` implement the RPC client half.

The brython objects the unified code works with — ``document``,
``window``, ``bind``, ``Node``, ``Event``, ``html``, ``aio``,
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
    DOMEvent as Event,
    DOMNode as Node,
    document,
    html,
    timer,
    window,
)
import javascript

from .app import Kopis
from .component import Component
from .dom import install as _install_dom
from .for_ import For
from ..common import (
    Client,
    CONTAINER_TAGS,
    Effect,
    Handle,
    RpcError,
    SharedSignal,
    Signal,
    TAGS,
    VOID_TAGS,
)

__all__ = [
    "CONTAINER_TAGS",
    "TAGS",
    "VOID_TAGS",
    "Client",
    "Component",
    "Effect",
    "Event",
    "For",
    "Handle",
    "Kopis",
    "Node",
    "RpcError",
    "SharedSignal",
    "Signal",
    "aio",
    "ajax",
    "bind",
    "document",
    "html",
    "javascript",
    "timer",
    "window",
]

# Extend the DOM (client side): a string passed to append is parsed as
# an HTML fragment first, and a coroutine function bound to an event is
# started with aio.run when the event fires. (The component module
# installs it as well, so that the Component class is built over the
# extended Node; the call here is a no-op then.)
_install_dom()
