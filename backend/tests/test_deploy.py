"""Things that only matter once the app runs somewhere public."""

import pytest
from sqlalchemy import func, select

from app.core.config import Settings, asyncpg_url
from app.db.session import sessionmaker
from app.models import Auditorium, Show, Theatre
from app.seed import PRICES, top_up


@pytest.mark.parametrize("given,expected", [
    # what Neon / Render / Heroku hand out
    ("postgresql://u:p@ep-cool-1.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require",
     "postgresql+asyncpg://u:p@ep-cool-1.ap-southeast-1.aws.neon.tech/neondb?ssl=require"),
    ("postgres://u:p@host:5432/db", "postgresql+asyncpg://u:p@host:5432/db"),
    # already right -> untouched
    ("postgresql+asyncpg://postgres:postgres@localhost:5432/cineverse",
     "postgresql+asyncpg://postgres:postgres@localhost:5432/cineverse"),
])
def test_hosted_database_urls_work_with_asyncpg(given, expected):
    assert asyncpg_url(given) == expected
    assert Settings(_env_file=None, database_url=given).database_url == expected


def test_prod_refuses_laptop_secrets():
    with pytest.raises(RuntimeError, match="CV_JWT_SECRET") as err:
        Settings(_env_file=None, env="prod", database_url="postgres://u:hunter2@db/x")
    assert "hunter2" not in str(err.value)  # never echo settings into logs
    ok = Settings(_env_file=None, env="prod", jwt_secret="a" * 40, ticket_signing_secret="b" * 40,
                  mock_payment_secret="c" * 40, seed_admin_password="Strong-Admin-9")
    assert ok.env == "prod"


async def test_top_up_fills_missing_days_once():
    async with sessionmaker()() as db:
        # seeded halls only - admin tests add their own tiny auditoriums
        halls = (await db.execute(select(func.count(Auditorium.id)).join(Theatre).where(
            Theatre.is_demo.is_(True), Auditorium.name.in_(PRICES)))).scalar_one()
        before = (await db.execute(select(func.count(Show.id)))).scalar_one()
        # the test DB was seeded with 2 days -> asking for 3 adds exactly one day everywhere
        added = await top_up(db, days=3)
        assert added == halls * 4
        assert (await db.execute(select(func.count(Show.id)))).scalar_one() == before + added
        assert await top_up(db, days=3) == 0  # idempotent: safe on every container boot
