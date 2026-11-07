import json
import logging

from fastapi import APIRouter, Header, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import DB, CurrentUser, Holds
from app.api.serializers import booking_out
from app.core.errors import AppError, bad_request, not_found
from app.models import Booking, BookingStatus, Payment, PaymentStatus, WebhookEvent
from app.schemas.api import MockCheckoutIn, OrderIn, VerifyIn
from app.services import bookings as svc
from app.services.payments import MockProvider, ProviderError, get_provider

router = APIRouter(prefix="/payments", tags=["payments"])
log = logging.getLogger("cineverse.payments")


@router.get("/config")
async def config():
    return get_provider().public_config()


@router.post("/order")
async def create_order(body: OrderIn, db: DB, user: CurrentUser):
    b = await db.get(Booking, body.booking_id)
    if not b or b.user_id != user.id:
        raise not_found("Booking")
    if b.status != BookingStatus.pending:
        raise bad_request("not_payable", f"Booking is {b.status.value.lower()}")
    if b.expires_at < svc.now_utc():
        raise AppError(410, "expired", "Payment window closed, please pick seats again")

    # reuse an open order so double-clicking "Pay" doesn't create two
    existing = (await db.execute(select(Payment).where(Payment.booking_id == b.id,
                                                       Payment.status == PaymentStatus.created))).scalars().first()
    provider = get_provider()
    if not existing:
        try:
            order = await provider.create_order(b.amount_paise, b.reference)
        except ProviderError as exc:
            log.error("order create failed: %s", exc)
            raise AppError(502, "provider_error", "Payment provider is unavailable, try again")
        existing = Payment(booking_id=b.id, provider=provider.name, provider_order_id=order["id"],
                           amount_paise=b.amount_paise)
        db.add(existing)
        await db.commit()
    return {"order_id": existing.provider_order_id, "amount_paise": existing.amount_paise, "currency": "INR",
            "booking_reference": b.reference, "expires_at": b.expires_at.isoformat(), **provider.public_config()}


@router.post("/mock/checkout")
async def mock_checkout(body: MockCheckoutIn, db: DB, user: CurrentUser):
    """Sandbox only: stands in for Razorpay's hosted checkout popup."""
    provider = get_provider()
    if not isinstance(provider, MockProvider):
        raise not_found("Endpoint")
    p = (await db.execute(select(Payment).where(Payment.provider_order_id == body.order_id))).scalars().first()
    if not p:
        raise not_found("Order")
    b = await db.get(Booking, p.booking_id)
    if b.user_id != user.id:
        raise not_found("Order")
    if body.outcome == "failure":
        return {"error": {"code": "BAD_REQUEST_ERROR", "description": "Simulated card decline",
                          "metadata": {"order_id": body.order_id}}}
    return provider.checkout(body.order_id)


async def _confirm(db, holds, p: Payment, payment_id: str):
    if p.provider_payment_id and p.provider_payment_id != payment_id:
        raise bad_request("payment_mismatch", "Order already paid with another payment")
    p.provider_payment_id = payment_id
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise bad_request("payment_reused", "Payment id already used")
    return await svc.confirm_booking(db, holds, p.booking_id, p)


@router.post("/verify")
async def verify(body: VerifyIn, db: DB, holds: Holds, user: CurrentUser):
    p = (await db.execute(select(Payment).where(Payment.provider_order_id == body.razorpay_order_id)
                          .with_for_update())).scalars().first()
    if not p or p.booking_id != body.booking_id:
        raise not_found("Order")
    b = await db.get(Booking, p.booking_id)
    if b.user_id != user.id:
        raise not_found("Order")
    if not get_provider().verify_payment(body.razorpay_order_id, body.razorpay_payment_id, body.razorpay_signature):
        p.status = PaymentStatus.failed
        p.failure_reason = "Signature mismatch"
        await db.commit()
        raise AppError(400, "bad_signature", "Payment could not be verified")
    await _confirm(db, holds, p, body.razorpay_payment_id)
    return booking_out(await db.get(Booking, body.booking_id, populate_existing=True))


@router.post("/failed")
async def payment_failed(body: OrderIn, db: DB, holds: Holds, user: CurrentUser):
    """Checkout reported a failure. We keep the booking pending so the user can
    retry until the window closes - just mark the attempt."""
    b = await db.get(Booking, body.booking_id)
    if not b or b.user_id != user.id:
        raise not_found("Booking")
    p = (await db.execute(select(Payment).where(Payment.booking_id == b.id,
                                                Payment.status == PaymentStatus.created))).scalars().first()
    if p:
        p.status = PaymentStatus.failed
        p.failure_reason = "Declined at checkout"
        await db.commit()
    return {"status": b.status.value, "expires_at": b.expires_at.isoformat()}


@router.post("/webhook/razorpay")
async def webhook(request: Request, db: DB, holds: Holds,
                  x_razorpay_signature: str = Header(default=""),
                  x_razorpay_event_id: str = Header(default="")):
    raw = await request.body()
    if not get_provider().verify_webhook(raw, x_razorpay_signature):
        raise AppError(400, "bad_signature", "Invalid webhook signature")
    event = json.loads(raw)
    event_id = x_razorpay_event_id or event.get("id") or ""
    if not event_id:
        raise bad_request("no_event_id", "Missing event id")

    db.add(WebhookEvent(id=event_id, provider="razorpay", event_type=event.get("event", ""), payload=event))
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return {"status": "duplicate"}  # already processed -> idempotent

    entity = (event.get("payload", {}).get("payment") or {}).get("entity") or {}
    order_id, payment_id = entity.get("order_id"), entity.get("id")
    p = (await db.execute(select(Payment).where(Payment.provider_order_id == order_id).with_for_update())).scalars().first()
    if not p:
        return {"status": "ignored"}

    kind = event.get("event")
    if kind in ("payment.captured", "order.paid"):
        try:
            await _confirm(db, holds, p, payment_id)
        except AppError as exc:
            # seats lost etc. - recorded on the payment, still 200 so Razorpay stops retrying
            return {"status": "handled", "note": exc.detail}
    elif kind == "payment.failed":
        if p.status == PaymentStatus.created:
            p.status = PaymentStatus.failed
            p.failure_reason = (entity.get("error_description") or "failed")[:300]
            await db.commit()
    return {"status": "ok"}
