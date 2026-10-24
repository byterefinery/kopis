"""Pure-Python modules shared by both sides of the web stack.

Every module in this subpackage runs unmodified on both the server
(CPython) and the client (Brython, in the browser): no web server, no
live DOM, no implementation-specific machinery. The server-side and
client-side halves of ``kopis`` import their shared code from here: the
RPC wire format (:mod:`~kopis.common.wire`), the ``Kopis`` base class
(:mod:`~kopis.common.base`), the ``Magic`` dummy stand-in
(:mod:`~kopis.common.magic`), and the minimal DOM library
(:mod:`~kopis.common.dom`), whose :class:`~kopis.common.dom.Document`
and :class:`~kopis.common.dom.Element` classes mirror the brython
``browser`` objects. Both sides hand out their tree as ``k.document``
(the server the parsed document, the client the live browser document);
the server's tree is also exposed as ``browser.document`` of the
stand-in ``browser`` package.
"""

from . import dom
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
    "dom",
    "encode",
]
