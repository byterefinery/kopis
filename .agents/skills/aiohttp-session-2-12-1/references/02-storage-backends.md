# Storage Backends

## SimpleCookieStorage

**Module:** `aiohttp_session`
**Install:** `pip install aiohttp-session` (no extras)

Stores session data as plain JSON in the browser cookie. No encryption, no signing. Users can read and forge session data.

```python
from aiohttp_session import setup, SimpleCookieStorage

setup(app, SimpleCookieStorage())
```

**Use only in tests.** Never in production.

### Parameters

All parameters from `AbstractStorage` (cookie_name, domain, max_age, path, secure, httponly, samesite, encoder, decoder).

---

## EncryptedCookieStorage

**Module:** `aiohttp_session.cookie_storage`
**Install:** `pip install aiohttp-session[secure]`

Stores session data in the browser cookie, encrypted with Fernet (AES-128-CBC with HMAC-SHA256). Data is unreadable and unforgeable without the key.

```python
from cryptography import fernet
from aiohttp_session import setup
from aiohttp_session.cookie_storage import EncryptedCookieStorage

# Option 1: Pass a Fernet instance
f = fernet.Fernet(fernet.Fernet.generate_key())
setup(app, EncryptedCookieStorage(f))

# Option 2: Pass raw 32 bytes (auto base64-encoded)
import os
setup(app, EncryptedCookieStorage(os.urandom(32)))

# Option 3: Pass base64-encoded string
setup(app, EncryptedCookieStorage("gWRB1M+dPRc12lTNz2sN6PLzY9Q86K6R0eStz2OLYyY="))
```

### Key Management

- `fernet.Fernet.generate_key()` produces a 32-byte URL-safe base64-encoded key
- The key can be passed as `bytes`, `bytearray`, `str` (base64), or `fernet.Fernet` instance
- Rotate keys by keeping old keys in a key list and using a custom Fernet instance
- If decryption fails (e.g., key rotated), the storage logs a warning and creates a new session

### max_age as TTL

For `EncryptedCookieStorage`, `max_age` serves dual purpose:
1. Cookie lifetime (browser deletes after `max_age` seconds)
2. Fernet token TTL — `fernet.decrypt()` is called with `ttl=max_age`, so tokens older than `max_age` are rejected even if the cookie persists

```python
# 1-hour sessions
storage = EncryptedCookieStorage(key, max_age=3600)
```

### Parameters

- `secret_key` — `str`, `bytes`, `bytearray`, or `fernet.Fernet` (required)
- All `AbstractStorage` parameters

---

## NaClCookieStorage

**Module:** `aiohttp_session.nacl_storage`
**Install:** `pip install aiohttp-session[pynacl]`

Stores session data in the browser cookie, encrypted with NaCl's `SecretBox` (XSalsa20-Poly1305). Similar security model to `EncryptedCookieStorage` but uses a different cryptographic library.

```python
import nacl.utils
from aiohttp_session import setup
from aiohttp_session.nacl_storage import NaClCookieStorage

# Generate a 32-byte key
key = nacl.utils.random(32)
setup(app, NaClCookieStorage(key))
```

### Parameters

- `secret_key` — `bytes`, exactly 32 bytes (required)
- All `AbstractStorage` parameters

---

## RedisStorage

**Module:** `aiohttp_session.redis_storage`
**Install:** `pip install aiohttp-session[aioredis]`

Stores session data in Redis. The cookie contains only a random UUID key. Session data lives server-side.

```python
from typing import AsyncIterator
from aiohttp import web
from redis import asyncio as aioredis
from aiohttp_session import setup
from aiohttp_session.redis_storage import RedisStorage

async def redis_init(app: web.Application) -> AsyncIterator[None]:
    redis = await aioredis.from_url("redis://localhost:6379")  # type: ignore[no-untyped-call]
    setup(app, RedisStorage(redis))
    yield
    await redis.close()

app.cleanup_ctx.append(redis_init)
```

### Key Rotation

Each new session gets a random UUID key (from `key_factory`, default `uuid.uuid4().hex`). The key is stored in the cookie. On each save, the same key is reused (identity is preserved).

### Redis Key Format

Session data is stored as `AIOHTTP_SESSION_{uuid}` (cookie_name + "_" + key). Use this pattern for manual cleanup or inspection:

```bash
redis-cli keys "AIOHTTP_SESSION_*"
```

### max_age and Redis TTL

The `max_age` parameter sets both the cookie lifetime and the Redis key TTL (via `EX` option on `SET`). When `max_age` expires, both the cookie and Redis entry are gone.

### Parameters

- `redis_pool` — `redis.asyncio.Redis` instance (required)
- `key_factory` — callable returning a `str` key (default: `uuid.uuid4().hex`)
- All `AbstractStorage` parameters

### Notes

- Requires `redis>=4.3` with `redis.asyncio` support
- The old `aioredis` package is deprecated and not supported
- `redis.asyncio.Redis` must be passed, not a connection pool

---

## MemcachedStorage

**Module:** `aiohttp_session.memcached_storage`
**Install:** `pip install aiohttp-session[aiomcache]`

Stores session data in Memcached. The cookie contains only a random UUID key.

```python
import aiomcache
from aiohttp_session import setup
from aiohttp_session.memcached_storage import MemcachedStorage

mc = aiomcache.Client("127.0.0.1", 11211)
setup(app, MemcachedStorage(mc))
```

### Expiration Handling

Memcached has a 30-day limit on expiration times. The storage handles this:
- `max_age=None` → expire = 0 (never expire, until evicted)
- `max_age <= 30 days` → expire = max_age (seconds)
- `max_age > 30 days` → expire = unix timestamp

### Parameters

- `memcached_conn` — `aiomcache.Client` instance (required)
- `key_factory` — callable returning a `str` key (default: `uuid.uuid4().hex`)
- All `AbstractStorage` parameters

---

## Comparison

| Feature | SimpleCookie | EncryptedCookie | NaClCookie | Redis | Memcached |
|---|---|---|---|---|---|
| Data in cookie | Full (plain) | Full (encrypted) | Full (encrypted) | Key only | Key only |
| Encryption | None | Fernet (AES) | NaCl (XSalsa20) | Server-side | Server-side |
| Cookie size limit | ~4KB | ~4KB | ~4KB | ~50 bytes | ~50 bytes |
| Server dependency | None | None | None | Redis | Memcached |
| Instant invalidation | No | No | No | Yes (delete key) | Yes (delete key) |
| Key rotation | N/A | Yes (Fernet) | No | Yes (new UUID) | Yes (new UUID) |
| Extra install | None | `[secure]` | `[pynacl]` | `[aioredis]` | `[aiomcache]` |

Choose cookie-based for stateless deployments (no server dependency). Choose Redis/Memcached for large sessions, instant invalidation, or sensitive data that should never leave the server.
