"""The browser modules that client code works with, under any Python.

``browser`` and ``javascript`` are built-in modules of the Brython
implementation. Under CPython they do not exist, so stand-ins keep this
subpackage importable for tooling and type-checking.
"""

import platform

if platform.python_implementation() == "Brython":
    from browser import DOMNode, aio, bind, window, websocket
    from browser import document as browser_document
    import javascript
else:
    from unittest.mock import MagicMock

    DOMNode = MagicMock()
    aio = MagicMock()
    bind = MagicMock()
    browser_document = MagicMock()
    javascript = MagicMock()
    websocket = MagicMock()
    window = MagicMock()

__all__ = [
    "DOMNode",
    "aio",
    "bind",
    "browser_document",
    "javascript",
    "websocket",
    "window",
]
