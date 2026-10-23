"""Kopis: pure-Python web development (server side).

This is the server-side half of the ``kopis`` package: it runs on CPython
and serves a web application — a root directory of static files, an HTML
document at ``/``, and RPC to and from clients. It shares its API with the
client-side half (the ``kopis.client`` subpackage, which runs in the
browser under Brython); only the implementation differs. By default
(``use="brython"``), the whole package is served to the browser and the
running script is attached to the document, so ``import kopis`` in browser
code resolves to the client side there.

:class:`Element` is the element of the minimal DOM library
(:mod:`kopis.common.dom`): the elements the server-side
:class:`Document` view hands out are ``kopis.common.dom.Element``
objects themselves.
"""

from . import aio
from .app import Kopis
from .document import Document
from ..common import Placeholder, RpcError, dom
from ..common.dom import Element

__all__ = ["Document", "Element", "Kopis", "Placeholder", "RpcError", "aio", "dom"]
