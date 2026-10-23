# kopis

Kopis (aka "kopis") is a library facilitating web application development in pure Python, eliminating the need for HTML, CSS, or JavaScript/TypeScript.

Kopis supports almost all NPM packages, JavaScript/TypeScript, and CSS, with everything seamlessly built/bundled in the background. It is great for (both) prototyping (and production ready solutions), letting developers focus on application logic instead of dealing with the details of JS/TS bundlers. The main focus is on easy development with focus on Developer Experience (DX).

## Python runtimes

Kopis runs Python on both ends of the web stack:

- **Server-side:** CPython 3.14
- **Client-side:** [Brython 3.14](https://brython.info/static_doc/3.14/en/intro.html) (Python compiled to run in the browser)

## Code layout

The `kopis` package is imported on both sides of the web stack, and its `__init__.py` (`src/kopis/__init__.py`) differentiates the implementations at import time based on the running Python implementation:

- `src/kopis/server/` — the **server-side** subpackage. Runs on CPython, provides the web application (root directory, HTML document, RPC) and starts the web server on `k.run()`.
- `src/kopis/client/` — the **client-side** subpackage. Runs in the browser under Brython; it has no web server (`k.run()` is a no-op), only the RPC client and the browser objects client code works with (`document`, `aio`, `javascript`).

Both sides expose the **same unified API** — `Kopis` (with `bind`, `rpc`, `document`, `add_static_file`, and `run`), `aio`, `RpcError`, and `Placeholder` — so a single application file runs unmodified on both sides; only the implementations differ. Values passed between the sides are pickled (see `src/kopis/_wire.py`), so objects are restored on the other end as long as their type exists there; anything that cannot be (de)serialized arrives as a `Placeholder` carrying the string of the exception.

A kopis application is a single Python file (e.g. `examples/ex0/app.py`). Running it with CPython starts the web server. With `Kopis(use="brython")`, the server serves the whole `kopis` package at `/kopis/...` and attaches the application file to the document as a Brython script, so the same code also runs in the browser under Brython (where `import kopis` picks the client side and the document is built on the live DOM). Developers write the unified code once and do not deal with the server/client split.

## Examples

Each example lives in its own directory and is run from within that directory using `uv run`, e.g. for [`examples/ex0`](examples/ex0/):

```sh
cd examples/ex0
uv run app.py
```
