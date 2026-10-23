# Creating HTML with browser.html

The `browser.html` module exposes one class per HTML tag (uppercase name): HTML4 tags (`A`, `DIV`, `INPUT`, ...), HTML5 (`ARTICLE`, `CANVAS`, `VIDEO`, ...), HTML5.1 (`DETAILS`, `DIALOG`, `SUMMARY`, ...). It is bundled in `brython.js`, so `brython_stdlib.js` is not needed for it.

## Creating elements

`TAG(content, **attributes)`:

- `content` is a Python value (string, number, another element). A **string is interpreted as an HTML snippet**; for plain text set the `text` property instead
- an iterable `content` makes one child per item
- keyword arguments become tag attributes; a hyphen must be written as underscore (`http_equiv`), or pass a dict: `html.BUTTON("hi", **{"v-on:click": "count++"})`
- `style` must be a dict with **Javascript property names**: `style={"backgroundColor": "#ADD8E6"}` (not `background-color`)
- `class` must be capitalized: `Class="container"` (Python keyword)

```python
from browser import document, html

link = html.A("Python", href="http://www.python.org")
row = html.TR(html.TH("Last") + html.TH("First"))     # + groups elements at the same level
t = html.TABLE()
t <= (TR(TD(i) + TD(i * i)) for i in range(10))      # <= appends, including whole iterables
document <= SELECT(OPTION(elt, value=i)
                  for i, elt in enumerate(["one", "two", "three"]))
```

Build up an element after creating it empty:

```python
link = html.A()
link <= html.B("connexion")
link.href = "http://example.com"
```

**One instance is one DOM node** — using the same object in two places renders it only in the last. Copy it with `.clone()`:

```python
document <= "Official Python Website: " + link
document <= html.P() + "again: " + link.clone()
```

Instances keep the attribute names of the matching DOM object (e.g. `selectedIndex` on `SELECT`), plus a few Pythonic additions.

## Helpers

- `html.maketag("P2")` — create a class for a custom tag, usable exactly like a standard tag class
- `html.tags` — dict mapping tag names to classes (includes `maketag` ones)
- `html.attribute_mapper` — function called to turn each keyword argument into an attribute name; the default replaces `_` with `-`. Replace it to support e.g. Vue-style `v_on_click`
