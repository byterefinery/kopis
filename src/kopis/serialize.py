"""Wire-format helpers shared by the server and the client.

RPC messages are JSON. Custom types participate by defining a
``to_json()`` method that returns plain JSON-able data; dataclasses and
objects with a ``__dict__`` are converted to a dict of their attributes;
anything else falls back to ``str()``. Neither side assumes the other
side has the same types — a value always arrives on the receiving end
as plain JSON data (dicts, lists, strings, numbers).
"""

import json
from typing import Any

try:
    from dataclasses import asdict, is_dataclass
except ImportError:  # Interpreter without dataclasses support.
    asdict = None
    is_dataclass = None

__all__ = ["RpcError", "decode", "encode"]


class RpcError(Exception):
    """Raised when a remote function call failed on the other side."""

    def __init__(self, type: str, message: str) -> None:
        super().__init__(f"{type}: {message}")
        self.type = type
        self.message = message


def _convert(value: object) -> object:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    to_json = getattr(value, "to_json", None)
    if callable(to_json):
        return _convert(to_json())
    if (
        is_dataclass is not None
        and asdict is not None
        and is_dataclass(value)
        and not isinstance(value, type)
    ):
        return _convert(asdict(value))
    if isinstance(value, dict):
        return {key: _convert(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_convert(item) for item in value]
    if hasattr(value, "__dict__"):
        return _convert(vars(value))
    return str(value)


def encode(value: object) -> str:
    """Serialize ``value`` to a JSON string, converting custom types to plain data."""
    return json.dumps(_convert(value))


def decode(text: str) -> Any:
    """Parse a JSON string into plain Python values."""
    return json.loads(text)
