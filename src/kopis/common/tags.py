"""The standard HTML5 tag names, grouped by their content model.

A ``Kopis`` resolves a tag name on the app (``k.li``) to the
``browser.html`` builder (``k.html.li``) before it resolves it to the
short way for an RPC call, so these names are the unified vocabulary
for making elements on both sides.

- :data:`VOID_TAGS` — the W3C **void elements**: they cannot have
  children (``<br>``, ``<img src="...">``, ...);
- :data:`CONTAINER_TAGS` — the other standard elements: they can have
  children (``<li>``, ``<div>``);
- :data:`TAGS` — all the standard elements:
  ``CONTAINER_TAGS | VOID_TAGS``.
"""

__all__ = ["CONTAINER_TAGS", "TAGS", "VOID_TAGS"]

#: The standard HTML5 void elements: they cannot have children.
VOID_TAGS: frozenset[str] = frozenset(
    (
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    )
)

#: The standard HTML5 tags that can have children.
CONTAINER_TAGS: frozenset[str] = frozenset(
    (
        "a",
        "abbr",
        "address",
        "article",
        "aside",
        "audio",
        "b",
        "bdi",
        "bdo",
        "big",
        "blockquote",
        "body",
        "button",
        "canvas",
        "caption",
        "center",
        "cite",
        "code",
        "colgroup",
        "data",
        "datalist",
        "dd",
        "del",
        "details",
        "dfn",
        "dialog",
        "div",
        "dl",
        "dt",
        "em",
        "fieldset",
        "figcaption",
        "figure",
        "font",
        "footer",
        "form",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "head",
        "header",
        "html",
        "i",
        "iframe",
        "ins",
        "kbd",
        "label",
        "legend",
        "li",
        "main",
        "map",
        "mark",
        "math",
        "menu",
        "meter",
        "nav",
        "noscript",
        "object",
        "ol",
        "optgroup",
        "option",
        "output",
        "p",
        "picture",
        "pre",
        "progress",
        "q",
        "rb",
        "rp",
        "rt",
        "rtc",
        "ruby",
        "s",
        "samp",
        "script",
        "section",
        "select",
        "small",
        "span",
        "strike",
        "strong",
        "style",
        "sub",
        "summary",
        "sup",
        "svg",
        "table",
        "tbody",
        "td",
        "template",
        "textarea",
        "tfoot",
        "th",
        "thead",
        "time",
        "title",
        "tr",
        "tt",
        "u",
        "ul",
        "var",
        "video",
    )
)

#: All the standard HTML5 tag names: ``CONTAINER_TAGS | VOID_TAGS``.
TAGS: frozenset[str] = CONTAINER_TAGS | VOID_TAGS
