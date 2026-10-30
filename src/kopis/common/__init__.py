"""Pure-Python modules shared by both sides of the web stack.

Every module in this subpackage runs unmodified on both the server
(CPython) and the client (Brython, in the browser): no web server, no
live DOM, no implementation-specific machinery. The server-side and
client-side halves of ``kopis`` import their shared code from here: the
RPC wire format (:mod:`~kopis.common.wire`), the ``Kopis`` base class
(:mod:`~kopis.common.base`), the ``RPCHandle`` type
(:mod:`~kopis.common.handle`), which stands in for a value that cannot
be serialized — the live object stays on the side where it is, and the
other side operates on it through the handle — the ``Signal`` class
(:mod:`~kopis.common.signal`), a single value with a getter and a
setter, in the spirit of solidjs signals, the ``SharedSignal`` class
(a :class:`~kopis.common.signal.SharedSignal` — a signal whose value is
shared between the server and the clients), the ``Effect`` class
(:mod:`~kopis.common.effect`), a reactive scope of the signals, in the
spirit of solidjs's ``createEffect``, and the ``_Item`` class
(:mod:`~kopis.common.for_`), the ``as`` variable of a ``For`` loop (the
loop itself is a side class — :mod:`~kopis.client.for_` and
:mod:`~kopis.server.for_`), with the client-side dependencies for
``k.use`` (:mod:`~kopis.common.uses`), the standard HTML5 tag names
grouped into the void elements (no children) and the container
elements (with children) (:mod:`~kopis.common.tags`), and the
``Magic`` dummy stand-in (:mod:`~kopis.common.magic`), which the
server uses for the brython ``browser`` and ``javascript`` objects it
has no live version of.
"""

from .base import Client, KopisBase
from .effect import Effect
from .handle import RPCHandle
from .magic import Magic
from .signal import SharedSignal, Signal
from .tags import CONTAINER_TAGS, TAGS, VOID_TAGS
from .uses import USES
from .wire import RpcError, WS_PATH, decode, encode

__all__ = [
    "CONTAINER_TAGS",
    "TAGS",
    "USES",
    "VOID_TAGS",
    "WS_PATH",
    "Client",
    "Effect",
    "KopisBase",
    "Magic",
    "RPCHandle",
    "RpcError",
    "SharedSignal",
    "Signal",
    "decode",
    "encode",
]
