---
name: aiohttp-security-0-5-0
description: >-
  Identity and authorization for aiohttp.web (v0.5.0). Covers identity policies
  (Cookies, Session, JWT), custom authorization policies, and the public API
  (setup, remember, forget, authorized_userid, permits, check_authorized,
  check_permission, is_anonymous). Use when building authentication or
  permission-gated endpoints with aiohttp.
---

# aiohttp-security 0.5.0

## Overview

`aiohttp-security` separates **authentication** (who the user is) from **authorization** (what they can do) via two pluggable policy interfaces:

- **`AbstractIdentityPolicy`** — stores, retrieves, and removes a session-wide identity string (cookie, session, or JWT). Three built-in implementations ship with the library.
- **`AbstractAuthorizationPolicy`** — maps an identity to a stable user ID and checks permissions. Always custom per application.

The public API is agnostic to policy implementations — handlers call `remember`, `forget`, `check_permission`, etc., never policy methods directly.

## Usage

### Setup

Register both policies on the `aiohttp.web.Application`:

```python
from aiohttp import web
from aiohttp_security import setup, SessionIdentityPolicy
from aiohttp_security.abc import AbstractAuthorizationPolicy

app = web.Application()
setup(app, SessionIdentityPolicy(), MyAuthorizationPolicy())
```

### Login / Logout Handlers

```python
from aiohttp_security import remember, forget

async def login(request: web.Request):
    form = await request.post()
    if verify_credentials(form["username"], form["password"]):
        response = web.HTTPFound("/")
        await remember(request, response, form["username"])
        raise response
    raise web.HTTPUnauthorized()

async def logout(request: web.Request):
    response = web.Response(text="Logged out")
    await forget(request, response)
    return response
```

### Protecting Endpoints

```python
from aiohttp_security import check_authorized, check_permission, authorized_userid, is_anonymous

async def public_page(request: web.Request):
    anon = await is_anonymous(request)
    return web.Response(text=f"Anonymous: {anon}")

async def logged_in_page(request: web.Request):
    userid = await check_authorized(request)  # raises HTTPUnauthorized if anonymous
    return web.Response(text=f"Hello {userid}")

async def admin_page(request: web.Request):
    await check_permission(request, "admin")  # raises HTTPUnauthorized or HTTPForbidden
    return web.Response(text="Admin area")
```

`check_permission` also accepts `enum.Enum` permissions and an optional `context` object.

### Building an Authorization Policy

Always implement `AbstractAuthorizationPolicy`. The identity policy is usually one of the built-ins.

```python
from enum import Enum
from typing import Any, Optional, Union
from aiohttp_security.abc import AbstractAuthorizationPolicy

class MyAuthPolicy(AbstractAuthorizationPolicy):

    async def authorized_userid(self, identity: str) -> Optional[str]:
        """Return the stable user ID for this identity, or None if unknown."""
        user = await lookup_user(identity)
        return user.id if user else None

    async def permits(self, identity: Optional[str], permission: Union[str, Enum],
                      context: Any = None) -> bool:
        """Return True if identity has the permission."""
        if identity is None:
            return False
        user = await lookup_user(identity)
        return user and permission in user.permissions
```

### Choosing an Identity Policy

| Policy | Storage | Extra dependency | Best for |
|---|---|---|---|
| `SessionIdentityPolicy` | `aiohttp-session` (encrypted cookie or Redis) | `aiohttp-session` | Most applications |
| `CookiesIdentityPolicy` | Plain HTTP cookie | None | Demos / prototypes only |
| `JWTIdentityPolicy` | `Authorization: Bearer <token>` header | `PyJWT` | Stateless / API servers |

**SessionIdentityPolicy** requires `aiohttp-session` to be set up first:

```python
from aiohttp_session import setup as setup_session, EncryptedCookieStorage
from aiohttp_security import SessionIdentityPolicy

setup_session(app, EncryptedCookieStorage(secret_key))
setup(app, SessionIdentityPolicy(), MyAuthPolicy())
```

**JWTIdentityPolicy** decodes tokens from the `Authorization: Bearer <token>` header:

```python
from aiohttp_security import JWTIdentityPolicy

setup(app, JWTIdentityPolicy(secret="my-secret", algorithm="HS256", key="sub"), MyAuthPolicy())
```

The `key` parameter selects which claim in the decoded JWT is used as the identity (default `"login"`).

## Gotchas

- **Identity is a session-wide string shared with the client.** Never store database primary keys, emails, or passwords as the identity. Use a UUID or opaque token so the client cannot guess another user's identity.
- **`SimpleCookieStorage` is insecure.** The demo uses it for convenience. Production code must use `EncryptedCookieStorage` (with a Fernet key) or `RedisStorage`.
- **`CookiesIdentityPolicy` is for demos only.** It stores the identity as a plain cookie with no encryption. Use `SessionIdentityPolicy` with encrypted storage instead.
- **`JWTIdentityPolicy.remember` and `forget` are no-ops.** JWT is stateless — the client holds the token. To "log out" with JWT, reject the token server-side (e.g., via a deny list) or rely on token expiration.
- **`permits` returns `True` when security is not set up.** If `setup()` was not called, `permits()` silently returns `True`. Always verify with `check_authorized()` or `check_permission()` which raise on missing setup.
- **`authorized_userid` returns `None` for unknown identities.** The authorization policy's `authorized_userid` method is the gate — if it returns `None`, the user is treated as anonymous even though an identity exists in the session.
- **`remember` raises `ValueError` if identity is not a string.** Pass a string, not an integer or object.
- **`check_permission` raises `HTTPForbidden` (403), not `HTTPUnauthorized` (402).** Anonymous users get 401 from the internal `check_authorized` call; authenticated users without the permission get 403.
- **`aiohttp-session` must be initialized before `SessionIdentityPolicy`.** Call `aiohttp_session.setup(app, storage)` before creating the identity policy, or `SessionIdentityPolicy` will raise `ImportError` at construction time.
- **`JWTIdentityPolicy` raises `ValueError` on wrong auth scheme.** If the `Authorization` header is present but does not start with `Bearer `, a `ValueError` is raised (not silently ignored). Handle this in middleware or a global exception handler.
- **`setup()` validates policy types.** Passing a non-subclass of `AbstractIdentityPolicy` or `AbstractAuthorizationPolicy` raises `ValueError` immediately.

## References

- [01-api-reference](references/01-api-reference.md) — Full API reference for all public functions and abstract policy methods
- [02-identity-policies](references/02-identity-policies.md) — Deep dive into CookiesIdentityPolicy, SessionIdentityPolicy, and JWTIdentityPolicy
- [03-custom-auth-policy](references/03-custom-auth-policy.md) — Patterns for building authorization policies (in-memory, dictionary, database)
- [04-complete-examples](references/04-complete-examples.md) — Full runnable demos (simple auth, dictionary auth, database auth with SQLAlchemy)
