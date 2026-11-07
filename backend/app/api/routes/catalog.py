from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from typing import Annotated

from fastapi import APIRouter, File, Query, Request, UploadFile
from sqlalchemy import func, or_, select

from app.api.deps import DB
from app.api.serializers import movie_out, show_out
from app.api.uploads import palette_or_400, read_image
from app.core.config import get_settings
from app.core.ratelimit import rate_limit
from app.core.errors import not_found
from app.models import Auditorium, Movie, Show, Theatre
from app.schemas.api import ThemePreviewIn
from app.services.theme_engine import generate_theme

router = APIRouter(tags=["catalog"])
IST = ZoneInfo("Asia/Kolkata")  # demo venues are all in India


async def _movie(db, key: str) -> Movie:
    m = (await db.execute(select(Movie).where(or_(Movie.id == key, Movie.slug == key)))).scalars().first()
    if not m:
        raise not_found("Movie")
    return m


@router.get("/movies")
async def list_movies(db: DB, q: str | None = None, genre: str | None = None, city: str | None = None,
                      language: str | None = None):
    stmt = select(Movie).where(Movie.is_active.is_(True)).order_by(Movie.release_date.desc().nulls_last(), Movie.title)
    if q:
        stmt = stmt.where(Movie.title.ilike(f"%{q.strip()}%"))
    if language:
        stmt = stmt.where(Movie.language == language)
    if city:
        now = datetime.now(timezone.utc)
        stmt = stmt.where(Movie.id.in_(
            select(Show.movie_id).join(Auditorium).join(Theatre)
            .where(Theatre.city == city, Show.starts_at > now, Show.is_cancelled.is_(False))
        ))
    movies = (await db.execute(stmt)).unique().scalars().all()
    if genre:
        g = genre.lower()
        movies = [m for m in movies if g in [x.lower() for x in m.genres]]
    return [movie_out(m) for m in movies]


@router.get("/movies/{key}")
async def get_movie(key: str, db: DB):
    return movie_out(await _movie(db, key), full=True)


@router.get("/genres")
async def genres(db: DB):
    found: set[str] = set()
    for g in (await db.execute(select(Movie.genres).where(Movie.is_active.is_(True)))).scalars():
        found.update(g or [])
    return sorted(found)


@router.get("/cities")
async def cities(db: DB):
    rows = await db.execute(select(Theatre.city, func.count()).group_by(Theatre.city).order_by(Theatre.city))
    return [{"city": c, "theatres": n} for c, n in rows.all()]


@router.get("/theatres")
async def theatres(db: DB, city: str | None = None):
    stmt = select(Theatre).order_by(Theatre.name)
    if city:
        stmt = stmt.where(Theatre.city == city)
    out = []
    for t in (await db.execute(stmt)).scalars().all():
        out.append({"id": t.id, "name": t.name, "city": t.city, "address": t.address, "is_demo": t.is_demo,
                    "amenities": t.amenities, "auditoriums": [{"id": a.id, "name": a.name} for a in t.auditoriums]})
    return out


@router.get("/movies/{key}/showtimes")
async def showtimes(key: str, db: DB, city: str | None = None, day: date | None = Query(default=None, alias="date")):
    movie = await _movie(db, key)
    now = datetime.now(timezone.utc)
    stmt = (select(Show).join(Auditorium).join(Theatre)
            .where(Show.movie_id == movie.id, Show.is_cancelled.is_(False), Show.starts_at > now)
            .order_by(Show.starts_at))
    if city:
        stmt = stmt.where(Theatre.city == city)
    shows = (await db.execute(stmt)).unique().scalars().all()

    dates = sorted({s.starts_at.astimezone(IST).date().isoformat() for s in shows})
    if day:
        lo = datetime.combine(day, time.min, IST)
        shows = [s for s in shows if lo <= s.starts_at < lo + timedelta(days=1)]

    by_theatre: dict[str, dict] = {}
    for s in shows:
        t = s.auditorium.theatre
        entry = by_theatre.setdefault(t.id, {"theatre": {"id": t.id, "name": t.name, "city": t.city,
                                                         "address": t.address, "is_demo": t.is_demo,
                                                         "amenities": t.amenities}, "shows": []})
        entry["shows"].append(show_out(s))
    return {"movie": movie_out(movie), "dates": dates, "theatres": list(by_theatre.values())}


@router.get("/shows/{show_id}")
async def get_show(show_id: str, db: DB):
    s = await db.get(Show, show_id)
    if not s:
        raise not_found("Show")
    t = s.auditorium.theatre
    return {**show_out(s), "movie": movie_out(s.movie, full=True),
            "theatre": {"id": t.id, "name": t.name, "city": t.city, "address": t.address, "is_demo": t.is_demo}}


@router.post("/themes/preview")
async def theme_preview(body: ThemePreviewIn):
    """Public playground: what atmosphere would the engine build for this movie?"""
    return generate_theme(body.model_dump())


@router.post("/themes/preview-art")
async def theme_preview_art(request: Request, file: Annotated[UploadFile, File()]):
    """Public playground: colours of an image. Nothing is stored."""
    await rate_limit(request, "art", get_settings().art_preview_limit_per_10min, 600)
    return {"art_palette": palette_or_400(await read_image(file))}
