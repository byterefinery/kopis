# HTTP Server

## Table of Contents

- [Application](#application)
- [Request](#request)
- [StreamResponse](#streamresponse)
- [Response](#response)
- [json_response()](#json_response)
- [FileResponse](#fileresponse)
- [run_app()](#run_app)
- [AppRunner / Sites](#apprunner--sites)
- [HTTP Exceptions](#http-exceptions)
- [Application lifecycle signals](#application-lifecycle-signals)

---

## Application

`web.Application` is the central object that holds routes, middlewares, and state.

### Construction

```python
app = web.Application(
    middlewares=[timing_middleware, auth_middleware],
    client_max_size=1024**2,  # max request body size (default 1MB)
)
```

### State management

```python
# Typed keys (recommended)
from aiohttp import web

DB_KEY = web.AppKey[str, "database_connection"]

async def init_db(app: web.Application) -> None:
    app[DB_KEY] = await create_pool(...)

# Access in handler
async def handler(request: web.Request):
    db = request.app[DB_KEY]
```

String keys work but trigger `NotAppKeyWarning` in strict mode.

### MutableMapping API

Application implements `MutableMapping[str, Any]`:

```python
app["key"] = value
value = app["key"]
del app["key"]
for k, v in app.items(): ...
```

### Sub-applications

```python
sub = web.Application()
sub.router.add_get("/sub", handler)
app = web.Application()
app.add_subapp("/api", sub)  # routes available at /api/sub
```

Sub-apps share the parent's middlewares. Each sub-app can have its own middlewares.

---

## Request

`web.Request` represents an incoming HTTP request.

### URL and path

| Property | Type | Description |
|---|---|---|
| `request.url` | `URL` | Full URL |
| `request.rel_url` | `URL` | Path + query (relative) |
| `request.path` | `str` | URL path |
| `request.query` | `MultiDictProxy` | Query parameters |
| `request.query_string` | `str` | Raw query string |
| `request.scheme` | `str` | `http` or `https` |
| `request.host` | `str` | Host header |
| `request.remote` | `str \| None` | Client IP |
| `request.path_qs` | `str` | Path + query string |
| `request.raw_path` | `str` | Raw (encoded) path |

### Headers

```python
# Headers are CIMultiDictProxy (case-insensitive, supports duplicates)
content_type = request.headers.get("Content-Type")
all_values = request.headers.getall("Accept")
```

### Match info (route parameters)

```python
# For route /items/{item_id}
item_id: str = request.match_info["item_id"]

# Access route handler
handler = request.match_info.handler

# Current app (in sub-app scenarios)
app = request.match_info.current_app
```

### Reading body

```python
# As bytes
body: bytes = await request.read()

# As text
text: str = await request.text()

# As JSON
data = await request.json()

# As form data (url-encoded or multipart)
data = await request.post()  # MultiDictProxy

# Multipart form
if request.content_type.startswith("multipart/"):
    reader = await request.multipart()
    async for part in reader:
        if part.filename:
            data = await part.read()
        else:
            text = await part.text()
```

### File uploads

```python
data = await request.post()
for field in data.values():
    if isinstance(field, web.FileField):
        # field: FileField(name, filename, file, content_type, headers)
        content = await field.file.read()
```

### Other properties

| Property | Type | Description |
|---|---|---|
| `request.method` | `str` | HTTP method |
| `request.version` | `HttpVersion` | HTTP version |
| `request.headers` | `CIMultiDictProxy` | Request headers |
| `request.content` | `StreamReader` | Raw body stream |
| `request.content_type` | `str` | Content-Type media type |
| `request.content_disposition` | `ContentDisposition` | Parsed Content-Disposition |
| `request.if_modified_since` | `datetime \| None` | If-Modified-Since header |
| `request.if_unmodified_since` | `datetime \| None` | If-Unmodified-Since header |
| `request.keep_alive` | `bool` | Keep-Alive requested |
| `request.transport` | `Transport` | Underlying transport |
| `request.task` | `asyncio.Task` | Handling task |
| `request.app` | `Application` | Current application |
| `request.writer` | `AbstractStreamWriter` | Response writer |
| `request.rel_url` | `URL` | Relative URL |

### Cloning

```python
clone = request.clone(method="POST", rel_url="/new/path")
```

---

## StreamResponse

Base class for all server responses. Use for streaming or low-level control.

### Construction

```python
resp = web.StreamResponse(
    status=200,
    reason=None,
    headers={"X-Custom": "value"},
)
```

### Writing

```python
async def handler(request: web.Request) -> web.StreamResponse:
    resp = web.StreamResponse()
    resp.content_type = "text/plain"
    await resp.prepare(request)  # MUST call before write()
    await resp.write(b"Hello ")
    await resp.write(b"World")
    await resp.write_eof()
    return resp
```

### Properties

| Property | Type | Description |
|---|---|---|
| `resp.status` | `int` | Status code |
| `resp.reason` | `str` | Reason phrase |
| `resp.headers` | `CIMultiDict` | Response headers |
| `resp.cookies` | `SimpleCookie` | Response cookies |
| `resp.prepared` | `bool` | Headers sent? |
| `resp.keep_alive` | `bool \| None` | Keep-alive |
| `resp.chunked` | `bool` | Chunked encoding |
| `resp.compression` | `bool` | Compression enabled |
| `resp.content_length` | `int \| None` | Content-Length |
| `resp.content_type` | `str` | Content-Type media type |
| `resp.charset` | `str \| None` | Character set |
| `resp.etag` | `ETag \| None` | ETag header |
| `resp.last_modified` | `datetime \| None` | Last-Modified header |

### Cookie handling

```python
resp.set_cookie(
    "session", "abc123",
    max_age=3600,
    path="/",
    secure=True,
    httponly=True,
    samesite="Lax",
    domain=".example.com",
)
resp.del_cookie("session")
```

### Compression

```python
resp.enable_compression()  # Auto-select based on Accept-Encoding
resp.enable_compression(force=web.ContentCoding.gzip)  # Force gzip
```

### Chunked encoding

```python
resp.enable_chunked_encoding()
```

### Connection control

```python
resp.force_close()  # Set Connection: close
```

---

## Response

Convenience class for simple responses with body.

```python
# Text response
return web.Response(text="Hello", content_type="text/html")

# Bytes response
return web.Response(body=b"binary", content_type="application/octet-stream")

# With status and headers
return web.Response(
    status=201,
    text="Created",
    headers={"Location": "/items/1"},
)
```

---

## json_response()

Quick JSON response helper:

```python
return web.json_response(
    {"key": "value"},
    status=200,
    headers={"X-Custom": "value"},
    dumps=json.dumps,           # custom encoder
    sort_keys=True,
    indent=2,
    separators=(",", ": "),
)
```

Also available: `web.json_bytes_response()` for bytes output.

---

## FileResponse

Serve static files efficiently (uses `sendfile` when available):

```python
return web.FileResponse(
    "/path/to/file.txt",
    chunk_size=256*1024,  # default 256KB
    status=200,
    headers={"X-Custom": "value"},
)
```

Features:
- Automatic MIME type detection via `mimetypes`
- Range request support (partial content)
- Conditional requests (If-Modified-Since, If-None-Match, If-Match)
- Pre-compressed file support (`.br`, `.gz`)
- Falls back to chunked reading when `sendfile` unavailable

Set `AIOHTTP_NOSENDFILE=1` to disable `sendfile`.

---

## run_app()

Convenience function for development:

```python
web.run_app(
    app,
    host="0.0.0.0",
    port=8080,
    ssl_context=ssl_context,           # SSL/TLS
    shutdown_timeout=60.0,             # Graceful shutdown timeout
    keepalive_timeout=75.0,            # Keep-alive timeout
    backlog=128,                       # Socket backlog
    access_log=access_logger,          # Access log
    access_log_format=...,             # Log format
    access_log_class=AccessLogger,     # Logger class
    handle_signals=True,               # Handle SIGTERM/SIGINT
    reuse_address=None,                # SO_REUSEADDR
    reuse_port=None,                   # SO_REUSEPORT
    handler_cancellation=False,        # Cancel handler on disconnect
)
```

Accepts `Application` or `Awaitable[Application]` (for async factory patterns).

---

## AppRunner / Sites

Low-level server control (production use):

```python
runner = web.AppRunner(app, access_log=logger)
await runner.setup()
site = web.TCPSite(runner, "0.0.0.0", 8080, ssl_context=ctx)
await site.start()

# Multiple sites
unix_site = web.UnixSite(runner, "/tmp/app.sock")
await unix_site.start()

# Graceful shutdown
await runner.cleanup()
```

Site types: `TCPSite`, `UnixSite`, `SockSite`, `NamedPipeSite`.

---

## HTTP Exceptions

Raise HTTP exceptions as responses:

```python
raise web.HTTPNotFound(text="Not found")
raise web.HTTPBadRequest(text="Bad request", headers={"Retry-After": "60"})
raise web.HTTPUnauthorized(text="Unauthorized")
raise web.HTTPForbidden()
raise web.HTTPTooManyRequests(text="Rate limited")
raise web.HTTPInternalServerError(text="Server error")
```

Full hierarchy: `HTTPException` → `HTTPSuccessful` (2xx), `HTTPRedirection` (3xx), `HTTPError` → `HTTPClientError` (4xx), `HTTPServerError` (5xx).

Exceptions are also `Response` objects — they can be returned directly:

```python
return web.HTTPCreated(text="Created", headers={"Location": "/items/1"})
```

---

## Application lifecycle signals

```python
async def on_startup(app: web.Application) -> None:
    app["db"] = await create_pool()

async def on_shutdown(app: web.Application) -> None:
    pass  # Stop accepting new connections

async def on_cleanup(app: web.Application) -> None:
    app["db"].close()
    await app["db"].wait_closed()

async def on_response_prepare(app: web.Application, request: web.Request, response: web.StreamResponse) -> None:
    response.headers["Server"] = "MyApp"

app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)
app.on_cleanup.append(on_cleanup)
app.on_response_prepare.append(on_response_prepare)
```

### Cleanup context manager

```python
@asynccontextmanager
async def db_ctx(app: web.Application):
    app["db"] = await create_pool()
    yield
    app["db"].close()
    await app["db"].wait_closed()

app.cleanup_ctx.append(db_ctx)
```

Registered via `app.cleanup_ctx.append()`. Context enters on startup, exits on cleanup.
