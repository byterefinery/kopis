"""Pure-Python modules shared by both sides of the web stack.

Every module in this subpackage runs unmodified on both the server
(CPython) and the client (Brython, in the browser): no web server, no
DOM, no implementation-specific machinery. The server-side and
client-side halves of ``kopis`` import their shared code from here: the
RPC wire format (:mod:`~kopis.common.wire`), the ``Kopis`` base class
(:mod:`~kopis.common.base`), and the minimal DOM library
(:mod:`~kopis.common.dom`), whose :class:`~kopis.common.dom.Document`
and :class:`~kopis.common.dom.Element` classes mirror the brython
``browser`` objects and are used by the server to parse and prettify
the document it serves.
"""

from . import dom
from .base import KopisBase
from .wire import Placeholder, RpcError, WS_PATH, decode, encode

__all__ = [
    "WS_PATH",
    "KopisBase",
    "Placeholder",
    "RpcError",
    "decode",
    "dom",
    "encode",
]
