"""RPC wire format, shared by the server and client halves of ``kopis``.

Calls and results travel both ways over a single WebSocket per client.
Messages are JSON, so they stay readable in the browser's network
inspector: a message is either a ``call`` (function name, ``args``,
``kwargs``) or a ``result``; a function name is a string, ``args`` is a
list, and ``kwargs`` is an object with string keys. The *values* of
``args`` and ``kwargs``, and any ``result``, are pickled Python objects,
base64-encoded so they fit inside the JSON.

A value that cannot be pickled on the sender side, or cannot be
unpickled on the receiver side (for example because its type does not
exist there), becomes a :class:`Placeholder` carrying the string of the
exception. A receiver therefore immediately knows that such a value did
not come back as its original type. Both sides assume everything is
serializable; any failure falls back to a ``Placeholder``.
"""

import base64
import json
import pickle
from typing import Any

__all__ = ["Placeholder", "RpcError", "decode", "encode"]


class Placeholder:
    """Stand-in for a value that could not be (de)serialized.

    ``error`` is the string of the exception raised when the value could
    not be pickled (on the sender side) or unpickled (on the receiver
    side). Receiving a ``Placeholder`` means the value did not come back
    as its original type.
    """

    def __init__(self, error: str) -> None:
        self.error = error

    def __repr__(self) -> str:
        return f"Placeholder({self.error!r})"


class RpcError(Exception):
    """Raised when a remote function call failed on the other side."""

    def __init__(self, type: str, message: str) -> None:
        super().__init__(f"{type}: {message}")
        self.type = type
        self.message = message


def _pack(value: Any) -> str:
    """Serialize ``value`` to a base64 string of its pickle.

    If ``value`` cannot be pickled, a ``Placeholder`` carrying the
    exception string is pickled instead.
    """
    try:
        data = pickle.dumps(value)
    except Exception as exc:  # noqa: BLE001 - any failure becomes a Placeholder
        data = pickle.dumps(Placeholder(str(exc)))
    return base64.b64encode(data).decode("ascii")


def _unpack(text: str) -> Any:
    """Deserialize a base64 pickled value.

    If the value cannot be unpickled (for example because its type does
    not exist on this side), a ``Placeholder`` carrying the exception
    string is returned instead.
    """
    try:
        return pickle.loads(base64.b64decode(text.encode("ascii")))
    except Exception as exc:  # noqa: BLE001 - any failure becomes a Placeholder
        return Placeholder(str(exc))


def encode(message: dict) -> str:
    """Serialize an RPC message to a JSON string.

    Message type, call id, function name, and error details stay plain
    JSON; the values of ``args`` and ``kwargs``, and any ``result``, are
    pickled.
    """
    packed = dict(message)
    if "args" in packed:
        packed["args"] = [_pack(value) for value in packed["args"]]
    if "kwargs" in packed:
        packed["kwargs"] = {
            key: _pack(value) for key, value in packed["kwargs"].items()
        }
    if "result" in packed:
        packed["result"] = _pack(packed["result"])
    return json.dumps(packed)


def decode(text: str) -> Any:
    """Parse an RPC message from a JSON string, restoring pickled values."""
    message = json.loads(text)
    if isinstance(message, dict):
        if "args" in message:
            message["args"] = [_unpack(value) for value in message["args"]]
        if "kwargs" in message:
            message["kwargs"] = {
                key: _unpack(value) for key, value in message["kwargs"].items()
            }
        if "result" in message:
            message["result"] = _unpack(message["result"])
    return message
