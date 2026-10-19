# Advanced Topics

## Table of Contents

- [StreamReader](#streamreader)
- [CookieJar](#cookiejar)
- [hdrs module](#hdrs-module)
- [Compression](#compression)
- [Gunicorn workers](#gunicorn-workers)
- [BasicAuth and encode_basic_auth](#basicauth-and-encode_basic_auth)
- [ETag](#etag)
- [ChainMapProxy](#chainmapproxy)
- [set_zlib_backend](#set_zlib_backend)
- [AppKey](#appkey)

---

## StreamReader

`StreamReader` provides async iteration over byte streams:

```python
# On ClientResponse
async for chunk in resp.content.iter_chunked(4096):
    process(chunk)

async for line in resp.content:
    process(line)  # Each line includes \n

async for slice in resp.content.iter_any():
    process(slice)  # Whatever data is available
```

```python
# On Request (server)
async for chunk in request.content.iter_chunked(4096):
    process(chunk)
```

### Methods

| Method | Description |
|---|---|
| `await reader.read(n)` | Read up to n bytes |
| `await reader.readany()` | Read available data |
| `await reader.readexactly(n)` | Read exactly n bytes |
| `await reader.readline()` | Read until \n |
| `await reader.readchunk()` | Read next chunk (tuple of bytes, is_eof) |
| `reader.at_eof()` | Check if stream ended |
| `await reader.wait_eof()` | Wait for EOF |

### Properties

| Property | Type | Description |
|---|---|---|
| `reader.total_bytes` | `int` | Total bytes read |
| `reader.total_compressed_bytes` | `int \| None` | Compressed bytes read |

---

## CookieJar

```python
from aiohttp import CookieJar, DummyCookieJar

# Standard cookie jar (RFC-compliant)
jar = CookieJar(unsafe=False, quote_cookie=True)

# Accept all cookies (useful for testing)
jar = CookieJar(unsafe=True)

# No cookie processing at all
jar = DummyCookieJar()

# Use with session
session = aiohttp.ClientSession(cookie_jar=jar)
```

### Manual cookie management

```python
jar.update_cookies({"session": "abc"})
cookies = jar.filter_cookies(url)
```

---

## hdrs module

HTTP header constants:

```python
from aiohttp import hdrs

hdrs.ACCEPT           # "Accept"
hdrs.CONTENT_TYPE     # "Content-Type"
hdrs.CONTENT_LENGTH   # "Content-Length"
hdrs.AUTHORIZATION    # "Authorization"
hdrs.COOKIE           # "Cookie"
hdrs.SET_COOKIE       # "Set-Cookie"
hdrs.USER_AGENT       # "User-Agent"
hdrs.HOST             # "Host"
hdrs.CONNECTION       # "Connection"
hdrs.UPGRADE          # "Upgrade"
hdrs.TRANSFER_ENCODING # "Transfer-Encoding"

# HTTP methods
hdrs.METH_GET         # "GET"
hdrs.METH_POST        # "POST"
hdrs.METH_PUT         # "PUT"
hdrs.METH_DELETE      # "DELETE"
hdrs.METH_PATCH       # "PATCH"
hdrs.METH_HEAD        # "HEAD"
hdrs.METH_OPTIONS     # "OPTIONS"
hdrs.METH_ALL         # Set of all methods
```

---

## Compression

### Server response compression

```python
resp = web.StreamResponse()
resp.enable_compression()  # Auto-negotiate (gzip, deflate, br)
resp.enable_compression(force=web.ContentCoding.gzip)  # Force gzip
await resp.prepare(request)
await resp.write(b"compressed data")
await resp.write_eof()
```

### Client auto-decompression

```python
session = aiohttp.ClientSession(auto_decompress=True)  # Default
```

### zlib backend

```python
# Switch zlib implementation
aiohttp.set_zlib_backend("python")   # Pure Python
aiohttp.set_zlib_backend("builtin")  # C extension (default if available)
```

Supported backends depend on available libraries. Brotli (`br`) and zstd are auto-detected.

---

## Gunicorn workers

aiohttp provides Gunicorn workers for production deployment:

```python
from aiohttp.web import Application
from aiohttp.worker import GunicornWebWorker, GunicornUVLoopWebWorker

# In gunicorn config
# worker_class = "aiohttp.GunicornWebWorker"
# worker_class = "aiohttp.GunicornUVLoopWebWorker"  # With uvloop
```

```bash
gunicorn app:create_app \
    -k aiohttp.GunicornWebWorker \
    -w 4 \
    --bind 0.0.0.0:8080
```

`GunicornUVLoopWebWorker` requires `uvloop` installed.

---

## BasicAuth and encode_basic_auth

### encode_basic_auth (recommended)

```python
import aiohttp

auth_header = aiohttp.encode_basic_auth("username", "password")
# Returns: "Basic dXNlcm5hbWU6cGFzc3dvcmQ="

async with session.get(url, headers={"Authorization": auth_header}) as resp:
    ...
```

### BasicAuth (deprecated)

```python
# Deprecated — use encode_basic_auth instead
auth = aiohttp.BasicAuth("username", "password")
auth.encode()  # "Basic ..."
```

### Decoding

```python
auth = aiohttp.BasicAuth.decode("Basic dXNlcm5hbWU6cGFzc3dvcmQ=")
print(auth.login, auth.password)
```

---

## ETag

```python
from aiohttp import ETag

# Weak ETag
etag = ETag(value="abc123", is_weak=True)

# Strong ETag
etag = ETag(value="abc123", is_weak=False)

# Use with response
resp.etag = etag
resp.etag = "abc123"  # String form (strong)
resp.etag = None  # Remove

# Special wildcard
resp.etag = "*"  # ETag wildcard
```

---

## ChainMapProxy

Immutable view over multiple mappings:

```python
from aiohttp import ChainMapProxy

proxy = ChainMapProxy(dict1, dict2)
# Reads from dict1 first, falls back to dict2
```

Used internally for request/app state lookups.

---

## set_zlib_backend

Configure the zlib compression backend at module level:

```python
import aiohttp

# Must be called before creating any sessions/responses
aiohttp.set_zlib_backend("python")   # Pure Python zlib
aiohttp.set_zlib_backend("builtin")  # C extension (default)
```

Available backends depend on compiled extensions.

---

## AppKey

Typed keys for Application and Request state:

```python
from aiohttp import web

# Define typed key
DB_KEY = web.AppKey[str, "database_connection"]
CACHE_KEY = web.AppKey[dict, "cache"]

async def init(app: web.Application) -> None:
    app[DB_KEY] = "postgresql://..."

async def handler(request: web.Request) -> web.Response:
    db_url: str = request.app[DB_KEY]  # Type-checked
```

Using string keys directly works but triggers `NotAppKeyWarning` in strict mode. `AppKey` provides type safety via generics.
