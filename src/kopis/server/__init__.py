"""Kopis: pure-Python web development (server side).

This is the server-side half of the ``kopis`` package: it runs on CPython
and serves a web application — a root directory of static files, an HTML
document at ``/``, and RPC to and from clients. It shares its API with
the client-side half (the ``kopis.client`` subpackage, which runs in the
browser under Brython); only the implementation differs. By default
(``use="brython"``), the whole package is served to the browser and the
running script is attached to the document, so ``import kopis`` in
browser code resolves to the client side there.

:class:`Document` and :class:`Element` are the classes of the minimal
DOM library (:mod:`kopis.common.dom`), which mirrors the brython
``browser`` objects: the server-side ``k.document`` is a
``kopis.common.dom.Document`` of the parsed document, and the elements
it hands out are ``kopis.common.dom.Element`` objects themselves.
``bind`` is the brython-style event decorator of the stand-in
``browser`` package (``kopis.browser``), so unified code gets the same
decorator on both sides.
"""

from . import aio
from .app import Kopis
from ..browser import bind
from ..common import Placeholder, RpcError, dom
from ..common.dom import Document, Element

__all__ = [
    "Document",
    "Element",
    "Kopis",
    "Placeholder",
    "RpcError",
    "aio",
    "bind",
    "dom",
]
