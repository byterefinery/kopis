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
``add_static_file``, and ``run``), and the brython objects ``document``,
``DOMNode``, ``DOMEvent``, ``bind``, ``html``, ``aio``, ``ajax``,
``timer``, ``window``, and ``javascript`` — so a single application file
can run unmodified on both sides; only the implementations differ
(e.g. ``k.run()`` starts the web server on the server and is a no-op on
the client). In the browser, ``document`` is the live DOM; on the
server it is a stand-in of the brython ``browser.document`` object,
because the server has no live DOM and never parses the HTML it serves
— the browser does that for it, in the brython way. Values exchanged
between the sides are pickled by the shared ``kopis.common`` package; a
value that cannot be (de)serialized arrives as a ``Placeholder``
carrying the string of the exception.

Developers import the brython objects from ``kopis``, never from
``browser`` or ``javascript`` directly: the names above are the unified
interface, resolved to the brython built-ins in the browser and to the
server stand-ins under CPython.
"""

import platform

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

if platform.python_implementation() == "Brython":
    # Client side: running in the browser under Brython. The brython
    # built-ins are re-exported under the unified names.
    from .client import (
        Kopis,
        Placeholder,
        RpcError,
        aio,
        ajax,
        bind,
        DOMEvent,
        DOMNode,
        document,
        html,
        javascript,
        timer,
        window,
    )
else:
    # Server side: running on CPython. The stand-ins of the brython
    # objects are re-exported under the same unified names.
    from .server import (
        Kopis,
        Placeholder,
        RpcError,
        aio,
        ajax,
        bind,
        DOMEvent,
        DOMNode,
        document,
        html,
        javascript,
        timer,
        window,
    )
