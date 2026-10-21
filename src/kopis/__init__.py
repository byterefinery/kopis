"""Kopis: pure-Python web development."""

__all__ = ["Document", "Element", "Kopis"]

import platform


if platform.python_implementation() != 'Brython':
    # Server
    from .kopis import Document, Element, Kopis
else:
    # Client
    from .brython.browser import document  # noqa: F401
    from .client import Kopis
