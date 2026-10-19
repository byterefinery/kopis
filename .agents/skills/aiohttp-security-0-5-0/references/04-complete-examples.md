# Complete Examples

Runnable demos from the `aiohttp-security` repository.

## Simple Auth (Session-based, Single User)

Minimal example with one hardcoded user. Uses `aiohttp-session` with `SimpleCookieStorage` (demo only — use `EncryptedCookieStorage` in production).

```python
from enum import Enum
from typing import NoReturn, Optional, Union
from aiohttp import web
from aiohttp_session import SimpleCookieStorage, session_middleware
from aiohttp_security import (
    SessionIdentityPolicy, check_permission, forget,
    is_anonymous, remember, setup as setup_security
)
from aiohttp_security.abc import AbstractAuthorizationPolicy


class SimpleAuthPolicy(AbstractAuthorizationPolicy):
    async def authorized_userid(self, identity: str) -> Optional[str]:
        return identity if identity == "jack" else None

    async def permits(self, identity: Optional[str], permission: Union[str, Enum],
                      context: None = None) -> bool:
        return identity == "jack" and permission == "listen"


async def handler_root(request: web.Request) -> web.Response:
    is_logged = not await is_anonymous(request)
    return web.Response(
        text=f"Hello Jack, logged in: {is_logged}",
        content_type="text/html"
    )


async def handler_login(request: web.Request) -> NoReturn:
    response = web.HTTPFound("/")
    await remember(request, response, "jack")
    raise response


async def handler_logout(request: web.Request) -> NoReturn:
    response = web.HTTPFound("/")
    await forget(request, response)
    raise response


async def handler_listen(request: web.Request) -> web.Response:
    await check_permission(request, "listen")
    return web.Response(text="I can listen!")


async def make_app() -> web.Application:
    middleware = session_middleware(SimpleCookieStorage())
    app = web.Application(middlewares=[middleware])

    app.router.add_get("/", handler_root)
    app.router.add_get("/login", handler_login)
    app.router.add_get("/logout", handler_logout)
    app.router.add_get("/listen", handler_listen)

    setup_security(app, SessionIdentityPolicy(), SimpleAuthPolicy())
    return app


if __name__ == "__main__":
    web.run_app(make_app(), port=9000)
```

## Dictionary Auth (Multiple Users, Encrypted Sessions)

Multiple users with hashed passwords, encrypted cookie sessions, and a login form.

### Users

```python
from dataclasses import dataclass

@dataclass
class User:
    password: str
    permissions: frozenset

user_map = {
    "alice": User(password="hashed_alice", permissions=frozenset({"read", "write"})),
    "bob":   User(password="hashed_bob",   permissions=frozenset({"read"})),
}
```

### Authorization Policy

```python
from enum import Enum
from typing import Mapping, Optional, Union
from aiohttp_security.abc import AbstractAuthorizationPolicy

class DictionaryAuthorizationPolicy(AbstractAuthorizationPolicy):
    def __init__(self, user_map: Mapping[str, User]):
        self.user_map = user_map

    async def authorized_userid(self, identity: str) -> Optional[str]:
        return identity if identity in self.user_map else None

    async def permits(self, identity: Optional[str], permission: Union[str, Enum],
                      context: None = None) -> bool:
        user = self.user_map.get(identity)
        return bool(user and permission in user.permissions)
```

### Handlers

```python
from aiohttp import web
from aiohttp_security import authorized_userid, check_authorized, check_permission, forget, remember

async def index(request: web.Request) -> web.Response:
    username = await authorized_userid(request)
    msg = f"Hello, {username}!" if username else "You need to login"
    return web.Response(text=msg, content_type="text/html")

async def login(request: web.Request):
    form = await request.post()
    username = form.get("username")
    password = form.get("password")
    if verify_credentials(username, password):
        response = web.HTTPFound("/")
        await remember(request, response, username)
        raise response
    raise web.HTTPUnauthorized()

async def logout(request: web.Request):
    await check_authorized(request)
    response = web.Response(text="Logged out")
    await forget(request, response)
    return response

async def public_page(request: web.Request):
    await check_permission(request, "read")
    return web.Response(text="Public area")

async def protected_page(request: web.Request):
    await check_permission(request, "write")
    return web.Response(text="Protected area")
```

### App Setup

```python
import base64
from aiohttp import web
from aiohttp_session import setup as setup_session
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from cryptography import fernet
from aiohttp_security import SessionIdentityPolicy, setup as setup_security

def make_app() -> web.Application:
    app = web.Application()
    app["user_map"] = user_map

    fernet_key = fernet.Fernet.generate_key()
    secret_key = base64.urlsafe_b64decode(fernet_key)

    setup_session(app, EncryptedCookieStorage(secret_key, cookie_name="API_SESSION"))
    setup_security(app, SessionIdentityPolicy(), DictionaryAuthorizationPolicy(user_map))

    app.router.add_get("/", index)
    app.router.add_post("/login", login)
    app.router.add_get("/logout", logout)
    app.router.add_get("/public", public_page)
    app.router.add_get("/protected", protected_page)

    return app
```

## Database Auth (SQLAlchemy, Async)

Full database-backed example with user/permission tables.

### Models

```python
import sqlalchemy as sa
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(sa.String(256), unique=True, index=True)
    password: Mapped[str] = mapped_column(sa.String(256))
    is_superuser: Mapped[bool] = mapped_column(default=False)
    disabled: Mapped[bool] = mapped_column(default=False)
    permissions = relationship("Permission", cascade="all, delete")

class Permission(Base):
    __tablename__ = "permissions"
    user_id: Mapped[int] = mapped_column(sa.ForeignKey(User.id, ondelete="CASCADE"), primary_key=True)
    name: Mapped[str] = mapped_column(sa.String(64), primary_key=True)
```

### DB Authorization Policy

```python
from enum import Enum
from typing import Any, Optional, Union
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload
from aiohttp_security.abc import AbstractAuthorizationPolicy

class DBAuthorizationPolicy(AbstractAuthorizationPolicy):
    def __init__(self, dbsession: async_sessionmaker[AsyncSession]):
        self.dbsession = dbsession

    async def authorized_userid(self, identity: str) -> Optional[str]:
        async with self.dbsession() as sess:
            user_id = await sess.scalar(
                sa.select(User.id).where(User.username == identity, ~User.disabled)
            )
        return str(user_id) if user_id else None

    async def permits(self, identity: Optional[str], permission: Union[str, Enum],
                      context: Any = None) -> bool:
        if identity is None:
            return False
        async with self.dbsession() as sess:
            user = await sess.scalar(
                sa.select(User)
                .options(selectinload(User.permissions))
                .where(User.username == identity, ~User.disabled)
            )
        if user is None:
            return False
        if user.is_superuser:
            return True
        return any(p.name == permission for p in user.permissions)
```

### Password Verification

```python
from passlib.hash import sha256_crypt

async def check_credentials(db_session: async_sessionmaker[AsyncSession],
                            username: str, password: str) -> bool:
    async with db_session() as sess:
        hashed_pw = await sess.scalar(
            sa.select(User.password).where(User.username == username, ~User.disabled)
        )
    if hashed_pw is None:
        return False
    return sha256_crypt.verify(password, hashed_pw)
```

### App Bootstrap

```python
from aiohttp import web
from aiohttp_session import SimpleCookieStorage, setup as setup_session
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from aiohttp_security import SessionIdentityPolicy, setup as setup_security

async def init_app() -> web.Application:
    app = web.Application()

    db_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    app["db_session"] = async_sessionmaker(db_engine, expire_on_commit=False)

    # Create tables and seed data
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    setup_session(app, SimpleCookieStorage())
    setup_security(app, SessionIdentityPolicy(), DBAuthorizationPolicy(app["db_session"]))

    # Register routes (see handler code above)
    return app
```
