# DOM access and events

Source pages in the 3.14 docs: `access`, `attributes`, `events`, `query` (https://brython.info/static_doc/3.14/en/).

## Getting elements

- `document["id"]` — element by id; `document` behaves like a dict keyed by element id. Raises `KeyError` when no element has that id
- `elt.get(name=N)` — list of descendants whose attribute `name` equals `N`
- `elt.get(selector=S)` / `elt.select(S)` — list of descendants matching CSS selector `S`
- `elt.select_one(S)` — first matching descendant, or `None`
- `document.select("#container")` is the same as `[document["container"]]`; other selectors: `.foo`, `form`, `H1.bar`, `a[title]`, `#tid td`

## Reading and writing element state

| Name | Kind | Meaning |
|---|---|---|
| `html` | R/W str | HTML code inside the element |
| `text` | R/W str | text content inside the element |
| `class_name` | R/W str | the tag's `class` attribute |
| `attrs` | dict-like | HTML attributes: set, get (raises `KeyError` if absent), `del`, iterate |
| `children` | R list | element children (not text nodes) |
| `parent` | R | parent element (`None` for the document) |
| `height`, `width` | R/W int | pixels; same as `style.height` / `style.width` but integers |

DOM rule that bites: attributes and properties are distinct. Attribute values are always strings; property values can be any type. Setting the `class` attribute does not set a `class_name` attribute (the DOM property behind the `class` attribute is `className`). Iterate attributes with `for name, value in elt.attrs.items()`.

## Adding, iterating, removing

```python
from browser import document, html
document["zone"] <= html.INPUT(id="data")   # append child; think of <= as a left arrow
for child in element: ...                   # iterate children
del document["zone"]                        # remove element from the page
```

Other methods: `elt.select(S)`, `elt.closest(tag_name)` (first parent with that tag, raises `KeyError` if none), `elt.index([selector])` (position among siblings), `elt.inside(other)`, `elt.clear()` (remove all descendants). The `options` of a `SELECT` is list-like: index access, `append`, `insert`, `del`.

## Events

```python
def show(ev):
    print(ev.target.text, ev.x, ev.y)

document["btn"].bind("click", show)
document["btn"].unbind("click", show)    # omit the handler to remove all handlers for that event
document["btn"].events("click")          # list of current handlers
```

`browser.bind` as a decorator — the target is a DOMNode, or a CSS selector string (then the handler is bound to every matching element):

```python
from browser import document, bind

@bind(document["btn"], "mouseover")
def mouseover(ev): ...

@bind("div.foo", "enter")    # all DIVs with class="foo"
def enter(ev): ...
```

`DOMEvent` attributes (for every event type): `bubbles`, `cancelable`, `currentTarget`, `defaultPrevented`, `eventPhase`, `target`, `timeStamp`, `type`. Mouse events add `x`, `y` (window-relative). Methods: `ev.preventDefault()`, `ev.stopPropagation()`.

Fire an event manually — the event class is a JS constructor, so use its `new` attribute:

```python
from browser import window
event = window.MouseEvent.new("click")
element.dispatchEvent(event)
```

## Query string

`document.query` parses the page URL query string:

- `document.query[key]` — value, or a list of values when the key repeats; `KeyError` if absent
- `document.query.getfirst(key, default)` / `getvalue(key, default)` — first value or default
- `document.query.getlist(key)` — all values, or `[]`
