# Install, brython-cli, import resolution, options

## Getting Brython

CDN (no installation):

```html
<script src="https://cdn.jsdelivr.net/npm/brython@3.14/brython.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/brython@3.14/brython_stdlib.js"></script>
```

- `brython@3` = latest 3.x, `brython@3.14` = latest 3.14.x, `brython@3.14.0` = pinned
- cdnjs mirror: `https://cdnjs.cloudflare.com/ajax/libs/brython/3.14.0/brython.min.js` and `.../brython_stdlib.min.js`

Local install:

```console
pip install brython
brython-cli install            # in an empty app dir; --no-demo skips demo.html
python -m http.server 8000     # serve it, then open http://localhost:8000/demo.html
pip install brython --upgrade
brython-cli update             # refresh brython.js / brython_stdlib.js in the app dir
```

Alternative without pip: download the `Brython-x.y.z.zip` from the GitHub releases page and unzip it. The distribution contains `brython.js` (engine; includes `browser`, `browser.html`, `javascript`), `brython_stdlib.js` (all supported stdlib modules), `index.html`, `demo.html`.

## brython-cli commands

| Command | Purpose |
|---|---|
| `install` (alias `init`) | initialize an empty dir with the Brython files; `--install-dir`, `--no-demo` |
| `update` | replace `brython.js` / `brython_stdlib.js` with the latest known to the CLI; `--update-dir` |
| `add_package <name>` | copy a pure-Python package from the current CPython environment into the app's `Lib/site-packages` |
| `make_modules` | create `brython_modules.js` with only the modules the application uses; `--reset`, `-o` |
| `make_package <name>` | bundle a pure-Python package into a loadable `<name>.brython.js` "Brython package"; `--src-dir`, `--exclude-dirs`, `-o` |
| `make_dist` | make a PyPI distribution of a Brython application |
| `make_file_system <vfs> [prefix]` | make a virtual file system |
| `start_server [port] [--bind addr]` | development server (default port 8000, localhost) |
| `--version` | print the Brython version |

## Import resolution

Brython uses the CPython mechanism: the standard library, then `X.py` or `X/__init__.py` next to the script, then the application `site-packages` (created by `add_package`). The browser has no filesystem, so every lookup is an Ajax call — hence the same-domain and file:// limits.

- Modules must be encoded in utf-8; an encoding declaration at the top of the file is ignored
- A `<script type="text/python" id="module">` already executed on the page can be imported by its id
- `brython_stdlib.js` is 4 MB+; `brython-cli make_modules` parses all Python code in the app directory and writes `brython_modules.js` with only what is used — then swap the `<script>` tag to it. The CPython that runs it must parse the app's syntax (e.g. `match`/`case` needs CPython 3.10+)
- `brython-cli make_package` produces a standalone `<name>.brython.js` that a page loads like a script to distribute a module/package without a server-side build

## file:// limitations

Opening an HTML file directly (file protocol) disables:

- loading external scripts with `<script src="app.py">`
- importing modules or packages located next to the page
- reading files with `open()`

All three rely on Ajax, which browsers refuse under file://. Stdlib imports still work if `brython_stdlib.js` is loaded. The fix is a local server (`python -m http.server` or `brython-cli start_server`).

## Execution options

Page level — a `<brython-options>` tag, preferably in `<body>`, not `<head>`:

```xml
<brython-options debug="1" cache="true"></brython-options>
```

Script level — attributes of the `<script>` tag; a script-level option overrides the page-level one.

Page-only options:

- `ids` — space-separated list of script ids to execute (empty string = execute none); by default all scripts run
- `indexedDB` — whether compiled stdlib modules can be cached in IndexedDB (default `true`)

Page- or script-level options:

- `args` — command-line-like strings, available as `sys.argv`
- `cache` — use the browser cache for module imports, `<script src>` loads and `open()` (default `false`)
- `debug` — 1 (default) errors to the console; 2 also prints the generated Javascript; 10 also prints imported modules
- `js_tab` — indentation of the generated Javascript, 1-4 spaces (default 2)
- `pythonpath` — space-separated list of extra module search paths
- `static_stdlib_import` — use the static mapping table in `stdlib_paths.js` for stdlib imports (default `true`)

The pre-3.12 syntax `<body onload="brython({debug: 2})">` still works for compatibility; when both are present, the values passed to `brython()` replace those of the `<brython-options>` tag.
