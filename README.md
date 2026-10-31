# kopis

Kopis (aka "kopis") is a library facilitating web application development in pure Python, eliminating the need for HTML, CSS, or JavaScript/TypeScript.

Kopis supports almost all NPM packages, JavaScript/TypeScript, and CSS, with everything seamlessly built/bundled in the background. It is great for (both) prototyping (and production ready solutions), letting developers focus on application logic instead of dealing with the details of JS/TS bundlers. The main focus is on easy development with focus on Developer Experience (DX).

## Python runtimes

Kopis runs Python on both ends of the web stack:

- **Server-side:** CPython 3.14
- **Client-side:** [Brython 3.14](https://brython.info/static_doc/3.14/en/intro.html) (Python compiled to run in the browser)

## Code layout

The `kopis` package is imported on both sides of the web stack, and differentiates the implementations at import time based on the running Python implementation. Both sides re-export the **same unified API** — `Kopis` (with `register`, `rpc`, `document`, `add_static_file`, and `run`), and the brython objects `document`, `DOMNode`, `DOMEvent`, `bind`, `html`, `aio`, `ajax`, `timer`, `window`, and `javascript` — so a single application file runs unmodified on both sides; only the implementations differ. Developers import the brython objects from `kopis`, never from `browser` or `javascript` directly:

- `src/kopis/common/` — code shared by both sides: the `Kopis` base class (the `register`/`rpc` registry, dispatch, and result settling), the RPC wire format (JSON messages with pickled values and the `RpcError` type), the `RPCHandle` type, which stands in for a value that does not travel — made by `Kopis.handle` (the wrap of a value that cannot be serialized) or `Kopis.get_handle` (an explicit handle to any object) — the live object stays on the side where it is, and the other side operates on it through the handle — and the `Magic` dummy stand-in, which also carries the brython DOM interface (`append`, `+`, `*`, `with`).
- `src/kopis/server/` — the **server-side** subpackage. Runs on CPython: the web application (root directory, HTML document at `/`, RPC server over WebSocket), the stand-ins of the brython `browser` objects (`document`, `DOMNode`, `DOMEvent`, `bind`, `html`, `window`, `ajax`, `timer`) and of the `javascript` module, and the `aio` facade. The server has no live DOM and never parses the HTML it serves (the browser does, in the brython way): `document` is a stand-in of the brython `browser.document` object. `k.run()` starts the web server.
- `src/kopis/client/` — the **client-side** subpackage. Runs in the browser under Brython; it has no web server (`k.run()` is a no-op): the RPC client and the re-exports of the built-in `browser`/`javascript` modules. `k.document` is the live DOM.

Values passed between the sides are pickled, so objects are restored on the other end as long as their type exists there. A value that cannot be pickled does not travel: sending it raises, and `k.get_handle(obj)` wraps it in an `RPCHandle` instead — a magic type through which the other side operates on the live object (the owner side applies each operation and decides whether it can be performed); a value that cannot be unpickled on the other end is reported back as the error of the message that carried it. A handle prints as `<RPCHandle local ...>` or `<RPCHandle remote ...>` — `local` when this side owns the live object, `remote` when it came from the other side — followed by the true representation of the live object, which the owning side computes when the handle is made and which travels with it, so printing a handle never needs a round trip. A dropped connection loses no work: it is re-opened automatically, in-flight calls and ops are re-sent, and the server runs each (client, id) at most once — a re-sent message is answered from the stored result.

A kopis application is a single Python file. Running it with CPython starts the web server. By default, the server serves the whole `kopis` package at `/kopis/...` and attaches the application file to the document as a Brython script, so the same code also runs in the browser under Brython (where `import kopis` picks the client side and the document is built on the live DOM). Developers write the unified code once and do not deal with the server/client split.

## Examples

Each example lives in its own directory and is run from within that directory using `uv run`, e.g. for [`examples/ex0`](examples/ex0/):

```sh
cd examples/ex0
uv run app.py
```
