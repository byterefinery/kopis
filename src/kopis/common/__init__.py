"""Pure-Python modules shared by both sides of the web stack.

Every module in this subpackage runs unmodified on both the server
(CPython) and the client (Brython, in the browser): no web server, no
live DOM, no implementation-specific machinery. The server-side and
client-side halves of ``kopis`` import their shared code from here: the
RPC wire format (:mod:`~kopis.common.wire`), the ``Kopis`` base class
(:mod:`~kopis.common.base`), the ``RPCHandle`` type
(:mod:`~kopis.common.handle`), which stands in for a value that cannot
be serialized — the live object stays on the side where it is, and the
other side operates on it through the handle — and the ``Magic`` dummy
stand-in (:mod:`~kopis.common.magic`), which the server uses for the
brython ``browser`` and ``javascript`` objects it has no live version
of.
"""

from .base import KopisBase
from .handle import RPCHandle
from .magic import Magic
from .wire import RpcError, WS_PATH, decode, encode

__all__ = [
    "WS_PATH",
    "KopisBase",
    "Magic",
    "RPCHandle",
    "RpcError",
    "decode",
    "encode",
]
