# Middlewares and Tracing

## Table of Contents

- [Server middlewares](#server-middlewares)
- [Client middlewares](#client-middlewares)
- [normalize_path_middleware](#normalize_path_middleware)
- [DigestAuthMiddleware](#digestauthmiddleware)
- [TraceConfig](#traceconfig)
- [Trace signals](#trace-signals)

---

## Server middlewares

Middlewares wrap request handlers. They receive `(request, handler)` and return a `StreamResponse`.

### Defining a middleware

```python
from aiohttp import web

@web.middleware
async def timing_middleware(request: web.Request, handler) -> web.StreamResponse:
    import time
    start = time.monotonic()
    response = await handler(request)
    elapsed = time.monotonic() - start
    response.headers["X-Response-Time"] = f"{elapsed:.3f}"
    return response
```

The `@web.middleware` decorator marks the function as v1 middleware (receives `handler` parameter). Without it, the function is treated as legacy middleware.

### Registering

```python
app = web.Application(middlewares=[timing_middleware, auth_middleware])
```

Middlewares execute in **reverse order** — the first middleware in the list wraps all others.

### Middleware pattern

```python
@web.middleware
async def auth_middleware(request: web.Request, handler) -> web.StreamResponse:
    token = request.headers.get("Authorization")
    if not token:
        return web.json_response({"error": "Unauthorized"}, status=401)

    user = await validate_token(token)
    if not user:
        return web.json_response({"error": "Invalid token"}, status=401)

    # Store in request state
    request["user"] = user
    return await handler(request)
```

### Accessing app state in middleware

```python
@web.middleware
async def logging_middleware(request: web.Request, handler) -> web.StreamResponse:
    logger = request.app["logger"]
    logger.info(f"{request.method} {request.path}")
    return await handler(request)
```

---

## Client middlewares

Client middlewares intercept outgoing requests. Signature: `(request: ClientRequest, handler: ClientHandlerType) -> ClientResponse`.

```python
from aiohttp import ClientMiddlewareType, ClientRequest, ClientResponse, ClientHandlerType

async def retry_middleware(
    request: ClientRequest, handler: ClientHandlerType
) -> ClientResponse:
    for attempt in range(3):
        try:
            return await handler(request)
        except aiohttp.ServerDisconnectedError:
            if attempt < 2:
                continue
            raise

session = aiohttp.ClientSession(middlewares=[retry_middleware])
```

### Per-request middleware override

```python
resp = await session.get(url, middlewares=[custom_middleware])
```

---

## normalize_path_middleware

Built-in middleware for path normalization:

```python
from aiohttp.web import normalize_path_middleware

app = web.Application(middlewares=[
    normalize_path_middleware(
        append_slash=True,     # Redirect /items to /items/
        remove_slash=False,    # Mutually exclusive with append_slash
        merge_slashes=True,    # Merge // into /
        redirect_class=web.HTTPPermanentRedirect,  # 301
    )
])
```

Only one of `append_slash` and `remove_slash` can be `True`.

---

## DigestAuthMiddleware

Built-in client middleware for HTTP Digest Authentication (RFC 7616):

```python
from aiohttp import DigestAuthMiddleware

middleware = DigestAuthMiddleware(
    username="user",
    password="pass",
)

session = aiohttp.ClientSession(middlewares=[middleware])
```

Supports algorithms: MD5, MD5-SESS, SHA, SHA-SESS, SHA256, SHA256-SESS, SHA512, SHA512-SESS, and their RFC 7616 equivalents.

---

## TraceConfig

Client-side request tracing via signal hooks:

```python
from aiohttp import TraceConfig, ClientSession

trace_config = TraceConfig()

@trace_config.on_request_start.connect
async def on_request_start(session, trace_ctx, params):
    print(f"Request started: {params.method} {params.url}")

@trace_config.on_request_end.connect
async def on_request_end(session, trace_ctx, params):
    print(f"Request ended: {params.response.status}")

@trace_config.on_request_exception.connect
async def on_request_exception(session, trace_ctx, params):
    print(f"Request failed: {params.exception}")

session = ClientSession(trace_configs=[trace_config])
```

### Custom trace context

```python
from types import SimpleNamespace

class MyTraceContext(SimpleNamespace):
    def __init__(self, trace_request_ctx=None):
        super().__init__(trace_request_ctx=trace_request_ctx)
        self.start_time = None

trace_config = TraceConfig(trace_config_ctx_factory=MyTraceContext)
```

---

## Trace signals

All trace signals receive `(session: ClientSession, trace_config_ctx, params)`:

| Signal | Params class | When fired |
|---|---|---|
| `on_request_start` | `TraceRequestStartParams` | Before request sent |
| `on_request_headers_sent` | `TraceRequestHeadersSentParams` | After headers written |
| `on_request_chunk_sent` | `TraceRequestChunkSentParams` | After request chunk sent |
| `on_response_chunk_received` | `TraceResponseChunkReceivedParams` | After response chunk |
| `on_request_end` | `TraceRequestEndParams` | After response complete |
| `on_request_exception` | `TraceRequestExceptionParams` | On request error |
| `on_request_redirect` | `TraceRequestRedirectParams` | On redirect |
| `on_connection_queued_start` | `TraceConnectionQueuedStartParams` | When queuing for connection |
| `on_connection_queued_end` | `TraceConnectionQueuedEndParams` | When connection acquired |
| `on_connection_create_start` | `TraceConnectionCreateStartParams` | When creating new connection |
| `on_connection_create_end` | `TraceConnectionCreateEndParams` | After connection created |
| `on_connection_reuseconn` | `TraceConnectionReuseconnParams` | When reusing connection |
| `on_dns_resolvehost_start` | `TraceDnsResolveHostStartParams` | DNS resolution started |
| `on_dns_resolvehost_end` | `TraceDnsResolveHostEndParams` | DNS resolution done |
| `on_dns_cache_hit` | `TraceDnsCacheHitParams` | DNS cache hit |
| `on_dns_cache_miss` | `TraceDnsCacheMissParams` | DNS cache miss |

### Param fields

```python
# TraceRequestStartParams
params.method   # str — HTTP method
params.url      # URL — request URL
params.headers  # CIMultiDict — request headers

# TraceRequestEndParams
params.method   # str
params.url      # URL
params.headers  # CIMultiDict
params.response # ClientResponse

# TraceRequestExceptionParams
params.method   # str
params.url      # URL
params.headers  # CIMultiDict
params.exception # BaseException

# TraceRequestRedirectParams
params.method   # str
params.url      # URL
params.headers  # CIMultiDict
params.redirect_url # URL — redirect target
params.headers  # CIMultiDict — response headers
```
