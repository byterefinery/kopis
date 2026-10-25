"""RPC wire format, shared by the server and client halves of ``kopis``.

Calls and results travel both ways over a single WebSocket per client.
Messages are JSON, so they stay readable in the browser's network
inspector: a message is either a ``call`` (function name, ``args``,
``kwargs``), an ``op`` (an operation on an ``RPCHandle``: its
``handle``, ``op``, ``name``, ``args``, ``kwargs``), or a ``result``; a
function name is a string, ``args`` is a list, and ``kwargs`` is an
object with string keys. The *values* of ``args``, ``kwargs``, and any
``result``, and any ``handle``, are pickled Python objects,
base64-encoded so they fit inside the JSON.

A value that cannot be pickled on the sender side, or cannot be
unpickled on the receiver side (for example because its type does not
exist there), stays alive on the side where it is: ``encode`` takes a
``maker`` that turns such a value into its :class:`RPCHandle` (which is
pickled instead), and ``decode`` takes a ``binder`` (the receiving
``Kopis``) that binds every ``RPCHandle`` in the message to it, so
operations on the handles go through that side (see
:mod:`~kopis.common.handle`).
"""

import base64
import json
import pickle
from collections.abc import Callable
from typing import Any

from .handle import RPCHandle

__all__ = ["WS_PATH", "RpcError", "decode", "encode"]

#: The URL of the WebSocket endpoint that carries RPC messages.
WS_PATH = "/__kopis__/rpc"


class RpcError(Exception):
    """Raised when a remote function call failed on the other side."""

    def __init__(self, type: str, message: str) -> None:
        super().__init__(f"{type}: {message}")
        self.type = type
        self.message = message


def _pack(value: Any, maker: Callable[[Any, str], Any]) -> str:
    """Serialize ``value`` to a base64 string of its pickle.

    If ``value`` cannot be pickled, ``maker(value, reason)`` is called
    and the value it returns (an ``RPCHandle`` pointing at ``value``,
    which stays alive on this side) is pickled instead.
    """
    try:
        data = pickle.dumps(value)
    except Exception as exc:  # noqa: BLE001 - any failure becomes a handle
        data = pickle.dumps(maker(value, str(exc)))
    return base64.b64encode(data).decode("ascii")


def _unpack(text: str) -> Any:
    """Deserialize a base64 pickled value.

    Raises if the value cannot be unpickled (for example because its
    type does not exist on this side); the receiver reports the error
    as the result of the message that carried the value.
    """
    return pickle.loads(base64.b64decode(text.encode("ascii")))


def _bind(value: Any, binder: Any) -> None:
    """Bind every ``RPCHandle`` in ``value`` to ``binder`` (recursively)."""
    if isinstance(value, RPCHandle):
        value._kopis = binder
    elif isinstance(value, dict):
        for key, item in value.items():
            _bind(key, binder)
            _bind(item, binder)
    elif isinstance(value, (list, tuple, set, frozenset)):
        for item in value:
            _bind(item, binder)


def encode(message: dict, maker: Callable[[Any, str], Any]) -> str:
    """Serialize an RPC message to a JSON string.

    Message type, call id, function name, op, and error details stay
    plain JSON; the values of ``args`` and ``kwargs``, any ``result``,
    and any ``handle`` are pickled. A value that cannot be pickled is
    turned into its ``RPCHandle`` by ``maker(value, reason)`` — the
    value itself stays alive on this side.
    """
    packed = dict(message)
    if "handle" in packed:
        packed["handle"] = _pack(packed["handle"], maker)
    if "args" in packed:
        packed["args"] = [_pack(value, maker) for value in packed["args"]]
    if "kwargs" in packed:
        packed["kwargs"] = {
            key: _pack(value, maker) for key, value in packed["kwargs"].items()
        }
    if "result" in packed:
        packed["result"] = _pack(packed["result"], maker)
    return json.dumps(packed)


def decode(text: str, binder: Any = None) -> Any:
    """Parse an RPC message from a JSON string, restoring pickled values.

    Raises if any pickled value cannot be unpickled. If ``binder`` (the
    receiving ``Kopis``) is given, every ``RPCHandle`` in the message is
    bound to it, so operations on the handles go through that side.
    """
    message = json.loads(text)
    if isinstance(message, dict):
        if "handle" in message:
            message["handle"] = _unpack(message["handle"])
        if "args" in message:
            message["args"] = [_unpack(value) for value in message["args"]]
        if "kwargs" in message:
            message["kwargs"] = {
                key: _unpack(value) for key, value in message["kwargs"].items()
            }
        if "result" in message:
            message["result"] = _unpack(message["result"])
    if binder is not None:
        _bind(message, binder)
    return message
