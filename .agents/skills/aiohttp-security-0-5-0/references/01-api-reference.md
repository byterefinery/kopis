# API Reference

Full reference for `aiohttp-security` 0.5.0 public API.

## Setup

### `setup(app, identity_policy, autz_policy)`

Register identity and authorization policies on an `aiohttp.web.Application`.

| Parameter | Type | Description |
|---|---|---|
| `app` | `web.Application` | The aiohttp application |
| `identity_policy` | `AbstractIdentityPolicy` | Handles identity storage/retrieval |
| `autz_policy` | `AbstractAuthorizationPolicy` | Handles user lookup and permission checks |

Raises `ValueError` if either policy is not a subclass of the expected abstract class.

Policies are stored internally using `aiohttp.web.AppKey` (`IDENTITY_KEY` / `AUTZ_KEY`).

## Session Management

### `async remember(request, response, identity, **kwargs)`

Store an identity in the response (cookie, session, etc.). After this call, subsequent requests will carry the identity.

| Parameter | Type | Description |
|---|---|---|
| `request` | `web.Request` | Current request |
| `response` | `web.StreamResponse` | Response to modify (usually `web.HTTPFound` for redirects) |
| `identity` | `str` | The identity string to remember |
| `**kwargs` | — | Policy-specific (e.g., `max_age` for `CookiesIdentityPolicy`) |

Raises `ValueError` if identity is not a string. Raises `HTTPInternalServerError` if security is not set up.

### `async forget(request, response)`

Remove the identity from the response, effectively logging the user out.

| Parameter | Type | Description |
|---|---|---|
| `request` | `web.Request` | Current request |
| `response` | `web.StreamResponse` | Response to modify |

Raises `HTTPInternalServerError` if security is not set up.

## Inspection

### `async authorized_userid(request) -> Optional[str]`

Return the stable user ID for the current request, or `None` if anonymous.

Combines `identity_policy.identify(request)` with `autz_policy.authorized_userid(identity)`. Returns `None` if either policy is missing or if the identity cannot be resolved to a user.

### `async is_anonymous(request) -> bool`

Return `True` if no identity is present in the request.

Checks `identity_policy.identify(request)` — returns `True` if the result is `None` or if no identity policy is configured.

### `async permits(request, permission, context=None) -> bool`

Check whether the current user has a given permission.

| Parameter | Type | Description |
|---|---|---|
| `request` | `web.Request` | Current request |
| `permission` | `str` or `enum.Enum` | The permission to check |
| `context` | `Any` | Optional context object passed to `autz_policy.permits()` |

Raises `ValueError` if permission is not a `str` or `enum.Enum`. Returns `True` if no policies are configured (fail-open). Delegates to `autz_policy.permits(identity, permission, context)`.

## Guards

### `async check_authorized(request) -> str`

Raise `HTTPUnauthorized` if the user is anonymous. Return the authorized user ID on success.

Use at the top of handlers that require any authenticated user:

```python
async def my_handler(request):
    userid = await check_authorized(request)
    # only reached by authenticated users
```

### `async check_permission(request, permission, context=None)`

Raise `HTTPUnauthorized` for anonymous users, `HTTPForbidden` for authenticated users lacking the permission.

```python
async def admin_handler(request):
    await check_permission(request, "admin")
    # only reached by users with "admin" permission
```

The `HTTPForbidden` response includes a reason: `"User does not have 'admin' permission"`.

## Abstract Policies

### `AbstractIdentityPolicy`

| Method | Signature | Description |
|---|---|---|
| `identify` | `async identify(request) -> Optional[str]` | Extract identity from request, or `None` |
| `remember` | `async remember(request, response, identity, **kwargs)` | Store identity into response |
| `forget` | `async forget(request, response)` | Remove identity from response |

### `AbstractAuthorizationPolicy`

| Method | Signature | Description |
|---|---|---|
| `authorized_userid` | `async authorized_userid(identity) -> Optional[str]` | Map identity to stable user ID, or `None` |
| `permits` | `async permits(identity, permission, context=None) -> bool` | Check if identity has permission |

## Imports

All public symbols are exported from the top-level package:

```python
from aiohttp_security import (
    AbstractAuthorizationPolicy,
    AbstractIdentityPolicy,
    CookiesIdentityPolicy,
    SessionIdentityPolicy,
    JWTIdentityPolicy,
    remember,
    forget,
    authorized_userid,
    permits,
    setup,
    is_anonymous,
    check_authorized,
    check_permission,
)
```

The abstract classes are also available from `aiohttp_security.abc`.
