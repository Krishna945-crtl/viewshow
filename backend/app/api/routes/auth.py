from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Request
from sqlalchemy import select

from app.api.deps import DB, CurrentUser
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.ratelimit import rate_limit
from app.core.security import create_access_token, hash_password, new_refresh_token, sha256, verify_password
from app.models import RefreshToken, User
from app.schemas.api import LoginIn, ProfileIn, RefreshIn, RegisterIn, TokenOut, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


async def _issue(db, user: User) -> TokenOut:
    raw, digest = new_refresh_token()
    db.add(RefreshToken(user_id=user.id, token_hash=digest,
                        expires_at=datetime.now(timezone.utc) + timedelta(days=get_settings().refresh_token_days)))
    await db.commit()
    return TokenOut(access_token=create_access_token(user.id, user.is_admin), refresh_token=raw,
                    user=UserOut.model_validate(user))


@router.post("/register", response_model=TokenOut, status_code=201)
async def register(body: RegisterIn, db: DB, request: Request):
    await rate_limit(request, "register", 10, 3600)
    email = body.email.lower()
    if (await db.execute(select(User.id).where(User.email == email))).first():
        raise AppError(409, "email_taken", "An account with this email already exists")
    user = User(email=email, full_name=body.full_name.strip(), password_hash=hash_password(body.password),
                city=body.city)
    db.add(user)
    await db.flush()
    return await _issue(db, user)


@router.post("/login", response_model=TokenOut)
async def login(body: LoginIn, db: DB, request: Request):
    await rate_limit(request, "login", 20, 300)
    user = (await db.execute(select(User).where(User.email == body.email.lower()))).scalars().first()
    if not user or not verify_password(body.password, user.password_hash) or not user.is_active:
        raise AppError(401, "bad_credentials", "Email or password is incorrect")
    return await _issue(db, user)


@router.post("/refresh", response_model=TokenOut)
async def refresh(body: RefreshIn, db: DB):
    row = (await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == sha256(body.refresh_token)).with_for_update()
    )).scalars().first()
    if not row or row.revoked or row.expires_at < datetime.now(timezone.utc):
        if row and row.revoked:
            # reuse of a rotated token -> someone copied it. kill the whole family
            for t in (await db.execute(select(RefreshToken).where(RefreshToken.user_id == row.user_id))).scalars():
                t.revoked = True
            await db.commit()
        raise AppError(401, "bad_refresh", "Session expired, please sign in again")
    row.revoked = True  # rotation
    user = await db.get(User, row.user_id)
    if not user or not user.is_active:
        raise AppError(401, "bad_refresh", "Session expired, please sign in again")
    return await _issue(db, user)


@router.post("/logout", status_code=204)
async def logout(body: RefreshIn, db: DB):
    row = (await db.execute(select(RefreshToken).where(RefreshToken.token_hash == sha256(body.refresh_token)))).scalars().first()
    if row:
        row.revoked = True
        await db.commit()


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser):
    return user


@router.patch("/me", response_model=UserOut)
async def update_me(body: ProfileIn, user: CurrentUser, db: DB):
    u = await db.get(User, user.id)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(u, k, v)
    await db.commit()
    return u
