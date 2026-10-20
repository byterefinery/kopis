"""Kopis: pure-Python web development."""

__all__ = ["Document", "Element", "Kopis"]

import platform
from typing import TYPE_CHECKING


if TYPE_CHECKING or platform.python_implementation() != 'Brython':
    # Server
    from .kopis import Document, Element, Kopis
else:
    # Client
    pass
