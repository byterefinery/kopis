# kopis

Kopis (aka "kopis") is a library facilitating web application development in pure Python, eliminating the need for HTML, CSS, or JavaScript/TypeScript.

Kopis supports almost all NPM packages, JavaScript/TypeScript, and CSS, with everything seamlessly built/bundled in the background. It is great for (both) prototyping (and production ready solutions), letting developers focus on application logic instead of dealing with the details of JS/TS bundlers. The main focus is on easy development with focus on Developer Experience (DX).

## Python runtimes

Kopis runs Python on both ends of the web stack:

- **Server-side:** CPython 3.14
- **Client-side:** [Brython 3.14](https://brython.info/static_doc/3.14/en/intro.html) (Python compiled to run in the browser)

## Code layout

The `kopis` module exists in two versions — same name, different meaning and implementation — in separate directories:

- `src/server/kopis.py` — the **server-side** module. Runs on CPython, provides the web application (root directory, HTML document, RPC) and is what `import kopis` resolves to in CPython code.
- `src/client/kopis.py` — the **client-side** module. Runs in the browser under Brython; it has no web server, only the RPC client (`Kopis`) and the browser objects client code works with (`document`, `aio`, `javascript`). It is never imported by CPython.

With `Kopis(use="brython")`, the server serves the client-side module at `/kopis.py`, so `import kopis` in browser code resolves to the client-side module.

## Examples

Each example lives in its own directory and is run from within that directory using `uv run`, e.g. for [`examples/ex0`](examples/ex0/):

```sh
cd examples/ex0
uv run ex0.py
```
