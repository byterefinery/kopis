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

A value that cannot be pickled on the sender side does not travel:
``encode`` raises, and the sender wraps the value in an explicit
:class:`RPCHandle` (``Kopis.get_handle``) instead — the live object
stays alive on the side where it is, and the handle travels. A value
that cannot be unpickled on the receiver side (for example because its
type does not exist there) is reported to the sender as the error of
the message that carried it. ``decode`` takes a ``binder`` (the
receiving ``Kopis``) that binds every ``RPCHandle`` in the message to
it, so operations on the handles go through that side. A handle that
has come back to the side where it was made is unwrapped there: it is
replaced by the live object it wraps, which is right there on that
side (see :mod:`~kopis.common.handle`).
"""

import base64
import json
import pickle
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


def _pack(value: Any) -> str:
    """Serialize ``value`` to a base64 string of its pickle.

    Raises if the value cannot be pickled: such a value does not
    travel, and the sender wraps it in an explicit ``RPCHandle``
    (``Kopis.get_handle``) if it should.
    """
    data = pickle.dumps(value)
    return base64.b64encode(data).decode("ascii")


def _unpack(text: str) -> Any:
    """Deserialize a base64 pickled value.

    Raises if the value cannot be unpickled (for example because its
    type does not exist on this side); the receiver reports the error
    as the result of the message that carried the value.
    """
    return pickle.loads(base64.b64decode(text.encode("ascii")))


def _bind(value: Any, binder: Any) -> Any:
    """Bind every ``RPCHandle`` in ``value`` to ``binder`` (recursively),
    and replace a handle by its live object when the handle has come
    back to the side where it was made (see :func:`_unwrap`). Returns
    the value, possibly replaced — or, for an immutable container,
    a copy of it holding the replacement."""
    if isinstance(value, RPCHandle):
        value._kopis = binder
        live = _unwrap(value, binder)
        return live if live is not None else value
    if isinstance(value, dict):
        for key in list(value):
            new_key = _bind(key, binder)
            if new_key is not key:
                value[new_key] = value.pop(key)
            value[new_key] = _bind(value[new_key], binder)
        return value
    if isinstance(value, list):
        for i in range(len(value)):
            value[i] = _bind(value[i], binder)
        return value
    if isinstance(value, tuple):
        items = [_bind(item, binder) for item in value]
        if any(new is not old for new, old in zip(items, value)):
            return tuple(items)
        return value
    if isinstance(value, (set, frozenset)):
        items = [_bind(item, binder) for item in value]
        if any(new is not old for new, old in zip(items, value)):
            return type(value)(items)
        return value
    return value


def _unwrap(handle: RPCHandle, binder: Any) -> Any:
    """The live object a handle wraps, when the handle has come back to
    the side where it was made and the object is still kept there —
    otherwise ``None``.

    The side that made the handle keeps its live object in
    ``_handles``: when the handle comes back to it, that object is
    passed on instead of the handle — the object is already there, and
    the handle was only a stand-in for the trip.
    """
    if handle._owner_side != binder.side:
        return None
    if handle._owner_id != binder._owner_id:
        return None
    return binder._handles.get(handle._id)


def encode(message: dict) -> str:
    """Serialize an RPC message to a JSON string.

    Message type, call id, function name, op, and error details stay
    plain JSON; the values of ``args`` and ``kwargs``, any ``result``,
    and any ``handle`` are pickled. Raises if a value cannot be
    pickled: a call or op the side sends raises at the sender's call
    site, and a result it replies with is reported to the other side
    as the error of that call or op.
    """
    packed = dict(message)
    if "handle" in packed:
        packed["handle"] = _pack(packed["handle"])
    if "args" in packed:
        packed["args"] = [_pack(value) for value in packed["args"]]
    if "kwargs" in packed:
        packed["kwargs"] = {
            key: _pack(value) for key, value in packed["kwargs"].items()
        }
    if "result" in packed:
        packed["result"] = _pack(packed["result"])
    return json.dumps(packed)


def decode(text: str, binder: Any = None) -> Any:
    """Parse an RPC message from a JSON string, restoring pickled values.

    Raises if any pickled value cannot be unpickled. If ``binder`` (the
    receiving ``Kopis``) is given, every ``RPCHandle`` in the message is
    bound to it, so operations on the handles go through that side, and
    a handle that has come back to the side where it was made is
    replaced by the live object it wraps — in the values of ``args``,
    ``kwargs``, and ``result``. The ``handle`` of an ``op`` message
    stays a handle: it names the live object the owner applies the op
    to, and the owner needs its identity for that.
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
            if "handle" in message:
                _bind(message["handle"], binder)
            if "args" in message:
                message["args"] = [_bind(value, binder) for value in message["args"]]
            if "kwargs" in message:
                message["kwargs"] = {
                    key: _bind(value, binder)
                    for key, value in message["kwargs"].items()
                }
            if "result" in message:
                message["result"] = _bind(message["result"], binder)
    return message
