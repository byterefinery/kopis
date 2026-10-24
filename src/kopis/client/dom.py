"""The brython DOM append interface, extended (client side).

In plain brython, ``element <= "text"`` appends a single text node: a
string containing HTML markup is added literally, the markup escaped
as visible text. This module extends the append interface so that a
string argument is first parsed by the browser as an HTML fragment,
and the fragment's top-level nodes (elements, text, and comments) are
then appended, in order. A string without markup still appends a text
node, so plain text keeps working as before.

The extension applies to the ``<=`` operator and to its aliases — the
``attach`` method (the method behind ``<=`` in brython) and the native
``append`` method — on every element, including the document. It is
installed once, by :func:`install` (called when :mod:`kopis.client` is
imported); it does not change any other brython behavior (in
particular, ``+`` still groups, and a string grouped with ``+`` is
still a text node).
"""

from browser import DOMNode, window

__all__ = ["install"]

#: The installer script. Finds the brython base class of the DOM nodes
#: (the class owning the ``attach`` function that ``<=`` goes through)
#: and makes string arguments of ``attach`` and of the native
#: ``append`` method parse the string as an HTML fragment and append
#: the fragment's top-level nodes. Idempotent.
_JS_INSTALL = """
(function () {
  if (window.__kopis_dom__) return 'ok'
  var c = $B.get_class(document.body), base = null, seen = 0
  while (c && seen++ < 16) {
    if (c.tp_funcs && Object.prototype.hasOwnProperty.call(c.tp_funcs, 'attach')) {
      base = c
      break
    }
    c = c.tp_bases ? c.tp_bases[0] : null
  }
  if (!base) return 'no DOMNode base class found'

  // The top-level nodes of an HTML fragment (parsed by the browser;
  // nothing is executed).
  function fragment_nodes(html) {
    var tpl = document.createElement('template')
    tpl.innerHTML = html
    var nodes = []
    for (var n = tpl.content.firstChild; n; n = n.nextSibling) {
      nodes.push(n)
    }
    return nodes
  }

  window.__kopis_dom__ = {base: base}

  // <= (brython's richcompare goes through the base attach function).
  var orig_attach = base.tp_funcs.attach
  base.tp_funcs.attach = function (self, other) {
    if (typeof other === 'string') {
      var nodes = fragment_nodes(other)
      for (var i = 0; i < nodes.length; i++) {
        orig_attach(self, nodes[i])
      }
      return self
    }
    return orig_attach(self, other)
  }

  // The native append method (ParentNode.append: elements, document,
  // and document fragments).
  function patch_append(proto) {
    if (!proto || typeof proto.append !== 'function') return
    var orig_append = proto.append
    proto.append = function () {
      var args = []
      for (var i = 0; i < arguments.length; i++) {
        if (typeof arguments[i] === 'string') {
          var nodes = fragment_nodes(arguments[i])
          for (var j = 0; j < nodes.length; j++) {
            args.push(nodes[j])
          }
        } else {
          args.push(arguments[i])
        }
      }
      return orig_append.apply(this, args)
    }
  }
  patch_append(Element.prototype)
  patch_append(Document.prototype)
  patch_append(DocumentFragment.prototype)
  return 'ok'
})()
"""


def _attach(self: DOMNode, other: object) -> DOMNode:
    """Append ``other`` as a child (the brython ``attach``, the method
    behind ``<=``).

    A string is first parsed as an HTML fragment (see the module
    docstring). Returns ``self``, so calls can be chained.
    """
    return self <= other


def install() -> None:
    """Install the extension (a no-op if it is already installed)."""
    res = window.eval(_JS_INSTALL)
    if res != "ok":
        raise RuntimeError(f"could not extend the DOM append interface: {res}")
    window["__kopis_dom__"]["base"].attach = _attach
