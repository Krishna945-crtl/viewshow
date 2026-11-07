from typing import Annotated

import jwt
from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.redis import get_redis
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User
from app.services.holds import HoldStore

DB = Annotated[AsyncSession, Depends(get_db)]


def get_holds() -> HoldStore:
    return HoldStore(get_redis())


Holds = Annotated[HoldStore, Depends(get_holds)]


def _token(authorization: str | None) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


async def user_from_token(db: AsyncSession, token: str | None) -> User | None:
    if not token:
        return None
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError:
        return None
    user = await db.get(User, payload["sub"])
    return user if user and user.is_active else None


async def optional_user(db: DB, authorization: Annotated[str | None, Header()] = None) -> User | None:
    return await user_from_token(db, _token(authorization))


async def current_user(db: DB, authorization: Annotated[str | None, Header()] = None) -> User:
    user = await user_from_token(db, _token(authorization))
    if not user:
        raise AppError(401, "unauthorized", "Please sign in")
    return user


async def admin_user(user: Annotated[User, Depends(current_user)]) -> User:
    if not user.is_admin:
        raise AppError(403, "forbidden", "Admins only")
    return user


CurrentUser = Annotated[User, Depends(current_user)]
OptionalUser = Annotated[User | None, Depends(optional_user)]
AdminUser = Annotated[User, Depends(admin_user)]
