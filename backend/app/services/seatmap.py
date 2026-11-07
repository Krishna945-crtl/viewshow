from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hold_tag
from app.models import Booking, BookingSeat, BookingStatus, Seat, Show
from app.services.holds import HoldStore
from app.services.layout import normalise_layout, layout_summary
from app.services.viewing import view_metrics


async def live_db_seats(db: AsyncSession, show_id: str) -> dict[str, tuple[BookingStatus, str]]:
    rows = await db.execute(
        select(BookingSeat.seat_id, Booking.status, Booking.user_id)
        .join(Booking, Booking.id == BookingSeat.booking_id)
        .where(BookingSeat.show_id == show_id, BookingSeat.active.is_(True))
    )
    return {seat_id: (status, uid) for seat_id, status, uid in rows.all()}


def seat_state(seat: Seat, db_state, hold_owner: str | None) -> tuple[str, str | None]:
    if seat.is_blocked:
        return "blocked", None
    if db_state:
        status, uid = db_state
        if status == BookingStatus.confirmed:
            return "booked", None
        return "held", hold_tag(uid)
    if hold_owner:
        return "held", hold_tag(hold_owner)
    return "available", None


async def build_seat_map(db: AsyncSession, holds: HoldStore, show: Show, user_id: str | None) -> dict:
    seats = (await db.execute(
        select(Seat).where(Seat.auditorium_id == show.auditorium_id).order_by(Seat.grid_row, Seat.grid_col)
    )).scalars().all()
    layout = normalise_layout(show.auditorium.layout)
    prices = {p.category.value: p.price_paise for p in show.prices}
    db_live = await live_db_seats(db, show.id)
    owners = await holds.owners(show.id)
    my_tag = hold_tag(user_id) if user_id else None

    out = []
    for s in seats:
        state, tag = seat_state(s, db_live.get(s.id), owners.get(s.id))
        vm = view_metrics(s.x, s.y, s.z, layout["screen"])
        out.append({
            "id": s.id, "label": s.label, "row": s.row_label, "number": s.number,
            "category": s.category.value, "block": s.block,
            "x": s.x, "y": s.y, "z": s.z, "yaw": s.yaw,
            "col": s.grid_col, "grid_row": s.grid_row, "accessible": s.is_accessible,
            "price_paise": prices.get(s.category.value, 0),
            "state": state, "tag": tag,
            "view": {"score": vm.score, "verdict": vm.verdict, "fov": vm.fov_deg,
                     "off_axis": vm.off_axis_deg, "vertical": vm.vertical_deg, "distance": vm.distance_m},
        })

    deadline = await holds.deadline(show.id, user_id) if user_id else None
    return {
        "show_id": show.id,
        "auditorium": {"id": show.auditorium.id, "name": show.auditorium.name,
                       "dimensions_verified": show.auditorium.dimensions_verified,
                       "screen": layout["screen"], "aisle_width": layout["aisle_width"],
                       **layout_summary(layout)},
        "prices": prices,
        "my_tag": my_tag,
        "hold_deadline_ms": deadline,
        "seats": out,
    }
