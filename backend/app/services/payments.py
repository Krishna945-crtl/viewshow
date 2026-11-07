"""Payment providers. Both speak the same tiny interface so the booking code
never cares which one is live.

`mock` is a local sandbox that mimics Razorpay's signature scheme exactly -
handy for demos/tests without keys. It is never presented as a real payment.
"""

import secrets

import httpx

from app.core.config import get_settings
from app.core.security import hmac_hex, safe_equals


class ProviderError(Exception):
    pass


class MockProvider:
    name = "mock"

    def __init__(self, secret: str):
        self.secret = secret

    async def create_order(self, amount_paise: int, receipt: str) -> dict:
        return {"id": "order_mock_" + secrets.token_hex(8), "amount": amount_paise, "currency": "INR"}

    def sign(self, order_id: str, payment_id: str) -> str:
        return hmac_hex(self.secret, f"{order_id}|{payment_id}")

    def checkout(self, order_id: str) -> dict:
        """What the hosted checkout would hand back to the browser."""
        pid = "pay_mock_" + secrets.token_hex(8)
        return {"razorpay_order_id": order_id, "razorpay_payment_id": pid,
                "razorpay_signature": self.sign(order_id, pid)}

    def verify_payment(self, order_id: str, payment_id: str, signature: str) -> bool:
        return safe_equals(self.sign(order_id, payment_id), signature or "")

    def verify_webhook(self, body: bytes, signature: str) -> bool:
        return safe_equals(hmac_hex(self.secret, body.decode()), signature or "")

    def public_config(self) -> dict:
        return {"provider": "mock", "key_id": None, "sandbox": True}


class RazorpayProvider:
    name = "razorpay"
    base = "https://api.razorpay.com/v1"

    def __init__(self, key_id: str, key_secret: str, webhook_secret: str):
        if not key_id or not key_secret:
            raise ProviderError("razorpay keys missing (CV_RAZORPAY_KEY_ID / CV_RAZORPAY_KEY_SECRET)")
        self.key_id, self.key_secret, self.webhook_secret = key_id, key_secret, webhook_secret

    async def create_order(self, amount_paise: int, receipt: str) -> dict:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(f"{self.base}/orders", auth=(self.key_id, self.key_secret),
                             json={"amount": amount_paise, "currency": "INR", "receipt": receipt})
        if r.status_code >= 300:
            raise ProviderError(f"razorpay order failed: {r.status_code} {r.text[:200]}")
        return r.json()

    def verify_payment(self, order_id: str, payment_id: str, signature: str) -> bool:
        return safe_equals(hmac_hex(self.key_secret, f"{order_id}|{payment_id}"), signature or "")

    def verify_webhook(self, body: bytes, signature: str) -> bool:
        if not self.webhook_secret:
            return False
        return safe_equals(hmac_hex(self.webhook_secret, body.decode()), signature or "")

    def public_config(self) -> dict:
        # key_id is meant to be public; only the secret stays on the server
        return {"provider": "razorpay", "key_id": self.key_id, "sandbox": self.key_id.startswith("rzp_test")}


_provider = None


def get_provider():
    global _provider
    if _provider is None:
        s = get_settings()
        if s.payment_provider == "razorpay":
            _provider = RazorpayProvider(s.razorpay_key_id, s.razorpay_key_secret, s.razorpay_webhook_secret)
        else:
            _provider = MockProvider(s.mock_payment_secret)
    return _provider


def reset_provider():
    global _provider
    _provider = None
