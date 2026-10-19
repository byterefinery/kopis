# Exceptions

## Table of Contents

- [Client exception hierarchy](#client-exception-hierarchy)
- [Client exceptions](#client-exceptions)
- [HTTPException (server)](#httpexception-server)
- [Error handling patterns](#error-handling-patterns)

---

## Client exception hierarchy

```
Exception
└── ClientError                    # Base for all client errors
    ├── ClientResponseError        # Errors with HTTP response
    │   ├── ContentTypeError       # Called resp.json() on non-JSON
    │   ├── WSServerHandshakeError # WebSocket handshake failed
    │   ├── ClientHttpProxyError   # Proxy returned error
    │   └── TooManyRedirects       # Exceeded max_redirects
    ├── ClientConnectionError      # Socket-level errors
    │   ├── ClientConnectionResetError  # Connection reset
    │   └── ClientOSError          # OS-level errors
    │       └── ClientConnectorError     # Connection failed
    │           ├── ServerConnectionError
    │           ├── UnixClientConnectorError
    │           ├── ClientProxyConnectionError
    │           ├── ClientConnectorDNSError
    │           ├── ClientConnectorSSLError
    │           │   └── ClientConnectorCertificateError
    │           └── ServerFingerprintMismatch
    ├── ClientSSLError             # SSL/TLS errors
    ├── ConnectionTimeoutError     # Connection timed out
    ├── SocketTimeoutError         # Socket read/write timed out
    ├── ServerTimeoutError         # Server timeout
    ├── ServerDisconnectedError    # Server closed connection
    ├── ClientPayloadError         # Payload errors
    ├── InvalidURL                 # Invalid URL
    ├── InvalidUrlClientError      # Invalid URL (client)
    ├── NonHttpUrlClientError      # Non-HTTP URL
    ├── InvalidUrlRedirectClientError  # Invalid redirect URL
    ├── NonHttpUrlRedirectClientError  # Non-HTTP redirect
    ├── RedirectClientError        # Redirect base
    └── WSMessageTypeError         # Wrong WS message type
```

---

## Client exceptions

### ClientResponseError

Raised by `resp.raise_for_status()` on 4xx/5xx:

```python
try:
    async with session.get(url) as resp:
        resp.raise_for_status()
except aiohttp.ClientResponseError as exc:
    print(exc.status)        # HTTP status code
    print(exc.message)       # Error message
    print(exc.headers)       # Response headers
    print(exc.history)       # Redirect history
    print(exc.request_info)  # Request details
```

### ConnectionTimeoutError

```python
try:
    resp = await session.get(url, timeout=aiohttp.ClientTimeout(total=5))
except aiohttp.ConnectionTimeoutError:
    print("Connection timed out")
```

### ServerDisconnectedError

```python
try:
    async with session.get(url) as resp:
        data = await resp.read()
except aiohttp.ServerDisconnectedError:
    print("Server closed the connection")
```

### ContentTypeError

```python
try:
    data = await resp.json()
except aiohttp.ContentTypeError:
    # Content-Type is not JSON — use resp.text() + json.loads()
    text = await resp.text()
    data = json.loads(text)
```

### TooManyRedirects

```python
try:
    resp = await session.get(url, max_redirects=5)
except aiohttp.TooManyRedirects as exc:
    print(f"Too many redirects: {len(exc.history)}")
    for prev_resp in exc.history:
        print(prev_resp.url, prev_resp.status)
```

---

## HTTPException (server)

Server-side HTTP exceptions double as responses. Raise them in handlers:

```python
from aiohttp import web

# 4xx errors
raise web.HTTPBadRequest(text="Bad request")
raise web.HTTPUnauthorized(text="Unauthorized")
raise web.HTTPForbidden(text="Forbidden")
raise web.HTTPNotFound(text="Not found")
raise web.HTTPMethodNotAllowed(method="GET")
raise web.HTTPTooManyRequests(text="Rate limited")

# 3xx redirects
raise web.HTTPFound(location="/new-path")
raise web.HTTPMovedPermanently(location="/new-path")

# 5xx errors
raise web.HTTPInternalServerError(text="Internal error")
raise web.HTTPBadGateway(text="Bad gateway")
raise web.HTTPServiceUnavailable(text="Service unavailable")
```

### Full list by category

**2xx Successful:** `HTTPOk` (200), `HTTPCreated` (201), `HTTPAccepted` (202), `HTTPNonAuthoritativeInformation` (203), `HTTPNoContent` (204), `HTTPResetContent` (205), `HTTPPartialContent` (206)

**3xx Redirection:** `HTTPMultipleChoices` (300), `HTTPMovedPermanently` (301), `HTTPFound` (302), `HTTPSeeOther` (303), `HTTPNotModified` (304), `HTTPTemporaryRedirect` (307), `HTTPPermanentRedirect` (308)

**4xx Client Error:** `HTTPBadRequest` (400), `HTTPUnauthorized` (401), `HTTPPaymentRequired` (402), `HTTPForbidden` (403), `HTTPNotFound` (404), `HTTPMethodNotAllowed` (405), `HTTPNotAcceptable` (406), `HTTPProxyAuthenticationRequired` (407), `HTTPRequestTimeout` (408), `HTTPConflict` (409), `HTTPGone` (410), `HTTPLengthRequired` (411), `HTTPPreconditionFailed` (412), `HTTPRequestEntityTooLarge` (413), `HTTPRequestURITooLong` (414), `HTTPUnsupportedMediaType` (415), `HTTPRequestRangeNotSatisfiable` (416), `HTTPExpectationFailed` (417), `HTTPUnprocessableEntity` (422), `HTTPTooManyRequests` (429), `HTTPRequestHeaderFieldsTooLarge` (431)

**5xx Server Error:** `HTTPInternalServerError` (500), `HTTPNotImplemented` (501), `HTTPBadGateway` (502), `HTTPServiceUnavailable` (503), `HTTPGatewayTimeout` (504), `HTTPVersionNotSupported` (505), `HTTPVariantAlsoNegotiates` (506), `HTTPInsufficientStorage` (507), `HTTPNotExtended` (510), `HTTPNetworkAuthenticationRequired` (511)

### Using as response

```python
# Return directly (not raise)
return web.HTTPCreated(text="Created", headers={"Location": "/items/1"})
return web.HTTPNoContent()
```

### Custom body/text

```python
raise web.HTTPNotFound(
    text="Resource not found",
    content_type="text/plain",
    headers={"X-Error": "not_found"},
)
```

---

## Error handling patterns

### Client retry

```python
import asyncio

async def fetch_with_retry(session, url, max_retries=3):
    for attempt in range(max_retries):
        try:
            async with session.get(url) as resp:
                resp.raise_for_status()
                return await resp.json()
        except (aiohttp.ServerDisconnectedError, aiohttp.ServerTimeoutError):
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                continue
            raise
        except aiohttp.ClientResponseError as exc:
            if exc.status == 429:
                retry_after = int(exc.headers.get("Retry-After", 5))
                await asyncio.sleep(retry_after)
                continue
            raise
```

### Server error handler

```python
@web.middleware
async def error_middleware(request: web.Request, handler) -> web.StreamResponse:
    try:
        return await handler(request)
    except web.HTTPException:
        raise  # Let aiohttp handle HTTP exceptions
    except ValueError as exc:
        return web.json_response(
            {"error": "Bad request", "detail": str(exc)},
            status=400,
        )
    except Exception as exc:
        request.logger.exception("Unhandled error")
        return web.json_response(
            {"error": "Internal server error"},
            status=500,
        )
```
