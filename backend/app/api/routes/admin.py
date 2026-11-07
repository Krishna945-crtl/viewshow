import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter
from sqlalchemy import delete, func, select

from app.api.deps import DB, AdminUser, Holds
from app.api.serializers import booking_out, movie_out, show_out
from app.core.errors import AppError, bad_request, conflict, not_found
from app.core.security import safe_equals, ticket_signature
from app.models import (Auditorium, Booking, BookingSeat, BookingStatus, ErrorLog, Movie, MovieTheme, Payment,
                        PaymentStatus, Seat, SeatCategory, Show, ShowPrice, Theatre)
from app.schemas.api import AuditoriumIn, MovieIn, ShowIn, TheatreIn, ThemeIn, ThemePreviewIn, TicketCheckIn
from app.services import bookings as svc
from app.services.layout import LayoutError, build_seats, layout_summary, normalise_layout
from app.services.theme_engine import generate_theme, guard

router = APIRouter(prefix="/admin", tags=["admin"])


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:120] or "movie"


# ---- movies ------------------------------------------------------------------

@router.get("/movies")
async def all_movies(db: DB, _: AdminUser):
    rows = (await db.execute(select(Movie).order_by(Movie.title))).unique().scalars().all()
    return [movie_out(m, full=True) for m in rows]


@router.post("/movies", status_code=201)
async def create_movie(body: MovieIn, db: DB, _: AdminUser):
    data = body.model_dump()
    data["slug"] = data["slug"] or slugify(body.title)
    if (await db.execute(select(Movie.id).where(Movie.slug == data["slug"]))).first():
        raise conflict("slug_taken", "A movie with this slug exists")
    if data["theme_id"] and not await db.get(MovieTheme, data["theme_id"]):
        raise bad_request("bad_theme", "Theme not found")
    m = Movie(**data)
    db.add(m)
    await db.commit()
    return movie_out(await db.get(Movie, m.id), full=True)


@router.put("/movies/{movie_id}")
async def update_movie(movie_id: str, body: MovieIn, db: DB, _: AdminUser):
    m = await db.get(Movie, movie_id)
    if not m:
        raise not_found("Movie")
    data = body.model_dump()
    data["slug"] = data["slug"] or m.slug
    if data["theme_id"] and not await db.get(MovieTheme, data["theme_id"]):
        raise bad_request("bad_theme", "Theme not found")
    for k, v in data.items():
        setattr(m, k, v)
    await db.commit()
    return movie_out(await db.get(Movie, movie_id, populate_existing=True), full=True)


@router.delete("/movies/{movie_id}", status_code=204)
async def archive_movie(movie_id: str, db: DB, _: AdminUser):
    m = await db.get(Movie, movie_id)
    if not m:
        raise not_found("Movie")
    m.is_active = False  # soft delete, bookings keep pointing at it
    await db.commit()


# ---- themes ------------------------------------------------------------------

@router.get("/themes")
async def themes(db: DB, _: AdminUser):
    rows = (await db.execute(select(MovieTheme).order_by(MovieTheme.name))).scalars().all()
    return [{"id": t.id, "name": t.name, "config": guard(t.config)} for t in rows]


@router.post("/themes", status_code=201)
async def create_theme(body: ThemeIn, db: DB, _: AdminUser):
    if (await db.execute(select(MovieTheme.id).where(MovieTheme.name == body.name))).first():
        raise conflict("name_taken", "Theme name already used")
    t = MovieTheme(name=body.name, config=guard({**body.config, "name": body.name}))
    db.add(t)
    await db.commit()
    return {"id": t.id, "name": t.name, "config": t.config}


@router.put("/themes/{theme_id}")
async def update_theme(theme_id: str, body: ThemeIn, db: DB, _: AdminUser):
    t = await db.get(MovieTheme, theme_id)
    if not t:
        raise not_found("Theme")
    t.name, t.config = body.name, guard({**body.config, "name": body.name})
    await db.commit()
    return {"id": t.id, "name": t.name, "config": t.config}


@router.delete("/themes/{theme_id}", status_code=204)
async def delete_theme(theme_id: str, db: DB, _: AdminUser):
    t = await db.get(MovieTheme, theme_id)
    if t:
        await db.delete(t)
        await db.commit()


@router.post("/themes/preview")
async def preview_theme(body: ThemePreviewIn, _: AdminUser):
    """'What would the auto engine do with this movie?' - used by the theme editor."""
    return generate_theme(body.model_dump())


# ---- theatres / auditoriums --------------------------------------------------

@router.post("/theatres", status_code=201)
async def create_theatre(body: TheatreIn, db: DB, _: AdminUser):
    t = Theatre(**body.model_dump(), is_demo=True)
    db.add(t)
    await db.commit()
    return {"id": t.id, **body.model_dump()}


@router.put("/theatres/{theatre_id}")
async def update_theatre(theatre_id: str, body: TheatreIn, db: DB, _: AdminUser):
    t = await db.get(Theatre, theatre_id)
    if not t:
        raise not_found("Theatre")
    for k, v in body.model_dump().items():
        setattr(t, k, v)
    await db.commit()
    return {"id": t.id, **body.model_dump()}


@router.get("/auditoriums/{aud_id}")
async def get_auditorium(aud_id: str, db: DB, _: AdminUser):
    a = await db.get(Auditorium, aud_id)
    if not a:
        raise not_found("Auditorium")
    return {"id": a.id, "name": a.name, "theatre_id": a.theatre_id, "layout": a.layout,
            "dimensions_verified": a.dimensions_verified, "summary": layout_summary(a.layout)}


@router.post("/layouts/validate")
async def validate_layout(body: AuditoriumIn, _: AdminUser):
    try:
        seats = build_seats(body.layout)
    except LayoutError as exc:
        raise bad_request("bad_layout", str(exc))
    return {"summary": layout_summary(body.layout),
            "seats": [{"label": s.label, "category": s.category.value, "x": s.x, "y": s.y, "z": s.z,
                       "col": s.grid_col, "grid_row": s.grid_row, "blocked": s.is_blocked} for s in seats]}


async def _write_seats(db, aud: Auditorium):
    await db.execute(delete(Seat).where(Seat.auditorium_id == aud.id))
    for s in build_seats(aud.layout):
        db.add(Seat(auditorium_id=aud.id, row_label=s.row_label, number=s.number, label=s.label,
                    category=s.category, block=s.block, x=s.x, y=s.y, z=s.z, yaw=s.yaw, grid_col=s.grid_col,
                    grid_row=s.grid_row, is_blocked=s.is_blocked, is_accessible=s.is_accessible))


@router.post("/theatres/{theatre_id}/auditoriums", status_code=201)
async def create_auditorium(theatre_id: str, body: AuditoriumIn, db: DB, _: AdminUser):
    if not await db.get(Theatre, theatre_id):
        raise not_found("Theatre")
    try:
        layout = normalise_layout(body.layout)
    except LayoutError as exc:
        raise bad_request("bad_layout", str(exc))
    a = Auditorium(theatre_id=theatre_id, name=body.name, layout=layout, dimensions_verified=body.dimensions_verified)
    db.add(a)
    await db.flush()
    await _write_seats(db, a)
    await db.commit()
    return {"id": a.id, "name": a.name, "summary": layout_summary(layout)}


@router.put("/auditoriums/{aud_id}")
async def update_auditorium(aud_id: str, body: AuditoriumIn, db: DB, _: AdminUser):
    a = await db.get(Auditorium, aud_id)
    if not a:
        raise not_found("Auditorium")
    try:
        layout = normalise_layout(body.layout)
    except LayoutError as exc:
        raise bad_request("bad_layout", str(exc))
    # re-generating seats would orphan existing tickets - refuse if anything was ever booked here
    used = (await db.execute(select(func.count()).select_from(BookingSeat).join(Seat)
                             .where(Seat.auditorium_id == aud_id))).scalar_one()
    if used and layout != a.layout:
        raise conflict("layout_in_use", "Seats here have bookings; create a new auditorium instead")
    a.name, a.layout, a.dimensions_verified = body.name, layout, body.dimensions_verified
    await _write_seats(db, a)
    await db.commit()
    return {"id": a.id, "name": a.name, "summary": layout_summary(layout)}


# ---- shows -------------------------------------------------------------------

@router.get("/shows")
async def list_shows(db: DB, _: AdminUser, movie_id: str | None = None):
    stmt = select(Show).where(Show.starts_at > datetime.now(timezone.utc) - timedelta(days=1)).order_by(Show.starts_at)
    if movie_id:
        stmt = stmt.where(Show.movie_id == movie_id)
    rows = (await db.execute(stmt.limit(500))).unique().scalars().all()
    return [{**show_out(s), "movie_title": s.movie.title, "theatre": s.auditorium.theatre.name} for s in rows]


@router.post("/shows", status_code=201)
async def create_show(body: ShowIn, db: DB, _: AdminUser):
    movie = await db.get(Movie, body.movie_id)
    aud = await db.get(Auditorium, body.auditorium_id)
    if not movie or not aud:
        raise bad_request("bad_refs", "Movie or auditorium not found")
    start = body.starts_at if body.starts_at.tzinfo else body.starts_at.replace(tzinfo=timezone.utc)
    end = start + timedelta(minutes=movie.runtime_minutes + 20)
    # overlap check: same auditorium can't run two shows at once
    clash = (await db.execute(
        select(Show).where(Show.auditorium_id == aud.id, Show.is_cancelled.is_(False),
                           Show.starts_at < end, Show.starts_at > start - timedelta(hours=4))
    )).unique().scalars().all()
    for c in clash:
        if c.starts_at + timedelta(minutes=c.movie.runtime_minutes + 20) > start:
            raise conflict("overlap", f"Overlaps with {c.movie.title} at {c.starts_at.isoformat()}")
    s = Show(movie_id=movie.id, auditorium_id=aud.id, starts_at=start, format=body.format, language=body.language)
    s.prices = [ShowPrice(category=SeatCategory(k), price_paise=v) for k, v in body.prices.items()]
    db.add(s)
    await db.commit()
    return show_out(await db.get(Show, s.id))


@router.post("/shows/{show_id}/cancel")
async def cancel_show(show_id: str, db: DB, holds: Holds, _: AdminUser):
    s = await db.get(Show, show_id)
    if not s:
        raise not_found("Show")
    s.is_cancelled = True
    await db.commit()
    ids = (await db.execute(select(Booking.id).where(Booking.show_id == show_id, Booking.status.in_(
        [BookingStatus.pending, BookingStatus.confirmed])))).scalars().all()
    for bid in ids:
        await svc.release_booking(db, holds, bid, BookingStatus.cancelled, "Show cancelled by cinema")
    return {"cancelled_bookings": len(ids)}


# ---- bookings / ops ----------------------------------------------------------

@router.get("/bookings")
async def bookings(db: DB, _: AdminUser, status: str | None = None, q: str | None = None):
    stmt = select(Booking).order_by(Booking.created_at.desc()).limit(200)
    if status:
        stmt = stmt.where(Booking.status == BookingStatus(status))
    if q:
        stmt = stmt.where(Booking.reference == q.strip().upper())
    return [booking_out(b, with_ticket=False) for b in (await db.execute(stmt)).unique().scalars().all()]


@router.post("/bookings/{booking_id}/cancel")
async def admin_cancel(booking_id: str, db: DB, holds: Holds, _: AdminUser):
    b = await db.get(Booking, booking_id)
    if not b:
        raise not_found("Booking")
    await svc.release_booking(db, holds, b.id, BookingStatus.cancelled, "Cancelled by admin")
    return booking_out(await db.get(Booking, booking_id, populate_existing=True), with_ticket=False)


@router.post("/tickets/check-in")
async def check_in(body: TicketCheckIn, db: DB, _: AdminUser):
    parts = body.payload.split("|")
    if len(parts) != 3 or parts[0] != "CV3D" or not safe_equals(ticket_signature(parts[1]), parts[2]):
        raise AppError(400, "bad_ticket", "Ticket signature is invalid")
    b = (await db.execute(select(Booking).where(Booking.reference == parts[1]))).unique().scalars().first()
    if not b or b.status != BookingStatus.confirmed:
        raise AppError(400, "bad_ticket", "Ticket is not valid")
    first = b.checked_in_at is None
    if first:
        b.checked_in_at = datetime.now(timezone.utc)
        await db.commit()
    return {"ok": True, "first_scan": first, "booking": booking_out(b, with_ticket=False)}


@router.get("/stats")
async def stats(db: DB, _: AdminUser):
    now = datetime.now(timezone.utc)
    confirmed = BookingStatus.confirmed
    revenue = (await db.execute(select(func.coalesce(func.sum(Booking.amount_paise), 0))
                                .where(Booking.status == confirmed))).scalar_one()
    by_status = dict((await db.execute(select(Booking.status, func.count()).group_by(Booking.status))).all())
    tickets = (await db.execute(select(func.count()).select_from(BookingSeat).where(BookingSeat.active.is_(True))
                                .join(Booking).where(Booking.status == confirmed))).scalar_one()
    refunds = (await db.execute(select(func.count()).select_from(Payment)
                                .where(Payment.status == PaymentStatus.refund_pending))).scalar_one()

    # occupancy for upcoming shows (top 15 by fill)
    seat_counts = dict((await db.execute(select(Seat.auditorium_id, func.count()).where(Seat.is_blocked.is_(False))
                                         .group_by(Seat.auditorium_id))).all())
    sold = dict((await db.execute(
        select(BookingSeat.show_id, func.count()).join(Booking)
        .where(BookingSeat.active.is_(True), Booking.status == confirmed).group_by(BookingSeat.show_id)
    )).all())
    upcoming = (await db.execute(select(Show).where(Show.starts_at > now, Show.is_cancelled.is_(False))
                                 .order_by(Show.starts_at).limit(300))).unique().scalars().all()
    occ = []
    for s in upcoming:
        cap = seat_counts.get(s.auditorium_id, 0) or 1
        occ.append({"show_id": s.id, "movie": s.movie.title, "theatre": s.auditorium.theatre.name,
                    "starts_at": s.starts_at.isoformat(), "sold": sold.get(s.id, 0), "capacity": cap,
                    "occupancy": round(sold.get(s.id, 0) / cap, 3)})
    occ.sort(key=lambda o: -o["occupancy"])

    per_movie: dict[str, int] = {}
    rows = await db.execute(select(Movie.title, func.sum(Booking.amount_paise)).join(Show, Show.movie_id == Movie.id)
                            .join(Booking, Booking.show_id == Show.id).where(Booking.status == confirmed)
                            .group_by(Movie.title))
    for title, amt in rows.all():
        per_movie[title] = int(amt or 0)

    errors_24h = (await db.execute(select(func.count()).select_from(ErrorLog)
                                   .where(ErrorLog.created_at > now - timedelta(days=1)))).scalar_one()
    return {
        "revenue_paise": int(revenue), "tickets_sold": tickets, "refunds_pending": refunds,
        "bookings_by_status": {k.value: v for k, v in by_status.items()},
        "upcoming_shows": len(upcoming),
        "occupancy": occ[:15],
        "revenue_by_movie": sorted(({"movie": k, "revenue_paise": v} for k, v in per_movie.items()),
                                   key=lambda r: -r["revenue_paise"]),
        "errors_24h": errors_24h,
    }


@router.get("/errors")
async def errors(db: DB, _: AdminUser):
    rows = (await db.execute(select(ErrorLog).order_by(ErrorLog.id.desc()).limit(100))).scalars().all()
    return [{"id": e.id, "at": e.created_at.isoformat(), "path": e.path, "method": e.method,
             "type": e.error_type, "message": e.message[:500], "request_id": e.request_id} for e in rows]
