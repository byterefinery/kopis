"""Kopis: pure-Python web development.

The ``kopis`` package is imported on both sides of the web stack, and this
``__init__`` differentiates the two sides at import time based on the
running Python implementation:

- **Server** (CPython): the :mod:`kopis.server` subpackage — a web
  application with a root directory, an HTML document served at ``/``,
  and RPC to and from clients.
- **Client** (Brython, in the browser): the :mod:`kopis.client`
  subpackage — the RPC client and the browser objects client code works
  with (``document``, ``aio``, ``javascript``). It has no web server.

``import kopis`` therefore resolves to the server side in CPython code
and to the client side in browser code. With ``Kopis(use="brython")``
the server serves this whole package to the browser, so the same
differentiation runs there.

Both sides expose the same unified API — ``Kopis`` (with ``bind``,
``rpc``, ``document``, ``add_static_file``, and ``run``), ``aio``,
``RpcError``, and ``Placeholder`` — so a single application file can run
unmodified on both sides; only the implementations differ (e.g.
``k.run()`` starts the web server on the server and is a no-op on the
client). Values exchanged between the sides are pickled by the shared
``kopis.common`` package; a value that cannot be (de)serialized arrives
as a ``Placeholder`` carrying the string of the exception.
"""

import platform

if platform.python_implementation() == "Brython":
    # Client side: running in the browser under Brython.
    from .client import Kopis, Placeholder, RpcError, aio, document, javascript

    __all__ = ["Kopis", "Placeholder", "RpcError", "aio", "document", "javascript"]
else:
    # Server side: running on CPython.
    from .server import Document, Element, Kopis, Placeholder, RpcError, aio

    __all__ = ["Document", "Element", "Kopis", "Placeholder", "RpcError", "aio"]
