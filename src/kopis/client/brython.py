"""The browser modules that client code works with, under any Python.

``browser`` and ``javascript`` are built-in modules of the Brython
implementation. Under CPython they do not exist, so stand-ins keep this
subpackage importable for tooling and type-checking.
"""

import platform

if platform.python_implementation() == "Brython":
    from browser import aio, window, websocket
    from browser import document as browser_document
    import javascript
else:
    from unittest.mock import MagicMock

    aio = MagicMock()
    browser_document = MagicMock()
    javascript = MagicMock()
    window = MagicMock()
    websocket = MagicMock()

__all__ = ["aio", "browser_document", "javascript", "websocket", "window"]
