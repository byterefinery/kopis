"""Kopis: pure-Python web development (server side).

This is the server-side half of the ``kopis`` package: it runs on CPython
and serves a web application — a root directory of static files, an HTML
document at ``/``, and RPC to and from clients. It shares its API with
the client-side half (the ``kopis.client`` subpackage, which runs in the
browser under Brython); only the implementations differ. By default
(``use=["brython"]``), the whole package is served to the browser and the
running script is attached to the document, so ``import kopis`` in
browser code resolves to the client side there.

The server has no live DOM and never parses the HTML it serves (the
browser does, in the brython way): ``document`` is a stand-in of the
brython ``browser.document`` object (a ``DOMNode`` of the served HTML
string), ``DOMNode`` and ``DOMEvent`` are stand-ins of the brython
classes, and ``bind``, ``html``, ``window``, ``ajax``, ``timer``, and
``javascript`` are stand-ins of the brython objects — the unified code
works on them identically to the browser, with the brython semantics
where they matter (``<=`` appends, ``+`` and ``*`` group and clone,
``bind`` binds, ``html.TAG(...)`` creates elements), but nothing is
rendered or fired.
"""

from . import aio, javascript
from .app import Kopis
from .browser import DOMEvent, DOMNode, ajax, bind, document, html, timer, window
from ..common import RPCHandle, RpcError

__all__ = [
    "DOMEvent",
    "DOMNode",
    "Kopis",
    "RPCHandle",
    "RpcError",
    "aio",
    "ajax",
    "bind",
    "document",
    "html",
    "javascript",
    "timer",
    "window",
]
