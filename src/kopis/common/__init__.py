"""Pure-Python modules shared by both sides of the web stack.

Every module in this subpackage runs unmodified on both the server
(CPython) and the client (Brython, in the browser): no web server, no
DOM, no implementation-specific machinery. The server-side and
client-side halves of ``kopis`` import their shared code from here:
the RPC wire format (:mod:`~kopis.common.wire`) and the ``Kopis`` base
class (:mod:`~kopis.common.base`).
"""

from .base import KopisBase
from .wire import Placeholder, RpcError, WS_PATH, decode, encode

__all__ = ["WS_PATH", "KopisBase", "Placeholder", "RpcError", "decode", "encode"]
