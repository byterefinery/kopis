# Testing

## Table of Contents

- [TestClient](#testclient)
- [TestServer](#testserver)
- [RawTestServer](#rawtestserver)
- [pytest fixtures](#pytest-fixtures)
- [loop management](#loop-management)
- [Unused port](#unused-port)

---

## TestClient

Full-featured test client that runs against a real server:

```python
import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

async def handler(request: web.Request) -> web.Response:
    return web.json_response({"message": "hello"})

app = web.Application()
app.router.add_get("/", handler)

@pytest.mark.asyncio
async def test_index():
    async with TestClient(TestServer(app)) as client:
        resp = await client.get("/")
        assert resp.status == 200
        data = await resp.json()
        assert data == {"message": "hello"}
```

### TestClient methods

| Method | Description |
|---|---|
| `client.get(path, **kw)` | GET request |
| `client.post(path, data, **kw)` | POST request |
| `client.put(path, data, **kw)` | PUT request |
| `client.patch(path, data, **kw)` | PATCH request |
| `client.delete(path, **kw)` | DELETE request |
| `client.options(path, **kw)` | OPTIONS request |
| `client.head(path, **kw)` | HEAD request |
| `client.request(method, path, **kw)` | Arbitrary method |
| `client.ws_connect(path, **kw)` | WebSocket connection |

All methods accept the same parameters as `ClientSession` equivalents. Paths are relative — the client prepends the server URL.

### Properties

| Property | Type | Description |
|---|---|---|
| `client.server` | `BaseTestServer` | Underlying server |
| `client.app` | `Application \| None` | Application (if TestServer) |
| `client.session` | `ClientSession` | Internal session |
| `client.host` | `str` | Server host |
| `client.port` | `int` | Server port |

### make_url()

```python
url = client.make_url("/path?query=value")
# Returns absolute URL: http://127.0.0.1:PORT/path?query=value
```

---

## TestServer

Wraps an `Application` in a real server:

```python
from aiohttp.test_utils import TestServer, TestClient

server = TestServer(app, host="127.0.0.1", port=8080)
client = TestClient(server)

async with client:
    resp = await client.get("/")
```

### Constructor

```python
TestServer(
    app,
    scheme="",          # "http" or "https" (auto-detected)
    host="127.0.0.1",   # Bind address
    port=None,          # Port (0 = random)
)
```

---

## RawTestServer

For testing raw request handlers without an Application:

```python
from aiohttp.test_utils import RawTestServer, TestClient
from aiohttp.web_protocol import RequestHandler

async def handler(request: web.Request) -> web.StreamResponse:
    return web.Response(text="hello")

server = RawTestServer(handler)
client = TestClient(server)
```

---

## pytest fixtures

aiohttp provides pytest fixtures via its plugin:

```python
import pytest
import aiohttp
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

@pytest.fixture
def app():
    app = web.Application()
    app.router.add_get("/", handler)
    return app

@pytest.fixture
async def client(app):
    async with TestClient(TestServer(app)) as client:
        yield client

@pytest.mark.asyncio
async def test_handler(client):
    resp = await client.get("/")
    assert resp.status == 200
```

### Built-in fixtures

```python
# From pytest_plugin
@pytest.fixture
def aiohttp_client(loop):
    """Factory fixture — yields callable that creates TestClient."""
    ...

# Usage
@pytest.mark.asyncio
async def test_with_fixture(aiohttp_client, app):
    async with aiohttp_client(app) as client:
        resp = await client.get("/")
        assert resp.status == 200
```

### Loop options

```bash
pytest --aiohttp-loop pyloop    # Default: pure Python loop
pytest --aiohttp-loop uvloop    # Use uvloop
pytest --aiohttp-loop all       # Run with both
pytest --aiohttp-fast           # Skip extra checks
pytest --aiohttp-enable-loop-debug  # Enable debug mode
```

---

## loop management

For manual event loop control in tests:

```python
from aiohttp.test_utils import setup_test_loop, teardown_test_loop, loop_context

# Setup
loop = setup_test_loop(app)
try:
    # Run tests
    result = loop.run_until_complete(coro)
finally:
    teardown_test_loop(loop)
```

### loop_context

```python
from aiohttp.test_utils import loop_context

# Creates and yields a new event loop
with loop_context() as loop:
    result = loop.run_until_complete(coro)
```

---

## Unused port

```python
from aiohttp.test_utils import unused_port

port = unused_port()  # Returns an available port number
```
