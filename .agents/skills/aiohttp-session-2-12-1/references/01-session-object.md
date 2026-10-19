# Session Object

## Class: `Session`

The `Session` class implements `MutableMapping[str, Any]`, providing full dict-like semantics plus session-specific properties and methods.

### Creation

Never instantiate `Session` directly. Retrieve it through:

```python
from aiohttp_session import get_session, new_session

# Load existing or create new
session = await get_session(request)

# Force new session (use during login)
session = await new_session(request)
```

The middleware caches the session on the request object, so repeated calls to `get_session(request)` within the same request return the same instance.

### Dictionary Interface

| Operation | Auto-changed? | Notes |
|---|---|---|
| `session["key"] = value` | Yes | Sets value, marks changed, updates `created` |
| `value = session["key"]` | No | Raises `KeyError` if missing |
| `del session["key"]` | Yes | Removes key, marks changed, updates `created` |
| `"key" in session` | No | Membership test |
| `len(session)` | No | Number of keys |
| `session.get("key", default)` | No | Safe get (from MutableMapping mixin) |
| `session.pop("key", default)` | Yes | Removes and returns value |
| `session.clear()` | Yes | Removes all keys |
| `for k in session` | No | Iterates keys |

### Properties

#### `session.new` — `bool`

`True` if this is a brand-new session (not loaded from storage). `False` if session was restored from existing data.

```python
session = await get_session(request)
if session.new:
    # First visit — no prior session data
    pass
```

#### `session.created` — `int`

UNIX timestamp (from `time.time()`) of when the session was first created. Updated on each `__setitem__` or `__delitem__` call.

```python
import time
age_seconds = time.time() - session.created
if age_seconds > 3600:
    # Session is older than 1 hour
    pass
```

#### `session.empty` — `bool`

`True` if the session has no data keys. Equivalent to `len(session) == 0`.

#### `session.identity` — `str | None`

Read-only. The storage-specific identity of the session. For cookie-based storages, this is `None`. For Redis/Memcached, this is the UUID key stored in the cookie.

#### `session.max_age` — `int | None`

Session lifetime in seconds. `None` means session cookie (expires on browser close). Readable and writable.

```python
# Shorten session to 30 minutes
session.max_age = 1800
```

### Methods

#### `session.changed()`

Explicitly mark the session as modified. Required when mutating nested mutable values:

```python
session["cart"] = session.get("cart", [])
session["cart"].append({"item": "book", "qty": 1})
session.changed()  # Required — the list mutation is invisible to Session
```

Not needed for direct key operations (`session["key"] = value`, `del session["key"]`, `session.pop()`) — those auto-mark changed.

#### `session.invalidate()`

Clear all session data and mark as changed. The middleware will delete the cookie on response. Use for logout:

```python
session = await get_session(request)
session.invalidate()
raise web.HTTPFound("/")
```

Equivalent to:
```python
session._mapping = {}
session._changed = True
```

#### `session.set_new_identity(identity)`

Change the session identity. Only valid on new sessions (`session.new == True`). Raises `RuntimeError` on existing sessions.

Used internally by Redis/Memcached storage when rotating session keys. Rarely needed in application code.

### Serialization

Session data is serialized through the storage's `encoder` (default `json.dumps`) and deserialized through `decoder` (default `json.loads`). This means:

- Keys must be strings (JSON object keys are always strings)
- Values must be JSON-serializable: `str`, `int`, `float`, `bool`, `None`, `list`, `dict`
- `datetime`, `set`, `bytes`, custom objects will raise on serialization
- Use custom `encoder`/`decoder` for non-standard types:

```python
import datetime
import json

def encode(obj):
    if isinstance(obj, datetime.datetime):
        return {"__datetime__": obj.isoformat()}
    raise TypeError(f"Cannot encode {type(obj)}")

def decode(obj):
    if isinstance(obj, dict) and "__datetime__" in obj:
        return datetime.datetime.fromisoformat(obj["__datetime__"])
    return obj

storage = EncryptedCookieStorage(
    key,
    encoder=lambda obj: json.dumps(obj, default=encode),
    decoder=lambda s: json.loads(s, object_hook=decode),
)
```

### Thread Safety

Session objects are request-scoped — each request gets its own `Session` instance. No thread safety concerns since aiohttp is single-threaded (async).
