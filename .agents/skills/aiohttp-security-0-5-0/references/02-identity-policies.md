# Identity Policies

Deep dive into the three built-in identity policy implementations.

## SessionIdentityPolicy

Uses `aiohttp-session` to store the identity in a server-side or encrypted cookie session.

### Construction

```python
from aiohttp_security import SessionIdentityPolicy

policy = SessionIdentityPolicy(session_key="AIOHTTP_SECURITY")
```

| Parameter | Default | Description |
|---|---|---|
| `session_key` | `"AIOHTTP_SECURITY"` | Key used inside the session dict |

Raises `ImportError` at construction if `aiohttp-session` is not installed.

### Setup Order

`aiohttp-session` must be configured before creating the policy:

```python
from aiohttp_session import setup as setup_session, EncryptedCookieStorage

secret_key = b"32-bytes-url-safe-base64-encoded-secret-key!!"
setup_session(app, EncryptedCookieStorage(secret_key, cookie_name="API_SESSION"))

from aiohttp_security import SessionIdentityPolicy
policy = SessionIdentityPolicy()
```

### Storage Backends

| Backend | Security | Use case |
|---|---|---|
| `EncryptedCookieStorage` | Encrypted (Fernet) | Default choice; no external deps |
| `RedisStorage` | Server-side | Large sessions, shared state |
| `SimpleCookieStorage` | **None** | Demos only |

### Behavior

- **`identify`** — reads `session[session_key]`, returns `None` if absent
- **`remember`** — writes `session[session_key] = identity`
- **`forget`** — pops `session[session_key]` (no-op if absent)

## CookiesIdentityPolicy

Stores the identity directly in an HTTP cookie. **For demonstration only** — the identity is visible and modifiable by the client.

### Construction

```python
from aiohttp_security import CookiesIdentityPolicy

policy = CookiesIdentityPolicy()
```

No constructor parameters. Uses hardcoded cookie name `AIOHTTP_SECURITY` and default max-age of 30 days.

### `remember` kwargs

| Parameter | Default | Description |
|---|---|---|
| `max_age` | 2,592,000 (30 days) | Cookie lifetime in seconds |
| `**kwargs` | — | Passed to `response.set_cookie()` (e.g., `path`, `domain`, `secure`, `httponly`) |

### Behavior

- **`identify`** — reads `request.cookies.get("AIOHTTP_SECURITY")`
- **`remember`** — calls `response.set_cookie("AIOHTTP_SECURITY", identity, max_age=max_age, **kwargs)`
- **`forget`** — calls `response.del_cookie("AIOHTTP_SECURITY")`

## JWTIdentityPolicy

Validates JSON Web Tokens from the `Authorization: Bearer <token>` header. Stateless — no server-side storage needed.

### Construction

```python
from aiohttp_security import JWTIdentityPolicy

policy = JWTIdentityPolicy(
    secret="my-jwt-secret",
    algorithm="HS256",
    key="sub",
)
```

| Parameter | Default | Description |
|---|---|---|
| `secret` | *(required)* | Signing secret for JWT verification |
| `algorithm` | `"HS256"` | JWT algorithm (passed to `jwt.decode`) |
| `key` | `"login"` | Claim name extracted as the identity |

Raises `RuntimeError` if `PyJWT` is not installed.

### Behavior

- **`identify`** — reads `Authorization` header, expects `Bearer <token>` prefix, decodes token via `jwt.decode(token, secret, algorithms=[algorithm])`, returns the value of the `key` claim
- **`remember`** — no-op (JWT is stateless; client holds the token)
- **`forget`** — no-op (JWT is stateless)

### Error Handling

If the `Authorization` header is present but does not start with `Bearer `, a `ValueError` is raised with message `"Invalid authorization scheme. Should be 'Bearer <token>'"`. Handle this in middleware or a global exception handler.

### Issuing Tokens

`aiohttp-security` does not issue JWTs — that is the application's responsibility:

```python
import jwt

token = jwt.encode(
    {"sub": user.id, "exp": datetime.utcnow() + timedelta(hours=1)},
    "my-jwt-secret",
    algorithm="HS256",
)
```

The token is returned to the client (e.g., in a JSON response), and the client includes it in subsequent `Authorization: Bearer <token>` headers.

## Custom Identity Policy

Implement `AbstractIdentityPolicy` for non-standard storage:

```python
from abc import abstractmethod
from aiohttp import web
from aiohttp_security.abc import AbstractIdentityPolicy

class HeaderIdentityPolicy(AbstractIdentityPolicy):
    """Extract identity from a custom X-User header (e.g., behind a proxy)."""

    async def identify(self, request: web.Request) -> Optional[str]:
        return request.headers.get("X-User")

    async def remember(self, request, response, identity, **kwargs):
        pass  # proxy handles auth

    async def forget(self, request, response):
        pass  # proxy handles auth
```
