"""The browser modules that client code works with, under any Python.

In the browser under Brython these are the built-in ``browser`` and
``javascript`` modules. Under CPython they are the stand-in packages
shipped with kopis (``kopis.browser`` and ``kopis.javascript``), which
:mod:`kopis` aliases to the same top-level names — so this module runs
unmodified on both sides.
"""

from browser import DOMNode, aio, bind, window, websocket
from browser import document as browser_document
import javascript

__all__ = [
    "DOMNode",
    "aio",
    "bind",
    "browser_document",
    "javascript",
    "websocket",
    "window",
]
