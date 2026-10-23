# Examples and where to find them

## In the repository (brython-dev/brython, branch 3.14)

- `www/gallery/` — runnable example apps, usually a `.html` plus a `.py` (`ajax.html`, `sudoku.py`, `kanban.py`, `calculator.html`, `drop_files.html`, `three_webgl_interactive_cubes.py`, `editor.py`, ...). `www/gallery/gallery_en.html` is the index with descriptions
- `www/doc/en/cookbook/` — short, focused recipes: hello world, basic markup, bind/unbind, content in a div, reading a file, local storage, drag and drop, select checkbox, table, validate form
- `www/doc/en/examples/` — examples embedded in the doc pages (e.g. the local storage todo app)
- `www/tests/` — development tools: `editor.html` (online editor) and `console.html` (online console)
- `demo.html` — installed by `brython-cli install`; a tour of creating elements, graphics, animations, Ajax requests
- `www/tutorial/` — the official tutorial, in en, es, fr, pt-br, it, br

## Online (3.14)

- Docs: https://brython.info/static_doc/3.14/en/intro.html
- Tutorial: https://brython.info/static_tutorial/en/index.html
- Gallery: http://brython.info/gallery/gallery_en.html
- Editor: http://brython.info/tests/editor.html
- Console: http://brython.info/tests/console.html

## Patterns worth copying

- `www/gallery/ajax.html` — Ajax request patterns: concise `ajax.get`/`ajax.post` and `ajax.Ajax()` side by side, 404 handling, cache-busting query string
- `www/gallery/sort_table.html` — build a sortable table with `browser.html` (`TABLE`, `TR`, `TH`, `A`, `link.clone()`)
- `www/gallery/webworker_mdn.html` — a complete web worker pair (`browser.worker`)
- `www/doc/en/cookbook/local_storage.md` — persist a todo app with `browser.local_storage` + `json`
- `www/doc/en/cookbook/drag_drop.md`, `validate_form.md`, `table.md` — DOM event and form patterns
- `www/gallery/editor.py` and `www/tests/console.py` — embedding a Python editor / interactive console in a page
- `www/gallery/three_webgl_interactive_cubes.py` — importing a JS library (three.js) with `javascript.import_modules`
