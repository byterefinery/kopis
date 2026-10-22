# kopis

Web application library in pure Python. Server-side: CPython 3.14 on the aiohttp web server. Client-side: [Brython 3.14](https://brython.info/static_doc/3.14/en/intro.html). NPM packages, JS/TS, and CSS are bundled automatically in the background.

The `kopis` package is imported on both sides of the web stack; its `__init__.py` (`src/kopis/__init__.py`) differentiates the sides at import time: the `server` subpackage (`src/kopis/server/`) runs on CPython and the `client` subpackage (`src/kopis/client/`) runs in the browser under Brython. With `Kopis(use="brython")` the whole package is served to the browser over HTTP, so `import kopis` in browser code picks the client side.

## Tooling

- `uv` — project management and running scripts
- `ty` — type-checking
- `ruff` — linting

## Examples

Each example lives in its own directory. Run it from within that directory:

```sh
cd examples/ex0
uv run server.py
```
