# kopis

Web application library in pure Python. Server-side: CPython 3.14 on the aiohttp web server. Client-side: [Brython 3.14](https://brython.info/static_doc/3.14/en/intro.html). NPM packages, JS/TS, and CSS are bundled automatically in the background.

The `kopis` module exists in two versions in separate directories: `src/server/kopis.py` (CPython) and `src/client/kopis.py` (Brython, browser). Same name, different implementation; the client-side module is served to the browser over HTTP (not imported by CPython).

## Tooling

- `uv` — project management and running scripts
- `ty` — type-checking
- `ruff` — linting

## Examples

Each example lives in its own directory. Run it from within that directory:

```sh
cd examples/ex0
uv run ex0.py
```
