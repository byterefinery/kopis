# Cookie Configuration

## Parameters

All storage backends accept these cookie configuration parameters through `AbstractStorage`:

```python
storage = EncryptedCookieStorage(
    key,
    cookie_name="AIOHTTP_SESSION",
    domain=None,
    max_age=None,
    path="/",
    secure=None,
    httponly=True,
    samesite=None,
)
```

### `cookie_name` — `str` (default: `"AIOHTTP_SESSION"`)

Name of the HTTP cookie. Change this to avoid conflicts with other applications on the same domain or to namespace multiple session types.

```python
# Separate sessions for admin and user interfaces
setup(user_app, EncryptedCookieStorage(key, cookie_name="USER_SESSION"))
setup(admin_app, EncryptedCookieStorage(key, cookie_name="ADMIN_SESSION"))
```

For Redis/Memcached, this name is also used as the prefix for server-side keys: `AIOHTTP_SESSION_{uuid}`.

### `domain` — `str | None` (default: `None`)

Cookie domain. `None` means the cookie is sent only to the exact host that set it.

```python
# Cookie shared across subdomains
storage = EncryptedCookieStorage(key, domain=".example.com")
# Cookie for specific subdomain
storage = EncryptedCookieStorage(key, domain="api.example.com")
```

### `max_age` — `int | None` (default: `None`)

Session lifetime in seconds.

- `None` — session cookie (deleted when browser closes)
- `3600` — 1-hour persistent cookie
- `86400` — 24-hour persistent cookie

For `EncryptedCookieStorage`, `max_age` also acts as the Fernet token TTL. Tokens older than `max_age` are rejected during decryption, even if the cookie is still present.

```python
# 30-day sessions
storage = EncryptedCookieStorage(key, max_age=30 * 24 * 3600)

# Per-session max_age override
session = await get_session(request)
session.max_age = 1800  # 30 minutes for this session
```

### `path` — `str` (default: `"/"`)

Cookie path. The cookie is sent for all URLs under this path.

```python
# Only for /admin/* routes
storage = EncryptedCookieStorage(key, path="/admin")
```

### `secure` — `bool | None` (default: `None`)

When `True`, the cookie is only sent over HTTPS connections.

- `None` — same as `False` (cookie sent over both HTTP and HTTPS)
- `True` — cookie sent only over HTTPS

Always set `secure=True` in production with HTTPS. Without it, the cookie can be intercepted on unencrypted connections.

```python
storage = EncryptedCookieStorage(key, secure=True)
```

### `httponly` — `bool` (default: `True`)

When `True`, the cookie is inaccessible to JavaScript (`document.cookie`). This mitigates XSS-based cookie theft.

```python
# Default (recommended)
storage = EncryptedCookieStorage(key, httponly=True)

# Allow JS access (not recommended)
storage = EncryptedCookieStorage(key, httponly=False)
```

### `samesite` — `str | None` (default: `None`)

Controls whether the cookie is sent on cross-site requests. Values:

- `None` — no SameSite attribute (browser default, usually `Lax`)
- `"lax"` — sent on top-level GET navigation (default in most browsers)
- `"strict"` — never sent on cross-site requests
- `"none"` — always sent (requires `secure=True`)

```python
# CSRF protection — cookie not sent on cross-site POST
storage = EncryptedCookieStorage(key, samesite="strict")

# Allow top-level navigation but block cross-site POST
storage = EncryptedCookieStorage(key, samesite="lax")

# Cross-site iframe embedding (requires secure=True)
storage = EncryptedCookieStorage(key, samesite="none", secure=True)
```

### `encoder` / `decoder` — `Callable` (default: `json.dumps` / `json.loads`)

Custom serialization functions. Must be symmetric (decoder reverses encoder).

```python
import orjson

storage = EncryptedCookieStorage(
    key,
    encoder=orjson.dumps,
    decoder=orjson.loads,
)
```

## `cookie_params` Property

Access the resolved cookie parameters as a dict:

```python
storage = EncryptedCookieStorage(key, domain=".example.com", max_age=3600)
print(storage.cookie_params)
# {'domain': '.example.com', 'max_age': 3600, 'path': '/', 'secure': None, 'httponly': True, 'samesite': None}
```

## Security Checklist

For production deployments, configure:

```python
storage = EncryptedCookieStorage(
    key,
    secure=True,      # HTTPS only
    httponly=True,    # No JS access
    samesite="lax",   # CSRF protection
    max_age=3600,     # 1-hour sessions
)
```

For Redis/Memcached backends, the cookie only contains a random key, so cookie theft alone is not sufficient — the attacker also needs access to the backend. However, still use `secure=True` and `httponly=True` to reduce attack surface.

## Cookie Size Limits

Browser cookie size limits vary but are typically 4096 bytes (4KB) per cookie. Cookie-based storages (Simple, Encrypted, NaCl) embed all session data in the cookie:

- Empty session: ~100-200 bytes of overhead (encryption, encoding)
- Each session key adds to the cookie size
- Oversized cookies may be silently rejected by the browser

For sessions that might grow beyond a few KB, use Redis or Memcached storage where the cookie holds only a ~32-byte UUID key.
