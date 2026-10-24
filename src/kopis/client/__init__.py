"""Kopis: pure-Python web development (client side).

This is the client-side half of the ``kopis`` package: it runs in the
browser under Brython. It shares its API with the server-side half
(the ``kopis.server`` subpackage); only the implementation differs: no
web server, no root directory. ``k.run()`` and ``k.add_static_file()``
are no-ops here; ``k.document`` is the browser document (the live DOM);
and ``k.register``/``k.rpc`` implement the RPC client half.

Calls and results travel both ways over a single WebSocket connection
per browser tab (``/__kopis__/rpc``), re-opened automatically on
disconnect. The browser's implicit event loop drives everything;
``aio.run`` starts a coroutine without blocking.
"""

from .app import Kopis
from .brython import aio, bind, browser_document as document, javascript
from ..common import Placeholder, RpcError

__all__ = [
    "Kopis",
    "Placeholder",
    "RpcError",
    "aio",
    "bind",
    "document",
    "javascript",
]
