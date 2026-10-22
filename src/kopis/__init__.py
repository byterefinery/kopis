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
"""

import platform

if platform.python_implementation() == "Brython":
    # Client side: running in the browser under Brython.
    from .client import Kopis, aio, document, javascript

    __all__ = ["Kopis", "aio", "document", "javascript"]
else:
    # Server side: running on CPython.
    from .server import Document, Element, Kopis

    __all__ = ["Document", "Element", "Kopis"]
