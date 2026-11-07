import os

os.environ.setdefault("CV_ENV", "test")
os.environ.setdefault("CV_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/cineverse_test")
os.environ.setdefault("CV_REDIS_URL", "redis://localhost:6379/15")
os.environ["CV_RUN_SWEEPER"] = "false"
os.environ["CV_PAYMENT_PROVIDER"] = "mock"

import itertools  # noqa: E402
from datetime import datetime, timezone  # noqa: E402

import httpx  # noqa: E402
import pytest  # noqa: E402
from sqlalchemy import select, text  # noqa: E402

from app.core.redis import get_redis  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_engine, sessionmaker  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Show  # noqa: E402
from app.seed import seed  # noqa: E402

_counter = itertools.count()


@pytest.fixture(scope="session", autouse=True)
async def database():
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with sessionmaker()() as db:
        await seed(db, days=2)
    yield
    await get_redis().flushdb()


@pytest.fixture(autouse=True)
async def clean_state():
    await get_redis().flushdb()
    async with sessionmaker()() as db:
        await db.execute(text("TRUNCATE webhook_events, payments, booking_seats, bookings RESTART IDENTITY CASCADE"))
        await db.commit()
    yield


@pytest.fixture
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test/api") as c:
        yield c


@pytest.fixture
def register(client):
    async def _make(name: str = "user", admin: bool = False):
        if admin:
            r = await client.post("/auth/login", json={"email": "admin@cineverse.dev", "password": "Admin@123"})
        else:
            n = next(_counter)
            r = await client.post("/auth/register", json={
                "email": f"{name}{n}@example.com", "password": "Passw0rd!", "full_name": f"{name} {n}"})
        assert r.status_code in (200, 201), r.text
        body = r.json()
        return {"Authorization": f"Bearer {body['access_token']}"}, body
    return _make


@pytest.fixture
async def show_id():
    async with sessionmaker()() as db:
        s = (await db.execute(select(Show).where(Show.starts_at > datetime.now(timezone.utc))
                              .order_by(Show.starts_at.desc()).limit(1))).unique().scalars().first()
        return s.id


@pytest.fixture
async def seats(client, show_id):
    r = await client.get(f"/shows/{show_id}/seats")
    return [s for s in r.json()["seats"] if s["state"] == "available"]
