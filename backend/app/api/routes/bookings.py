from datetime import timedelta

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import DB, CurrentUser, Holds
from app.api.serializers import booking_out
from app.core.errors import AppError, bad_request, not_found
from app.models import Booking, BookingStatus
from app.schemas.api import BookingIn
from app.services import bookings as svc

router = APIRouter(prefix="/bookings", tags=["bookings"])
CANCEL_CUTOFF = timedelta(hours=2)


async def _own(db, booking_id: str, user) -> Booking:
    b = await db.get(Booking, booking_id)
    if not b or (b.user_id != user.id and not user.is_admin):
        raise not_found("Booking")
    return b


@router.post("", status_code=201)
async def create(body: BookingIn, db: DB, holds: Holds, user: CurrentUser):
    b = await svc.create_booking(db, holds, user.id, body.show_id, body.seat_ids)
    b = await db.get(Booking, b.id)
    return booking_out(b)


@router.get("")
async def mine(db: DB, user: CurrentUser):
    rows = (await db.execute(
        select(Booking).where(Booking.user_id == user.id, Booking.status != BookingStatus.cancelled)
        .order_by(Booking.created_at.desc()).limit(100)
    )).unique().scalars().all()
    return [booking_out(b) for b in rows]


@router.get("/{booking_id}")
async def one(booking_id: str, db: DB, user: CurrentUser):
    return booking_out(await _own(db, booking_id, user))


@router.post("/{booking_id}/cancel")
async def cancel(booking_id: str, db: DB, holds: Holds, user: CurrentUser):
    b = await _own(db, booking_id, user)
    if b.status not in (BookingStatus.pending, BookingStatus.confirmed):
        raise bad_request("not_cancellable", f"Booking is {b.status.value.lower()}")
    if b.status == BookingStatus.confirmed and b.show.starts_at - svc.now_utc() < CANCEL_CUTOFF:
        raise AppError(422, "too_late", "Tickets can be cancelled up to 2 hours before the show")
    await svc.release_booking(db, holds, b.id, BookingStatus.cancelled, "Cancelled by customer")
    return booking_out(await db.get(Booking, b.id, populate_existing=True))
