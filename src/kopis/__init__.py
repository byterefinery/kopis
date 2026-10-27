"""Kopis: pure-Python web development.

The ``kopis`` package is imported on both sides of the web stack, and
this ``__init__`` differentiates the two sides at import time based on
the running Python implementation:

- **Server** (CPython): the :mod:`kopis.server` subpackage — a web
  application with a root directory, an HTML document served at ``/``,
  and RPC to and from clients.
- **Client** (Brython, in the browser): the :mod:`kopis.client`
  subpackage — the RPC client and the browser objects the client code
  works with (``document``, ``window``, ``bind``, ``html``, ``aio``,
  ...). It has no web server.

``import kopis`` therefore resolves to the server side in CPython code
and to the client side in browser code. Both sides expose the same
unified API — ``Kopis`` (with ``register``, ``rpc``, ``document``,
``html``, ``add_static_file``, ``parse_html``, and ``run``), the
``Signal`` class, and the brython objects ``document``,
``DOMNode``, ``DOMEvent``, ``bind``, ``html``, ``aio``, ``ajax``,
``timer``, ``window``, and ``javascript`` — so a single application file
can run unmodified on both sides; only the implementations differ
(e.g. ``k.run()`` starts the web server on the server and is a no-op on
the client). In the browser, ``document`` is the live DOM; on the
server it is a stand-in of the brython ``browser.document`` object,
because the server has no live DOM and never parses the HTML it serves
— the browser does that for it, in the brython way. Values exchanged
between the sides are pickled by the shared ``kopis.common`` package; a
value that cannot be serialized does not travel — sending it raises,
and the developer wraps it in an explicit ``RPCHandle``
(``k.get_handle``) through which the other side operates on the live
object.

Developers import the brython objects from ``kopis``, never from
``browser`` or ``javascript`` directly: the names above are the unified
interface, resolved to the brython built-ins in the browser and to the
server stand-ins under CPython.

The side of the web stack the code is running on is indicated by the
module constants :data:`IS_SERVER` and :data:`IS_CLIENT` (and, on the
application itself, by :meth:`Kopis.is_server` and
:meth:`Kopis.is_client`), which let app code take a side-specific
branch at import time, before the ``Kopis`` instance exists::

    if IS_SERVER:
        import os
    elif IS_CLIENT:
        import sys
"""

import platform

#: ``True`` when this ``kopis`` is running on the server side (CPython)
#: and a web server is available; ``False`` in the browser (Brython).
IS_SERVER: bool = platform.python_implementation() != "Brython"

#: ``True`` when this ``kopis`` is running on the client side (Brython,
#: in the browser); ``False`` under CPython.
IS_CLIENT: bool = not IS_SERVER

__all__ = [
    "IS_CLIENT",
    "IS_SERVER",
    "DOMEvent",
    "DOMNode",
    "Kopis",
    "RPCHandle",
    "RpcError",
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

if IS_CLIENT:
    # Client side: running in the browser under Brython. The brython
    # built-ins are re-exported under the unified names.
    from .client import (
        Kopis,
        RPCHandle,
        RpcError,
        aio,
        ajax,
        bind,
        DOMEvent,
        DOMNode,
        document,
        html,
        javascript,
        Signal,
        timer,
        window,
    )
else:
    # Server side: running on CPython. The stand-ins of the brython
    # objects are re-exported under the same unified names.
    from .server import (
        Kopis,
        RPCHandle,
        RpcError,
        aio,
        ajax,
        bind,
        DOMEvent,
        DOMNode,
        document,
        html,
        javascript,
        Signal,
        timer,
        window,
    )
