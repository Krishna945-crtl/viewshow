from fastapi import Request

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.redis import get_redis


async def rate_limit(request: Request, bucket: str, limit: int, window_s: int):
    """Fixed-window limiter. Good enough for auth endpoints."""
    if get_settings().env == "test":
        return
    ip = request.client.host if request.client else "unknown"
    key = f"cv:rl:{bucket}:{ip}"
    r = get_redis()
    n = await r.incr(key)
    if n == 1:
        await r.expire(key, window_s)
    if n > limit:
        raise AppError(429, "rate_limited", "Too many attempts, slow down a bit")
