# kopis

Web application library in pure Python. Server-side: CPython 3.14 on the aiohttp web server. Client-side: [Brython 3.14](https://brython.info/static_doc/3.14/en/intro.html). NPM packages, JS/TS, and CSS are bundled automatically in the background.

The `kopis` package exposes one unified API on both sides of the web stack; its `__init__.py` (`src/kopis/__init__.py`) differentiates the implementations at import time: the `server` subpackage (`src/kopis/server/`) runs on CPython and the `client` subpackage (`src/kopis/client/`) runs in the browser under Brython. Application code is a single file (e.g. `examples/ex0/app.py`) that runs on both sides: on the server, `Kopis` builds the app and `k.run()` starts the HTTP server; with `Kopis(use="brython")` the app file is also attached to the document as a Brython script, so the same code runs in the browser, where `k.run()` is a no-op and `k.document` works on the live DOM. Developers write the unified code once and do not deal with the server/client split.

## Tooling

- `uv` — project management and running scripts
- `ty` — type-checking
- `ruff` — linting

## Examples

Each example lives in its own directory. Run it from within that directory:

```sh
cd examples/ex0
uv run app.py
```
