"""Booking lifecycle. The rules that matter:

* seats go into a booking only if the caller *currently* holds them in Redis
* the partial unique index on booking_seats(show_id, seat_id) WHERE active is the
  last line of defence - two live bookings can never share a seat
* confirm is idempotent; a late payment for an expired booking re-claims the
  seats if still free, otherwise the payment is flagged for refund
"""

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import bad_request, conflict, not_found
from app.models import Booking, BookingSeat, BookingStatus, Payment, PaymentStatus, Seat, Show
from app.services.events import publish_seats
from app.services.holds import HoldStore

FEE_PER_SEAT = 2500  # Rs 25 convenience fee, in paise
REF_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def new_reference() -> str:
    return "".join(secrets.choice(REF_ALPHABET) for _ in range(8))


async def create_booking(db: AsyncSession, holds: HoldStore, user_id: str, show_id: str, seat_ids: list[str]) -> Booking:
    seat_ids = list(dict.fromkeys(seat_ids))  # dedupe, keep order
    s = get_settings()
    if not seat_ids:
        raise bad_request("no_seats", "Pick at least one seat")
    if len(seat_ids) > s.max_seats_per_booking:
        raise bad_request("too_many", f"Max {s.max_seats_per_booking} seats per booking")

    show = await db.get(Show, show_id)
    if not show or show.is_cancelled:
        raise not_found("Show")
    if show.starts_at <= now_utc():
        raise bad_request("show_started", "This show has already started")

    held = set(await holds.user_holds(show_id, user_id))
    missing = [sid for sid in seat_ids if sid not in held]
    if missing:
        raise conflict("hold_missing", "Your hold on some seats expired. Please pick them again.", seat_ids=missing)

    seats = (await db.execute(select(Seat).where(Seat.id.in_(seat_ids)))).scalars().all()
    if len(seats) != len(seat_ids) or any(x.auditorium_id != show.auditorium_id or x.is_blocked for x in seats):
        raise bad_request("bad_seats", "Some seats are not part of this show")

    prices = {p.category: p.price_paise for p in show.prices}
    deadline = await holds.deadline(show_id, user_id)
    expires = now_utc() + timedelta(seconds=s.payment_window_seconds)
    if deadline:
        expires = max(expires, datetime.fromtimestamp(deadline / 1000, timezone.utc))

    # one pending booking per user per show: an older one gets replaced
    await _drop_user_pending(db, user_id, show_id)

    booking = Booking(
        reference=new_reference(), user_id=user_id, show_id=show_id,
        amount_paise=sum(prices.get(x.category, 0) for x in seats) + FEE_PER_SEAT * len(seats),
        convenience_fee_paise=FEE_PER_SEAT * len(seats), expires_at=expires,
    )
    booking.seats = [BookingSeat(show_id=show_id, seat_id=x.id, price_paise=prices.get(x.category, 0)) for x in seats]
    db.add(booking)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise conflict("seat_taken", "Someone just grabbed one of those seats")
    await db.refresh(booking)
    return booking


async def _drop_user_pending(db: AsyncSession, user_id: str, show_id: str):
    old = (await db.execute(
        select(Booking).where(Booking.user_id == user_id, Booking.show_id == show_id,
                              Booking.status == BookingStatus.pending).with_for_update(of=Booking)
    )).scalars().all()
    for b in old:
        b.status = BookingStatus.cancelled
        b.cancelled_at = now_utc()
        await db.execute(update(BookingSeat).where(BookingSeat.booking_id == b.id).values(active=False))
    if old:
        await db.flush()


async def _lock(db: AsyncSession, booking_id: str) -> Booking:
    b = (await db.execute(select(Booking).where(Booking.id == booking_id).with_for_update(of=Booking))).scalars().first()
    if not b:
        raise not_found("Booking")
    return b


async def confirm_booking(db: AsyncSession, holds: HoldStore, booking_id: str, payment: Payment) -> Booking:
    """Called after a verified payment (client callback OR webhook - whichever is first)."""
    b = await _lock(db, booking_id)
    if b.status == BookingStatus.confirmed:
        await db.commit()
        return b  # idempotent

    if b.status != BookingStatus.pending:
        # late payment: try to re-claim the seats
        ok = await _reactivate(db, b)
        if not ok:
            payment.status = PaymentStatus.refund_pending
            payment.failure_reason = "Seats were released before payment completed"
            await db.commit()
            raise conflict("seats_lost", "Payment received but the seats were released. A refund has been initiated.")

    b.status = BookingStatus.confirmed
    b.confirmed_at = now_utc()
    payment.status = PaymentStatus.captured
    await db.commit()
    seat_ids = [x.seat_id for x in b.seats]
    await holds.release(b.show_id, b.user_id, seat_ids)
    await publish_seats(b.show_id, [{"seat_id": sid, "state": "booked"} for sid in seat_ids])
    return b


async def _reactivate(db: AsyncSession, b: Booking) -> bool:
    try:
        async with db.begin_nested():
            await db.execute(update(BookingSeat).where(BookingSeat.booking_id == b.id).values(active=True))
    except IntegrityError:
        return False
    return True


async def release_booking(db: AsyncSession, holds: HoldStore, booking_id: str, status: BookingStatus,
                          reason: str | None = None) -> Booking:
    """Fail / cancel / expire: seats go back on sale."""
    b = await _lock(db, booking_id)
    if b.status not in (BookingStatus.pending, BookingStatus.confirmed):
        await db.commit()
        return b
    was_confirmed = b.status == BookingStatus.confirmed
    b.status = status
    if status == BookingStatus.cancelled:
        b.cancelled_at = now_utc()
    await db.execute(update(BookingSeat).where(BookingSeat.booking_id == b.id).values(active=False))
    if was_confirmed:
        pays = (await db.execute(select(Payment).where(Payment.booking_id == b.id,
                                                       Payment.status == PaymentStatus.captured))).scalars().all()
        for p in pays:
            p.status = PaymentStatus.refund_pending
            p.failure_reason = reason or "Booking cancelled"
    await db.commit()
    seat_ids = [x.seat_id for x in b.seats]
    await holds.release(b.show_id, b.user_id, seat_ids)
    await publish_seats(b.show_id, [{"seat_id": sid, "state": "available"} for sid in seat_ids])
    return b


async def expire_due(db: AsyncSession, holds: HoldStore, limit: int = 100) -> int:
    rows = (await db.execute(
        select(Booking.id).where(Booking.status == BookingStatus.pending, Booking.expires_at < now_utc())
        .limit(limit).with_for_update(skip_locked=True, of=Booking)
    )).scalars().all()
    await db.commit()
    for bid in rows:
        await release_booking(db, holds, bid, BookingStatus.expired)
    return len(rows)
