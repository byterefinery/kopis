# Custom Storage

## Writing a Custom Storage

Custom storage backends extend `AbstractStorage` and implement two async methods: `load_session()` and `save_session()`. The base class provides cookie handling helpers.

### Minimal Example

```python
import abc
from aiohttp import web
from aiohttp_session import AbstractStorage, Session

class MyStorage(AbstractStorage):
    async def load_session(self, request: web.Request) -> Session:
        cookie = self.load_cookie(request)
        if cookie is None:
            return Session(None, data=None, new=True, max_age=self.max_age)

        # Decode cookie data into session dict
        data = self._decoder(cookie)
        return Session(None, data=data, new=False, max_age=self.max_age)

    async def save_session(
        self, request: web.Request, response: web.StreamResponse, session: Session
    ) -> None:
        if session.empty:
            self.save_cookie(response, "", max_age=session.max_age)
            return

        data = self._encoder(self._get_session_data(session))
        self.save_cookie(response, data, max_age=session.max_age)
```

### Registering

```python
from aiohttp_session import setup

setup(app, MyStorage())
```

## AbstractStorage API

### Constructor Parameters

```python
AbstractStorage(
    cookie_name: str = "AIOHTTP_SESSION",  # Cookie name
    domain: str | None = None,              # Cookie domain
    max_age: int | None = None,             # Session lifetime (seconds)
    path: str = "/",                        # Cookie path
    secure: bool | None = None,             # HTTPS-only cookie
    httponly: bool = True,                  # No JS access
    samesite: str | None = None,            # CSRF protection ("lax", "strict", "none")
    encoder: Callable[[Any], str] = json.dumps,  # Serializer
    decoder: Callable[[str], Any] = json.loads,  # Deserializer
)
```

### Properties

- `cookie_name` — name of the session cookie
- `max_age` — session lifetime in seconds
- `cookie_params` — dict of cookie parameters
- `encoder` / `decoder` — serializer/deserializer

### Methods to Implement

#### `async load_session(request) -> Session`

Called by the middleware on each request. Load session data from your backend and return a `Session` instance.

```python
async def load_session(self, request: web.Request) -> Session:
    # 1. Read cookie (or other identifier)
    cookie = self.load_cookie(request)

    # 2. If no cookie, return new session
    if cookie is None:
        return Session(None, data=None, new=True, max_age=self.max_age)

    # 3. Load data from backend
    data = await self._backend.get(cookie)

    # 4. If data not found, return new session
    if data is None:
        return Session(None, data=None, new=True, max_age=self.max_age)

    # 5. Decode and return session
    decoded = self._decoder(data)
    return Session(cookie, data=decoded, new=False, max_age=self.max_age)
```

#### `async save_session(request, response, session) -> None`

Called by the middleware after the handler returns (only if `session._changed` is `True`). Persist session data and set/update the cookie.

```python
async def save_session(
    self, request: web.Request, response: web.StreamResponse, session: Session
) -> None:
    # 1. Get or create identity (key)
    key = session.identity
    if key is None:
        key = self._key_factory()

    # 2. Save data to backend
    if session.empty:
        await self._backend.delete(key)
        self.save_cookie(response, "", max_age=session.max_age)
    else:
        data = self._encoder(self._get_session_data(session))
        await self._backend.set(key, data, ttl=session.max_age)
        self.save_cookie(response, key, max_age=session.max_age)
```

### Helper Methods

- `load_cookie(request) -> str | None` — reads the session cookie from request
- `save_cookie(response, data, *, max_age=None) -> None` — sets or deletes the cookie on response
- `_get_session_data(session) -> dict` — extracts `{"created": ..., "session": {...}}` from a Session
- `new_session() -> Session` — creates a fresh empty Session

## Session Constructor

```python
Session(
    identity: Any | None,          # Storage-specific identifier (key, UUID, etc.)
    *,
    data: dict | None,             # SessionData: {"created": int, "session": dict}
    new: bool,                     # True if this is a brand-new session
    max_age: int | None = None,    # Session lifetime
)
```

- `identity` — for cookie-based storages, pass `None`. For server-side storages, pass the key (UUID string).
- `data` — dict with `created` (UNIX timestamp) and `session` (the actual session dict). Pass `None` for empty new sessions.
- `new` — `True` for first-time sessions, `False` for restored sessions.

### Data Format

```python
# Full session data
data = {
    "created": 1700000000,
    "session": {"user_id": "abc123", "cart": [{"item": "book"}]}
}

# Empty session
data = {}  # or None
```

## Database Example (PostgreSQL)

```python
import json
import uuid
from aiohttp import web
from aiohttp_session import AbstractStorage, Session

class PostgresStorage(AbstractStorage):
    def __init__(self, pool, **kwargs):
        super().__init__(**kwargs)
        self._pool = pool
        self._key_factory = lambda: uuid.uuid4().hex

    async def load_session(self, request: web.Request) -> Session:
        cookie = self.load_cookie(request)
        if cookie is None:
            return Session(None, data=None, new=True, max_age=self.max_age)

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT data FROM sessions WHERE key = $1", cookie
            )

        if row is None:
            return Session(None, data=None, new=True, max_age=self.max_age)

        try:
            data = self._decoder(row["data"])
        except ValueError:
            data = None

        return Session(cookie, data=data, new=False, max_age=self.max_age)

    async def save_session(
        self, request: web.Request, response: web.StreamResponse, session: Session
    ) -> None:
        key = session.identity
        if key is None:
            key = self._key_factory()

        if session.empty:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    "DELETE FROM sessions WHERE key = $1", key
                )
            self.save_cookie(response, "", max_age=session.max_age)
        else:
            data = self._encoder(self._get_session_data(session))
            async with self._pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO sessions (key, data) VALUES ($1, $2) "
                    "ON CONFLICT (key) DO UPDATE SET data = $2",
                    key, data,
                )
            self.save_cookie(response, key, max_age=session.max_age)
```

## Third-Party Extensions

Community-maintained storage backends:

- [aiohttp-session-mongo](https://github.com/alexpantyukhin/aiohttp-session-mongo) — MongoDB storage
- [aiohttp-session-dynamodb](https://github.com/alexpantyukhin/aiohttp-session-dynamodb) — AWS DynamoDB storage
