"""
Shared SlowAPI rate limiter.
Uses Redis storage when REDIS_URL is configured (production / multi-worker).
Falls back to in-memory storage for local dev.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings


def _make_limiter() -> Limiter:
    if settings.redis_url:
        return Limiter(
            key_func=get_remote_address,
            storage_uri=settings.redis_url,
        )
    return Limiter(key_func=get_remote_address)


limiter = _make_limiter()
