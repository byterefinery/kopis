# Custom Authorization Policies

Patterns for implementing `AbstractAuthorizationPolicy`.

## Interface

```python
from enum import Enum
from typing import Any, Optional, Union
from aiohttp_security.abc import AbstractAuthorizationPolicy

class MyPolicy(AbstractAuthorizationPolicy):

    async def authorized_userid(self, identity: str) -> Optional[str]:
        """Return the stable user ID for this identity, or None."""
        ...

    async def permits(self, identity: Optional[str], permission: Union[str, Enum],
                      context: Any = None) -> bool:
        """Return True if identity has permission."""
        ...
```

- `authorized_userid` receives the **identity string** (from the identity policy) and returns a stable user ID (often the same string, or a database primary key). Return `None` if the identity is unknown.
- `permits` receives the **identity** (may be `None` for anonymous requests), a permission (`str` or `enum.Enum`), and an optional `context`. Return `True` to allow, `False` to deny.

## In-Memory (Dictionary) Policy

Suitable for small applications with a fixed set of users.

```python
from dataclasses import dataclass
from typing import Mapping, Optional, Union
from enum import Enum
from aiohttp_security.abc import AbstractAuthorizationPolicy

@dataclass
class User:
    password: str
    permissions: frozenset

# Identity -> User mapping
user_map: dict[str, User] = {
    "alice": User(password="hashed_pw_1", permissions=frozenset({"read", "write"})),
    "bob":   User(password="hashed_pw_2", permissions=frozenset({"read"})),
}

class DictionaryAuthorizationPolicy(AbstractAuthorizationPolicy):

    def __init__(self, user_map: Mapping[str, User]):
        self.user_map = user_map

    async def authorized_userid(self, identity: str) -> Optional[str]:
        return identity if identity in self.user_map else None

    async def permits(self, identity: Optional[str], permission: Union[str, Enum],
                      context: None = None) -> bool:
        user = self.user_map.get(identity)
        if not user:
            return False
        return permission in user.permissions
```

### Credential Verification

```python
async def check_credentials(user_map, username: str, password: str) -> bool:
    user = user_map.get(username)
    if not user:
        return False
    return user.password == hash_password(password)
```

Store hashed passwords (e.g., via `passlib`), never plaintext.

## Database Policy (SQLAlchemy)

For applications with users stored in a relational database.

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

### Typical Schema

```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import sqlalchemy as sa

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

## Permission Enums

Use `enum.Enum` for type-safe permissions:

```python
from enum import Enum

class Permissions(Enum):
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"

async def permits(self, identity, permission, context=None):
    # permission is Permissions.READ, Permissions.WRITE, etc.
    return user and permission in user.permissions
```

## Context-Aware Permissions

The `context` parameter in `permits` enables resource-level authorization:

```python
async def permits(self, identity, permission, context=None):
    if context and isinstance(context, dict):
        resource_id = context.get("resource_id")
        return user_owns_resource(user, resource_id)
    return basic_permission_check(user, permission)
```

Usage in handlers:

```python
await check_permission(request, "edit", context={"resource_id": post_id})
```
