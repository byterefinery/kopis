---
name: brython-3-14
description: Python 3.14 in the web browser via Brython. Use when writing client-side web apps in Python, reading or modifying DOM elements from Python, binding DOM events, building HTML programmatically with browser.html, making Ajax requests with browser.ajax, calling Javascript libraries from Python, or installing, developing and deploying a Brython app with brython-cli.
license: BSD-3-Clause
compatibility: Any modern web browser. CDN usage needs no installation. Local development needs a web server such as python -m http.server. brython-cli needs CPython with pip.
metadata:
  tags:
    - python
    - web
    - browser
    - dom
    - client-side
---

# brython 3.14

## Overview

Brython (Browser Python) is an implementation of Python 3 that runs in the browser, replacing Javascript as the page scripting language. Since Brython 3.8.0 the two track the same version number, so Brython 3.14 implements Python 3.14. It supports Python 3 syntax and the pure-Python part of the CPython standard library (features that need disk access or C extensions are excluded), plus the `browser` and `javascript` packages that expose the DOM, events, Ajax, storage, web workers and Javascript objects.

What is built in:

- `browser.document` — the current page, dict-like, keyed by element id
- `browser.window` — the browser window; all Javascript globals are its attributes
- `browser.html` — create and compose HTML elements in Python (jQuery-like API)
- `browser.ajax` — GET/POST/... requests with Pythonic callbacks
- `javascript` — import and call Javascript modules and objects from Python

## Usage

Minimal page (from the official README):

```html
<html>
<head>
<script src="https://cdn.jsdelivr.net/npm/brython@3.14/brython.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/brython@3.14/brython_stdlib.js"></script>
</head>
<body>
<script type="text/python">
from browser import bind, document, alert

@bind(document["mybutton"], "click")
def echo(event):
    alert(document["zone"].value)
</script>
<input id="zone"><button id="mybutton">click !</button>
</body>
</html>
```

Rules for that page:

- `brython.js` (the engine) is always required; it already includes `browser`, `browser.html` and `javascript`
- `brython_stdlib.js` is only needed when the script imports modules of the standard library (e.g. `json`, `datetime`)
- Larger programs go in a separate file loaded with `<script type="text/python" src="app.py">`; the file must be in the same domain as the page
- Serve the page over http (e.g. `python -m http.server`), never open it as a local file — see Gotchas

Local development loop:

```console
pip install brython
brython-cli install            # in an empty app dir; creates brython.js, brython_stdlib.js, demo.html
python -m http.server 8000     # then open http://localhost:8000/demo.html
brython-cli make_modules       # shrink the stdlib bundle to the modules the app actually uses
```

Execution options (debug, args, pythonpath, cache, ...) are set with a `<brython-options>` tag in `<body>` or as attributes of a `<script>` tag — see [05-install-cli-options](references/05-install-cli-options.md).

## Gotchas

- **Serve over http, not file://** — module imports, `open()` and `<script src="app.py">` all go through Ajax, and browsers refuse Ajax under the `file` protocol. If the app works on `localhost` but breaks when the file is opened directly, that is why.
- **No C extensions** — Brython executes Python, not C. `numpy` and the data-science stack will not work. Only pure-Python packages can be added, via `brython-cli add_package <name>` after `pip install <name>`.
- **No `requests` or `urllib.request`** — browsers limit the HTTP requests a page can send. Use `browser.ajax` instead (see [03-ajax-http](references/03-ajax-http.md)).
- **`brython_stdlib.js` is 4 MB+** — generate a smaller `brython_modules.js` holding only the modules the app imports (`brython-cli make_modules`) and swap the `<script>` tag to it.
- **`class` is a Python keyword** — in `browser.html` write `Class="foo"`. The `style` keyword must be a dict with Javascript property names (`backgroundColor`), not CSS (`background-color`). Hyphenated attribute names need underscores, or pass a dict: `**{"v-on:click": "count++"}`.
- **One element instance is one DOM node** — reusing the same `browser.html` object in two places renders it only in the last one. Use `.clone()` for repeated content.
- **`.py` URLs can be hijacked by the server** — if the server treats the Ajax call to `app.py` as a CGI execution, the page breaks. Rename the file to `.bry` and keep `type="text/python"`.
- **`print()` goes to the browser console**, not the page. Open devtools to see it, or write into an element's `.text` / `.html` instead.
- **External scripts are same-domain only** — both `<script src="app.py">` and module imports must resolve to URLs on the same domain as the page.
- **Modules must be utf-8** — the encoding declaration line at the top of a script is ignored.
- **`<brython-options>` goes in `<body>`, not `<head>`** — and script-level attributes override page-level ones. The old `onload="brython({debug: 2})"` syntax is only kept for pre-3.12 pages.

## References

- [01-dom-events](references/01-dom-events.md) — element access by id and CSS selector, properties (`html`, `text`, `class_name`, `attrs`), `<=` and `del`, events (`bind`/`unbind`, `DOMEvent`, `@bind`), query string
- [02-html-builder](references/02-html-builder.md) — creating and composing elements with `browser.html`; `maketag`, `attribute_mapper`
- [03-ajax-http](references/03-ajax-http.md) — `browser.ajax` request functions, response modes, callbacks, file upload
- [04-javascript-interop](references/04-javascript-interop.md) — calling Javascript from Python; `import_js`/`import_modules`, JS constructors
- [05-install-cli-options](references/05-install-cli-options.md) — CDN and local install, `brython-cli` commands, import resolution, `<brython-options>`
- [06-workers-timers-storage](references/06-workers-timers-storage.md) — web workers, timers, local/session storage, other browser APIs
- [07-examples](references/07-examples.md) — where to find working examples: gallery, tutorial, online editor, cookbook
