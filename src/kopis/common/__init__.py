"""Pure-Python modules shared by both sides of the web stack.

Every module in this subpackage runs unmodified on both the server
(CPython) and the client (Brython, in the browser): no web server, no
live DOM, no implementation-specific machinery. The server-side and
client-side halves of ``kopis`` import their shared code from here: the
RPC wire format (:mod:`~kopis.common.wire`), the ``Kopis`` base class
(:mod:`~kopis.common.base`), and the ``Magic`` dummy stand-in
(:mod:`~kopis.common.magic`), which the server uses for the brython
``browser`` and ``javascript`` objects it has no live version of.
"""

from .base import KopisBase
from .magic import Magic
from .wire import Placeholder, RpcError, WS_PATH, decode, encode

__all__ = [
    "WS_PATH",
    "KopisBase",
    "Magic",
    "Placeholder",
    "RpcError",
    "decode",
    "encode",
]
