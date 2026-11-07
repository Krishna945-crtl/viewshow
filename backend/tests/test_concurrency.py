"""The 'two people click F12 at the same instant' tests."""

import asyncio

from sqlalchemy import select

from app.db.session import sessionmaker
from app.models import Booking, BookingSeat, BookingStatus, Show


async def test_thirty_users_race_for_one_seat(client, register, show_id, seats):
    users = [await register(f"racer") for _ in range(30)]
    sid = seats[5]["id"]

    async def grab(h):
        return await client.post(f"/shows/{show_id}/holds", json={"seat_ids": [sid]}, headers=h)

    results = await asyncio.gather(*(grab(h) for h, _ in users))
    codes = sorted(r.status_code for r in results)
    assert codes.count(200) == 1
    assert codes.count(409) == 29


async def test_overlapping_group_holds_never_split_a_seat(client, register, show_id, seats):
    """Users grab overlapping windows of 3. Every seat ends up with at most one owner."""
    users = [await register("grp") for _ in range(8)]
    ids = [s["id"] for s in seats[20:30]]

    async def grab(i, h):
        window = ids[i % 8: i % 8 + 3]
        return await client.post(f"/shows/{show_id}/holds", json={"seat_ids": window}, headers=h)

    results = await asyncio.gather(*(grab(i, h) for i, (h, _) in enumerate(users)))
    held = [r.json()["held"] for r in results if r.status_code == 200]
    flat = [s for group in held for s in group]
    assert len(flat) == len(set(flat))


async def test_database_refuses_double_booking_even_if_redis_is_bypassed(show_id, seats, register):
    """Simulate a bug that skips the hold check: the partial unique index still wins."""
    _, a = await register()
    _, b = await register()
    sid = seats[7]["id"]
    async with sessionmaker()() as db:
        show = await db.get(Show, show_id)
        expires = show.starts_at

    async def insert(uid):
        async with sessionmaker()() as db:
            bk = Booking(reference=uid[:8].upper(), user_id=uid, show_id=show_id, amount_paise=100, expires_at=expires)
            bk.seats = [BookingSeat(show_id=show_id, seat_id=sid, price_paise=100)]
            db.add(bk)
            try:
                await db.commit()
                return True
            except Exception:
                return False

    ok = await asyncio.gather(insert(a["user"]["id"]), insert(b["user"]["id"]))
    assert sorted(ok) == [False, True]
    async with sessionmaker()() as db:
        live = (await db.execute(select(BookingSeat).where(BookingSeat.seat_id == sid,
                                                           BookingSeat.active.is_(True)))).scalars().all()
        assert len(live) == 1


async def test_concurrent_confirm_is_idempotent(client, register, show_id, seats):
    h, _ = await register()
    sid = seats[9]["id"]
    await client.post(f"/shows/{show_id}/holds", json={"seat_ids": [sid]}, headers=h)
    booking = (await client.post("/bookings", json={"show_id": show_id, "seat_ids": [sid]}, headers=h)).json()
    order = (await client.post("/payments/order", json={"booking_id": booking["id"]}, headers=h)).json()
    paid = (await client.post("/payments/mock/checkout", json={"order_id": order["order_id"]}, headers=h)).json()
    body = {"booking_id": booking["id"], **paid}

    results = await asyncio.gather(*(client.post("/payments/verify", json=body, headers=h) for _ in range(5)))
    assert all(r.status_code == 200 for r in results), [r.text for r in results]
    async with sessionmaker()() as db:
        b = await db.get(Booking, booking["id"])
        assert b.status == BookingStatus.confirmed
