import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update

from app.core.config import get_settings
from app.core.redis import get_redis
from app.core.security import hmac_hex
from app.db.session import sessionmaker
from app.models import Booking, BookingStatus, Payment, PaymentStatus
from app.services.bookings import expire_due
from app.services.holds import HoldStore


async def _book(client, h, show_id, ids):
    r = await client.post(f"/shows/{show_id}/holds", json={"seat_ids": ids}, headers=h)
    assert r.status_code == 200, r.text
    r = await client.post("/bookings", json={"show_id": show_id, "seat_ids": ids}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


async def _pay(client, h, booking_id, outcome="success"):
    order = (await client.post("/payments/order", json={"booking_id": booking_id}, headers=h)).json()
    return order, (await client.post("/payments/mock/checkout", json={"order_id": order["order_id"],
                                                                      "outcome": outcome}, headers=h)).json()


async def test_happy_path_end_to_end(client, register, show_id, seats):
    h, _ = await register("happy")
    ids = [seats[0]["id"], seats[1]["id"]]
    b = await _book(client, h, show_id, ids)
    assert b["status"] == "PENDING_PAYMENT"
    expected = sum(s["price_paise"] for s in seats[:2]) + 2 * 2500
    assert b["amount_paise"] == expected

    order, paid = await _pay(client, h, b["id"])
    assert order["provider"] == "mock" and order["sandbox"] is True
    r = await client.post("/payments/verify", json={"booking_id": b["id"], **paid}, headers=h)
    assert r.status_code == 200, r.text
    done = r.json()
    assert done["status"] == "CONFIRMED"
    assert done["ticket_payload"].startswith("CV3D|" + done["reference"])

    m = (await client.get(f"/shows/{show_id}/seats")).json()
    states = {s["id"]: s["state"] for s in m["seats"]}
    assert states[ids[0]] == states[ids[1]] == "booked"

    hist = (await client.get("/bookings", headers=h)).json()
    assert hist[0]["id"] == b["id"]


async def test_booking_requires_a_live_hold(client, register, show_id, seats):
    h, _ = await register()
    r = await client.post("/bookings", json={"show_id": show_id, "seat_ids": [seats[0]["id"]]}, headers=h)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "hold_missing"


async def test_booked_seat_cannot_be_held_again(client, register, show_id, seats):
    a, _ = await register()
    b, _ = await register()
    sid = seats[3]["id"]
    bk = await _book(client, a, show_id, [sid])
    # a's redis hold ends, but the pending booking still owns the seat
    await HoldStore(get_redis()).release_all(show_id, (await client.get("/auth/me", headers=a)).json()["id"])
    r = await client.post(f"/shows/{show_id}/holds", json={"seat_ids": [sid]}, headers=b)
    assert r.status_code == 409
    assert bk["status"] == "PENDING_PAYMENT"


async def test_bad_signature_is_rejected(client, register, show_id, seats):
    h, _ = await register()
    b = await _book(client, h, show_id, [seats[4]["id"]])
    _, paid = await _pay(client, h, b["id"])
    paid["razorpay_signature"] = "0" * 64
    r = await client.post("/payments/verify", json={"booking_id": b["id"], **paid}, headers=h)
    assert r.status_code == 400
    assert (await client.get(f"/bookings/{b['id']}", headers=h)).json()["status"] == "PENDING_PAYMENT"


async def test_failed_payment_keeps_booking_retryable(client, register, show_id, seats):
    h, _ = await register()
    b = await _book(client, h, show_id, [seats[5]["id"]])
    _, fail = await _pay(client, h, b["id"], outcome="failure")
    assert "error" in fail
    r = await client.post("/payments/failed", json={"booking_id": b["id"]}, headers=h)
    assert r.json()["status"] == "PENDING_PAYMENT"
    # retry with a fresh order works
    _, paid = await _pay(client, h, b["id"])
    r = await client.post("/payments/verify", json={"booking_id": b["id"], **paid}, headers=h)
    assert r.json()["status"] == "CONFIRMED"


async def test_order_is_reused_on_double_click(client, register, show_id, seats):
    h, _ = await register()
    b = await _book(client, h, show_id, [seats[6]["id"]])
    o1 = (await client.post("/payments/order", json={"booking_id": b["id"]}, headers=h)).json()
    o2 = (await client.post("/payments/order", json={"booking_id": b["id"]}, headers=h)).json()
    assert o1["order_id"] == o2["order_id"]


def _webhook(order_id, payment_id, event="payment.captured", event_id="evt_1"):
    body = json.dumps({"id": event_id, "event": event,
                       "payload": {"payment": {"entity": {"id": payment_id, "order_id": order_id}}}})
    sig = hmac_hex(get_settings().mock_payment_secret, body)
    return body, {"x-razorpay-signature": sig, "x-razorpay-event-id": event_id, "content-type": "application/json"}


async def test_webhook_confirms_and_is_idempotent(client, register, show_id, seats):
    h, _ = await register()
    b = await _book(client, h, show_id, [seats[7]["id"]])
    order, _ = await _pay(client, h, b["id"])
    body, headers = _webhook(order["order_id"], "pay_hook_1", event_id="evt_abc")
    r1 = await client.post("/payments/webhook/razorpay", content=body, headers=headers)
    r2 = await client.post("/payments/webhook/razorpay", content=body, headers=headers)
    assert r1.json()["status"] == "ok" and r2.json()["status"] == "duplicate"
    assert (await client.get(f"/bookings/{b['id']}", headers=h)).json()["status"] == "CONFIRMED"


async def test_webhook_with_bad_signature(client):
    body, headers = _webhook("order_x", "pay_x")
    headers["x-razorpay-signature"] = "nope"
    assert (await client.post("/payments/webhook/razorpay", content=body, headers=headers)).status_code == 400


async def _force_expire(booking_id):
    async with sessionmaker()() as db:
        await db.execute(update(Booking).where(Booking.id == booking_id)
                         .values(expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)))
        await db.commit()
        n = await expire_due(db, HoldStore(get_redis()))
    return n


async def test_abandoned_booking_expires_and_frees_seats(client, register, show_id, seats):
    h, me = await register()
    sid = seats[8]["id"]
    b = await _book(client, h, show_id, [sid])
    await HoldStore(get_redis()).release_all(show_id, me["user"]["id"])
    assert await _force_expire(b["id"]) == 1
    assert (await client.get(f"/bookings/{b['id']}", headers=h)).json()["status"] == "EXPIRED"
    other, _ = await register()
    assert (await client.post(f"/shows/{show_id}/holds", json={"seat_ids": [sid]}, headers=other)).status_code == 200


async def test_late_payment_reclaims_free_seats(client, register, show_id, seats):
    h, me = await register()
    b = await _book(client, h, show_id, [seats[9]["id"]])
    order, paid = await _pay(client, h, b["id"])
    await _force_expire(b["id"])
    r = await client.post("/payments/verify", json={"booking_id": b["id"], **paid}, headers=h)
    assert r.status_code == 200 and r.json()["status"] == "CONFIRMED"


async def test_late_payment_after_seat_resold_flags_refund(client, register, show_id, seats):
    h, me = await register()
    sid = seats[10]["id"]
    b = await _book(client, h, show_id, [sid])
    order, paid = await _pay(client, h, b["id"])
    await HoldStore(get_redis()).release_all(show_id, me["user"]["id"])
    await _force_expire(b["id"])
    other, _ = await register()
    await _book(client, other, show_id, [sid])  # seat resold

    r = await client.post("/payments/verify", json={"booking_id": b["id"], **paid}, headers=h)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "seats_lost"
    async with sessionmaker()() as db:
        p = (await db.execute(select(Payment).where(Payment.booking_id == b["id"]))).scalars().first()
        assert p.status == PaymentStatus.refund_pending
        assert (await db.get(Booking, b["id"])).status == BookingStatus.expired


async def test_user_cancel_frees_seats_and_flags_refund(client, register, show_id, seats):
    h, _ = await register()
    sid = seats[11]["id"]
    b = await _book(client, h, show_id, [sid])
    _, paid = await _pay(client, h, b["id"])
    await client.post("/payments/verify", json={"booking_id": b["id"], **paid}, headers=h)
    r = await client.post(f"/bookings/{b['id']}/cancel", headers=h)
    assert r.status_code == 200 and r.json()["status"] == "CANCELLED"
    m = (await client.get(f"/shows/{show_id}/seats")).json()
    assert next(s for s in m["seats"] if s["id"] == sid)["state"] == "available"


async def test_cannot_see_other_users_booking(client, register, show_id, seats):
    a, _ = await register()
    b, _ = await register()
    bk = await _book(client, a, show_id, [seats[12]["id"]])
    assert (await client.get(f"/bookings/{bk['id']}", headers=b)).status_code == 404
    assert (await client.post("/payments/order", json={"booking_id": bk["id"]}, headers=b)).status_code == 404


async def test_ticket_check_in(client, register, show_id, seats):
    h, _ = await register()
    admin, _ = await register(admin=True)
    b = await _book(client, h, show_id, [seats[13]["id"]])
    _, paid = await _pay(client, h, b["id"])
    t = (await client.post("/payments/verify", json={"booking_id": b["id"], **paid}, headers=h)).json()
    r1 = await client.post("/admin/tickets/check-in", json={"payload": t["ticket_payload"]}, headers=admin)
    r2 = await client.post("/admin/tickets/check-in", json={"payload": t["ticket_payload"]}, headers=admin)
    assert r1.json()["first_scan"] is True and r2.json()["first_scan"] is False
    forged = t["ticket_payload"][:-4] + "abcd"
    assert (await client.post("/admin/tickets/check-in", json={"payload": forged}, headers=admin)).status_code == 400
