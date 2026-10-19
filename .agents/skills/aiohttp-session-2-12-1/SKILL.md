---
name: aiohttp-session-2-12-1
description: >
  aiohttp-session 2.12.1 — session management middleware for aiohttp.web. Use this skill whenever
  the user works with aiohttp web sessions, needs to store per-user data across requests, implements
  login/logout flows, flash messages, or session-based authentication in aiohttp. Supports multiple
  storage backends — encrypted cookies (Fernet/NaCl), Redis, Memcached, and plain cookies (testing
  only). Provides dict-like Session objects via get_session/new_session, with middleware-based
  automatic load/save. Use when the user mentions aiohttp sessions, session cookies, session fixation,
  or server-side session storage with aiohttp.
metadata:
  tags:
    - python
    - web
    - aiohttp
    - session
---

# aiohttp-session 2.12.1

## Overview

`aiohttp-session` is a session management library for `aiohttp.web` applications. It provides a dict-like `Session` object accessible from request handlers, with automatic persistence via middleware. The library supports multiple storage backends, ranging from simple unencrypted cookies to server-side Redis/Memcached stores.

### Architecture

The library works as an aiohttp middleware that wraps every request/response cycle:

1. On request — storage loads session data (from cookie, Redis, etc.) into a `Session` object
2. In handler — `await get_session(request)` returns the session (cached per request)
3. On response — middleware saves any changed session data back to storage

### Key Objects

- **`Session`** — dict-like (`MutableMapping[str, Any]`) object holding per-user data. Supports `session[key] = value`, `del session[key]`, `key in session`, plus `.new`, `.created`, `.empty`, `.invalidate()`, `.changed()`.
- **`AbstractStorage`** — base class for storage backends. Subclasses implement `load_session()` and `save_session()`.
- **`setup(app, storage)`** — registers session middleware on an `aiohttp.web.Application`.
- **`get_session(request)`** — async function to retrieve the current session from a request.
- **`new_session(request)`** — async function to create a fresh session, discarding any existing one (use during login to prevent session fixation).

### Storage Backends

| Storage | Module | Data Location | Security | Extra Install |
|---|---|---|---|---|
| `SimpleCookieStorage` | `aiohttp_session` | Cookie (plain JSON) | None — testing only | None |
| `EncryptedCookieStorage` | `aiohttp_session.cookie_storage` | Cookie (Fernet-encrypted) | AES encryption | `pip install aiohttp-session[secure]` |
| `NaClCookieStorage` | `aiohttp_session.nacl_storage` | Cookie (NaCl-encrypted) | XSalsa20-Poly1305 | `pip install aiohttp-session[pynacl]` |
| `RedisStorage` | `aiohttp_session.redis_storage` | Redis (cookie holds UUID key) | Server-side | `pip install aiohttp-session[aioredis]` |
| `MemcachedStorage` | `aiohttp_session.memcached_storage` | Memcached (cookie holds UUID key) | Server-side | `pip install aiohttp-session[aiomcache]` |

Cookie-based storages embed all data in the browser cookie. Redis/Memcached store data server-side and keep only a random key in the cookie.

## Usage

### Basic setup with encrypted cookies

```python
from cryptography import fernet
from aiohttp import web
from aiohttp_session import setup, get_session
from aiohttp_session.cookie_storage import EncryptedCookieStorage

async def handler(request: web.Request) -> web.Response:
    session = await get_session(request)
    session["counter"] = session.get("counter", 0) + 1
    return web.Response(text=f"Count: {session['counter']}")

def make_app() -> web.Application:
    app = web.Application()
    # Generate a 32-byte key (Fernet.generate_key produces a 32-byte URL-safe base64 key)
    fernet_key = fernet.Fernet.generate_key()
    setup(app, EncryptedCookieStorage(fernet_key))
    app.router.add_get("/", handler)
    return app

web.run_app(make_app())
```

### Login / logout pattern

```python
from aiohttp import web
from aiohttp_session import setup, get_session, new_session
from aiohttp_session.cookie_storage import EncryptedCookieStorage

def login_required(handler):
    async def wrapped(request: web.Request) -> web.StreamResponse:
        session = await get_session(request)
        if "user_id" not in session:
            raise web.HTTPFound(request.app.router["login"].url_for())
        return await handler(request)
    return wrapped

@login_required
async def dashboard(request: web.Request) -> web.Response:
    session = await get_session(request)
    return web.Response(text=f"Welcome, user {session['user_id']}")

async def login(request: web.Request) -> web.StreamResponse:
    form = await request.post()
    # Validate credentials...
    # Use new_session() to prevent session fixation attacks
    session = await new_session(request)
    session["user_id"] = form["username"]
    raise web.HTTPFound(request.app.router["dashboard"].url_for())

async def logout(request: web.Request) -> web.StreamResponse:
    session = await get_session(request)
    session.invalidate()  # Clear all session data and cookie
    raise web.HTTPFound(request.app.router["login_page"].url_for())
```

### Redis-backed sessions

```python
from typing import AsyncIterator
from aiohttp import web
from redis import asyncio as aioredis
from aiohttp_session import setup, get_session
from aiohttp_session.redis_storage import RedisStorage

async def redis_init(app: web.Application) -> AsyncIterator[None]:
    redis = await aioredis.from_url("redis://localhost:6379")  # type: ignore[no-untyped-call]
    setup(app, RedisStorage(redis))
    yield
    await redis.close()

def make_app() -> web.Application:
    app = web.Application()
    app.cleanup_ctx.append(redis_init)
    app.router.add_get("/", handler)
    return app
```

### Flash messages

Implement flash messages by layering a custom middleware on top of the session middleware:

```python
from aiohttp import web
from aiohttp.typedefs import Handler

def flash(request: web.Request, message: str) -> None:
    request.setdefault("flash_outgoing", []).append(message)

def get_messages(request: web.Request) -> list[str]:
    return request.pop("flash_incoming", [])

@web.middleware
async def flash_middleware(request: web.Request, handler: Handler) -> web.StreamResponse:
    session = await get_session(request)
    request["flash_incoming"] = session.pop("flash", [])
    try:
        return await handler(request)
    finally:
        session["flash"] = request.get("flash_incoming", []) + request.get("flash_outgoing", [])

# Register after session middleware
app.middlewares.append(flash_middleware)
```

### Session properties and methods

```python
session = await get_session(request)

session["key"] = "value"       # Set (auto-marks changed)
value = session["key"]         # Get
del session["key"]             # Delete (auto-marks changed)
"key" in session               # Contains check
len(session)                   # Item count
session.get("key", default)    # Safe get (MutableMapping)

session.new        # bool — True if this is a brand-new session
session.created    # int — UNIX timestamp of session creation
session.empty      # bool — True if session has no data
session.max_age    # int | None — session lifetime in seconds

session.changed()  # Call after mutating nested mutable values (lists, dicts)
session.invalidate()  # Clear all data and mark for cookie deletion
```

### Custom cookie name and parameters

```python
storage = EncryptedCookieStorage(
    fernet_key,
    cookie_name="MY_APP_SESSION",
    domain=".example.com",
    max_age=3600,         # 1 hour
    path="/",
    secure=True,          # HTTPS only
    httponly=True,        # No JS access
    samesite="lax",      # CSRF protection
)
```

## Gotchas

- **Always use `new_session()` during login** — `get_session()` reuses the existing session cookie, which enables session fixation attacks. `new_session()` creates a fresh session with a new identity, breaking the attacker's link.
- **Call `session.changed()` after mutating nested values** — Setting `session["key"] = value` auto-marks the session as changed. But mutating a value already in the session (e.g., `session["list"].append(item)`) does not. Call `session.changed()` explicitly after such mutations, or the change is silently lost.
- **Session data must be JSON-serializable** — All built-in storages use `json.dumps`/`json.loads` by default. Storing `datetime`, `set`, or custom objects will raise on serialization. Use custom `encoder`/`decoder` callables if needed.
- **`SimpleCookieStorage` is insecure** — It stores plain JSON in cookies with no encryption or signing. Users can read and forge session data. Use only in tests.
- **EncryptedCookieStorage accepts Fernet objects directly** — You can pass a `fernet.Fernet` instance or raw bytes/str. If passing raw bytes, they are base64-encoded internally. Key must be exactly 32 bytes (or a valid Fernet key).
- **Cookie size limits apply** — Cookie-based storages (Simple, Encrypted, NaCl) embed all data in the cookie. Browsers limit cookies to ~4KB. Large sessions will be silently rejected by the browser. Use Redis/Memcached for larger session data.
- **`max_age` vs session cookies** — `max_age=None` creates a session cookie (deleted on browser close). Setting `max_age` to seconds creates a persistent cookie. For `EncryptedCookieStorage`, `max_age` also serves as the Fernet token TTL.
- **Redis/Memcached store only a key in the cookie** — The session data lives server-side. If the backend is cleared or the key expires, the session is lost and a new one is created on next request.
- **`session.invalidate()` clears data and cookie** — It empties the session dict and marks it changed, causing the cookie to be deleted on response. Use for logout.
- **`response.prepared` blocks session save** — If a handler returns a pre-prepared response (headers already sent), the middleware cannot save session data and raises `RuntimeError`. Avoid calling `response.prepare()` before returning.
- **WebSocket responses skip session save** — The middleware detects non-`Response` types (like `WebSocketResponse`) and returns early without saving. Session changes in WebSocket handlers are not persisted.
- **`redis.asyncio.Redis` required, not `aioredis`** — `RedisStorage` expects `redis.asyncio.Redis` (from `redis>=4.3`). The old `aioredis` package is deprecated and no longer supported.
- **Custom `encoder`/`decoder` must be symmetric** — If you pass a custom serializer (e.g., `msgpack.dumps`), the decoder must be its inverse. Mismatch causes `ValueError` on load, which silently creates a new session.

## References

- [01-session-object](references/01-session-object.md) — Session class API, MutableMapping interface, identity, lifecycle
- [02-storage-backends](references/02-storage-backends.md) — All storage backends: SimpleCookie, EncryptedCookie, NaCl, Redis, Memcached
- [03-custom-storage](references/03-custom-storage.md) — Writing custom AbstractStorage implementations
- [04-cookie-configuration](references/04-cookie-configuration.md) — Cookie parameters, security flags, domain/path/samesite settings
