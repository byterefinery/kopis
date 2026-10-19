---
name: aiohttp-3-14-1
description: >
  asyncio-based HTTP client/server framework for Python (aiohttp 3.14.1).
  Use when building or interacting with async HTTP services, REST APIs,
  WebSocket connections, or async web scraping. Covers ClientSession,
  Application/routing, middlewares, FileResponse, multipart uploads,
  streaming, tracing, and testing with TestClient/TestServer.
metadata:
  tags:
    - python
    - http
    - async
    - web
    - networking
---

# aiohttp 3.14.1

## Overview

aiohttp is a full-featured asyncio HTTP library providing both a client and a server.
It is built on top of `asyncio` and uses `yarl` for URLs, `multidict` for headers/params,
and `attrs` for data classes. Default timeout is `ClientTimeout(total=300, sock_connect=30)`.

### Core imports

```python
# Client
from aiohttp import ClientSession, ClientTimeout, ClientResponseError, TCPConnector

# Server
from aiohttp import web
from aiohttp.web import Application, Request, Response, StreamResponse, json_response, FileResponse

# WebSockets
from aiohttp import WSMsgType, WSCloseCode

# Helpers
from aiohttp import FormData, MultipartWriter, MultipartReader, Payload
from aiohttp import TraceConfig, BasicAuth, encode_basic_auth
from aiohttp import hdrs  # HTTP header constants
```

## Usage

### HTTP Client — basic pattern

```python
import aiohttp

async with aiohttp.ClientSession() as session:
    async with session.get("https://httpbin.org/get") as resp:
        resp.raise_for_status()
        data = await resp.json()
```

### HTTP Client — context manager shortcut

```python
async with aiohttp.request("GET", "https://httpbin.org/get") as resp:
    body = await resp.read()
```

### HTTP Server — minimal app

```python
from aiohttp import web

async def handle(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})

app = web.Application()
app.router.add_get("/", handle)
web.run_app(app, host="0.0.0.0", port=8080)
```

### HTTP Server — decorator routing

```python
routes = web.RouteTableDef()

@routes.get("/items/{item_id}")
async def get_item(request: web.Request) -> web.Response:
    item_id = request.match_info["item_id"]
    return web.json_response({"id": item_id})

app = web.Application()
app.router.add_routes(routes)
```

### WebSocket server

```python
from aiohttp import web, WSMsgType

async def ws_handler(request: web.Request) -> web.WebSocketResponse:
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    async for msg in ws:
        if msg.type == WSMsgType.TEXT:
            await ws.send_str(f"echo: {msg.data}")
        elif msg.type == WSMsgType.ERROR:
            break
    return ws

app = web.Application()
app.router.add_get("/ws", ws_handler)
```

### WebSocket client

```python
async with session.ws_connect("wss://echo.websocket.org") as ws:
    await ws.send_str("hello")
    async for msg in ws:
        if msg.type == WSMsgType.TEXT:
            print(msg.data)
        elif msg.type in (WSMsgType.CLOSE, WSMsgType.ERROR):
            break
```

### Middleware

```python
from aiohttp import web

@web.middleware
async def timing_middleware(request: web.Request, handler) -> web.StreamResponse:
    import time
    start = time.monotonic()
    resp = await handler(request)
    resp.headers["X-Response-Time"] = str(time.monotonic() - start)
    return resp

app = web.Application(middlewares=[timing_middleware])
```

### Sub-applications

```python
sub = web.Application()
sub.router.add_get("/sub", handler)
app = web.Application()
app.add_subapp("/api", sub)
```

## Gotchas

- **Always `await session.close()` or use `async with`** — unclosed sessions leak connections and trigger `ResourceWarning`.
- **`base_url` must end with `/`** — `ClientSession(base_url="https://api.example.com")` raises `ValueError`; use `"https://api.example.com/"`.
- **`data` and `json` are mutually exclusive** — passing both to `session.request()` raises `ValueError`.
- **Redirects consume the body** — after a redirect, the original payload may be consumed. Use bytes or seekable files for redirectable POST bodies, or set `allow_redirects=False`.
- **`auth` parameter is deprecated** — use `headers={"Authorization": aiohttp.encode_basic_auth(login, password)}` instead. Same for `proxy_auth` (use `proxy_headers`).
- **`BasicAuth` is deprecated** — use `encode_basic_auth(login, password)` directly.
- **`read_timeout`/`conn_timeout` are deprecated** — use `timeout=ClientTimeout(total=..., connect=...)`.
- **`session.loop` and `connector.loop` are deprecated** — use `asyncio.get_running_loop()`.
- **`resp.content_length` can be `None`** — always check before arithmetic; use `await resp.read()` for unknown sizes.
- **`resp.json()` raises `ContentTypeError`** if Content-Type is not JSON — use `await resp.text()` and `json.loads()` for non-JSON content types.
- **Server handlers must be `async`** — sync handlers trigger a deprecation warning and are wrapped. Always write `async def handler(request)`.
- **`StreamResponse.prepare()` is idempotent** — calling it again returns `None`. Check `resp.prepared` before writing.
- **`resp.raise_for_status()` must be called explicitly** — aiohttp does not auto-raise on 4xx/5xx. Set `raise_for_status=True` on the session or call it per-response.
- **`FileResponse` uses `sendfile` when available** — set `AIOHTTP_NOSENDFILE=1` env var to force chunked fallback.
- **`normalize_path_middleware` cannot both append and remove slashes** — only one of `append_slash`/`remove_slash` can be `True`.
- **`client_max_size` defaults to 1 MB** — raise `ValueError` on larger bodies. Set `Application(client_max_size=...)` to increase.
- **`resp.history` is a tuple** — populated only when redirects occurred. Empty tuple means no redirects.
- **Inheritance from `ClientSession` or `Application` triggers deprecation warnings** — compose instead of subclass.
- **`resp.release()` vs `resp.close()`** — `release()` returns the connection to the pool; `close()` closes it. Use `release()` when you don't need the body.
- **WebSocket `decode_text=False`** keeps messages as `bytes` — the default `True` decodes text frames to `str`.
- **`session.ws_connect()` returns a context manager** — use `async with session.ws_connect(...) as ws:` for proper cleanup.
- **`TraceConfig` signals are frozen at session creation** — do not modify `on_request_start` etc. after creating `ClientSession`.
- **`verify_ssl`, `ssl_context`, `fingerprint` are deprecated** — use `ssl=context`, `ssl=False`, or `ssl=Fingerprint(bytes)`.
- **`ssl=None` is deprecated** — explicitly use `ssl=True`.
- **Cookie handling preserves raw headers** — `DummyCookieJar` skips all cookie processing; use `CookieJar(unsafe=True)` to accept all cookies.
- **`resp.start()` was removed** — responses auto-start; use `resp.read()`, `resp.text()`, `resp.json()`, or iterate `resp.content`.
- **`payload_streamer` is the `streamer` function** — use `aiohttp.streamer()` for streaming payloads.
- **`set_zlib_backend()` controls compression** — call before creating sessions to switch zlib implementation.

## References

- [01-http-client](references/01-http-client.md) — ClientSession, request methods, ClientResponse, standalone request()
- [02-http-server](references/02-http-server.md) — Application, Request, Response, StreamResponse, FileResponse, json_response
- [03-routing](references/03-routing.md) — UrlDispatcher, RouteTableDef, decorators, View, sub-apps, static files
- [04-websockets](references/04-websockets.md) — WebSocket client (ClientWebSocketResponse) and server (WebSocketResponse), WSMsgType
- [05-connectors-timeouts](references/05-connectors-timeouts.md) — TCPConnector, UnixConnector, NamedPipeConnector, ClientTimeout, SSL
- [06-middlewares-tracing](references/06-middlewares-tracing.md) — Server/client middlewares, TraceConfig, signal hooks, DigestAuthMiddleware
- [07-multipart-payloads](references/07-multipart-payloads.md) — FormData, MultipartReader/Writer, Payload registry, streaming
- [08-testing](references/08-testing.md) — TestClient, TestServer, RawTestServer, pytest fixtures, loop management
- [09-exceptions](references/09-exceptions.md) — Client exception hierarchy, HTTPException web responses, error handling
- [10-advanced](references/10-advanced.md) — Streams, CookieJar, resolvers, workers, compression, helpers
