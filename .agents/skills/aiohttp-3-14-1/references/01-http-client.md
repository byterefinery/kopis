# HTTP Client

## Table of Contents

- [ClientSession](#clientsession)
- [Request methods](#request-methods)
- [Request parameters](#request-parameters)
- [ClientResponse](#clientresponse)
- [Standalone request()](#standalone-request)
- [ClientTimeout](#clienttimeout)
- [ClientWSTimeout](#clientwstimeout)
- [Proxies](#proxies)
- [trust_env](#trust_env)

---

## ClientSession

`ClientSession` is the primary interface for making HTTP requests. It manages connection pooling, cookies, and default headers.

### Construction

```python
async with aiohttp.ClientSession(
    base_url="https://api.example.com/",    # prefix for relative URLs (must end with /)
    connector=TCPConnector(limit=100),       # custom connector
    cookies={"session": "abc123"},           # initial cookies
    headers={"X-API-Key": "secret"},         # default headers on every request
    trust_env=False,                         # read proxies/netrc from env
    raise_for_status=False,                  # auto-raise on 4xx/5xx
    auto_decompress=True,                    # auto-decompress gzip/deflate/br/zstd
    timeout=ClientTimeout(total=30, connect=10),
    cookie_jar=CookieJar(),                  # custom cookie jar
    middlewares=[my_middleware],             # client middlewares
    trace_configs=[TraceConfig()],           # tracing hooks
    json_serialize=json.dumps,               # custom JSON encoder
    requote_redirect_url=True,               # requote redirect URLs
    read_bufsize=2**18,                      # read buffer size (default 256KB)
    max_line_size=8190,                      # max header line length
    max_field_size=8190,                     # max header field size
    max_headers=128,                         # max number of headers
) as session:
    ...
```

### Key properties

| Property | Type | Description |
|---|---|---|
| `session.closed` | `bool` | True after `close()` |
| `session.connector` | `BaseConnector` | Underlying connector |
| `session.cookie_jar` | `AbstractCookieJar` | Session cookies |
| `session.headers` | `CIMultiDict[str]` | Default headers |
| `session.timeout` | `ClientTimeout` | Default timeout |
| `session.trust_env` | `bool` | Env proxy/netrc enabled |
| `session.auto_decompress` | `bool` | Auto decompression |
| `session.raise_for_status` | `bool` | Auto raise |

### Lifecycle

```python
session = aiohttp.ClientSession()
try:
    resp = await session.get("https://example.com")
finally:
    await session.close()  # or use `async with`
```

`session.detach()` releases the connector without closing it (e.g., for external lifecycle management).

---

## Request methods

All HTTP methods are available on `ClientSession`:

| Method | Signature |
|---|---|
| `get(url, **kw)` | GET request |
| `options(url, **kw)` | OPTIONS request |
| `head(url, **kw)` | HEAD request (no redirect by default) |
| `post(url, data=None, **kw)` | POST request |
| `put(url, data=None, **kw)` | PUT request |
| `patch(url, data=None, **kw)` | PATCH request |
| `delete(url, **kw)` | DELETE request |
| `request(method, url, **kw)` | Arbitrary HTTP method |

All return `_RequestContextManager` — usable as `async with` or `await`:

```python
# Context manager — auto-closes response
async with session.get("https://httpbin.org/get") as resp:
    body = await resp.read()

# Direct await — must manually release
resp = await session.get("https://httpbin.org/get")
body = await resp.read()
resp.release()  # return connection to pool
```

---

## Request parameters

Full parameter set for `session.request()` / `session.get()` etc.:

| Parameter | Type | Default | Description |
|---|---|---|---|
| `params` | `Query` | `{}` | URL query parameters (dict, list of tuples, or string) |
| `data` | `Any` | `None` | Request body (bytes, str, file, FormData, Payload) |
| `json` | `Any` | `None` | JSON-serialized body (mutually exclusive with `data`) |
| `cookies` | `LooseCookies` | `None` | Per-request cookies |
| `headers` | `LooseHeaders` | `None` | Per-request headers (merged with session defaults) |
| `skip_auto_headers` | `Iterable[str]` | `None` | Headers to skip auto-generation for |
| `allow_redirects` | `bool` | `True` | Follow redirects |
| `max_redirects` | `int` | `10` | Max redirect count |
| `compress` | `str \| bool` | `None` | Request body compression (`"gzip"`, `"deflate"`, or `True`) |
| `chunked` | `bool` | `None` | Chunked transfer encoding |
| `expect100` | `bool` | `False` | Send `Expect: 100-continue` |
| `raise_for_status` | `bool \| Callable` | `None` | Override session setting per request |
| `read_until_eof` | `bool` | `True` | Read full response body |
| `proxy` | `StrOrURL` | `None` | Proxy URL |
| `ssl` | `SSLContext \| bool \| Fingerprint` | `True` | SSL context, `False` to disable, or fingerprint |
| `server_hostname` | `str` | `None` | SNI hostname |
| `proxy_headers` | `LooseHeaders` | `None` | Extra headers sent to proxy |
| `timeout` | `ClientTimeout` | session default | Per-request timeout |
| `read_bufsize` | `int` | session default | Read buffer size |
| `auto_decompress` | `bool` | session default | Per-request decompression |
| `max_line_size` | `int` | session default | Max header line length |
| `max_field_size` | `int` | session default | Max header field size |
| `max_headers` | `int` | session default | Max header count |
| `trace_request_ctx` | `Any` | `None` | Context for tracing hooks |
| `middlewares` | `Sequence` | `None` | Per-request middleware override |

### Sending data

```python
# JSON body
await session.post(url, json={"key": "value"})

# Form data (url-encoded)
await session.post(url, data={"key": "value"})

# Multipart form
form = aiohttp.FormData()
form.add_field("text", "hello")
form.add_field("file", open("data.bin", "rb"), filename="data.bin")
await session.post(url, data=form)

# Raw bytes
await session.post(url, data=b"raw bytes", headers={"Content-Type": "application/octet-stream"})

# Streaming payload
async def generate():
    for i in range(100):
        yield f"chunk {i}\n"

await session.post(url, data=aiohttp.streamer(generate()))
```

### Sending JSON

```python
# Default: json.dumps
await session.post(url, json={"key": "value"})

# Custom encoder
await session.post(url, json=obj, headers={"Content-Type": "application/json"})
```

---

## ClientResponse

`ClientResponse` wraps the HTTP response.

### Properties

| Property | Type | Description |
|---|---|---|
| `resp.status` | `int` | HTTP status code |
| `resp.reason` | `str` | Reason phrase |
| `resp.headers` | `CIMultiDictProxy[str]` | Response headers |
| `resp.content` | `StreamReader` | Raw byte stream |
| `resp.content_length` | `int \| None` | Content-Length header value |
| `resp.history` | `tuple[ClientResponse, ...]` | Redirect history |
| `resp.cookies` | `SimpleCookie` | Response cookies |
| `resp.real_url` | `URL` | Final URL after redirects |
| `resp.url` | `URL` | Response URL |
| `resp.request_info` | `RequestInfo` | Request details (url, method, headers) |
| `resp.connection` | `Connection \| None` | Underlying connection |
| `resp.ok` | `bool` | True if status < 400 |
| `resp.links` | `dict` | Parsed Link header |

### Reading body

```python
# As bytes
body: bytes = await resp.read()

# As text (uses charset from Content-Type or default utf-8)
text: str = await resp.text()

# As JSON — raises ContentTypeError if Content-Type is not JSON
data = await resp.json(content_type="application/json")

# Streaming — iterate chunks
async for chunk in resp.content.iter_chunked(4096):
    process(chunk)

# Streaming — iterate lines
async for line in resp.content:
    process(line)

# Streaming — iterate any available data
async for slice in resp.content.iter_any():
    process(slice)
```

### Error handling

```python
# Explicit check
resp.raise_for_status()  # raises ClientResponseError for 4xx/5xx

# Per-request
async with session.get(url, raise_for_status=True) as resp:
    ...

# Session-wide
session = aiohttp.ClientSession(raise_for_status=True)

# Custom handler
async def custom_check(resp: aiohttp.ClientResponse) -> None:
    if resp.status == 429:
        await asyncio.sleep(1)
        raise aiohttp.ClientResponseError(...)

async with session.get(url, raise_for_status=custom_check) as resp:
    ...
```

### Connection management

```python
resp.release()   # Return connection to pool (don't read body)
resp.close()     # Close connection entirely

# Context manager auto-releases
async with session.get(url) as resp:
    data = await resp.json()
# Connection returned to pool here
```

---

## Standalone request()

One-off request without explicit session management:

```python
async with aiohttp.request("GET", "https://httpbin.org/get") as resp:
    body = await resp.read()
```

Creates a `ClientSession` internally with `TCPConnector(force_close=True)`. The session and connector are closed when the context manager exits.

---

## ClientTimeout

```python
timeout = aiohttp.ClientTimeout(
    total=30,           # Total request time (including redirects)
    connect=10,         # TCP connection timeout
    sock_read=5,        # Socket read timeout
    sock_connect=5,     # Socket connect timeout
    ceil_threshold=5,   # Max timeout granularity (prevents tiny timeouts)
)

session = aiohttp.ClientSession(timeout=timeout)
```

Default: `ClientTimeout(total=300, sock_connect=30)` (5-minute total).

Create per-request timeout via `attr.evolve()`:

```python
from attr import evolve

short_timeout = evolve(session.timeout, total=5)
resp = await session.get(url, timeout=short_timeout)
```

---

## ClientWSTimeout

```python
ws_timeout = aiohttp.ClientWSTimeout(
    ws_receive=None,   # Timeout per ws.receive() call (None = infinite)
    ws_close=10.0,     # Timeout for close handshake
)
```

Default: `ClientWSTimeout(ws_receive=None, ws_close=10.0)`.

---

## Proxies

```python
# Via parameter
async with session.get(url, proxy="http://proxy:8080") as resp:
    ...

# Via session default
session = aiohttp.ClientSession(proxy="http://proxy:8080")

# With proxy headers (use instead of deprecated proxy_auth)
await session.get(
    url,
    proxy="http://proxy:8080",
    proxy_headers={"Proxy-Authorization": aiohttp.encode_basic_auth("user", "pass")}
)
```

---

## trust_env

When `trust_env=True`, the session reads proxy settings from environment variables (`HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY`) and credentials from `~/.netrc`:

```python
session = aiohttp.ClientSession(trust_env=True)
```

This is equivalent to the `requests` library's `trust_env` behavior.
