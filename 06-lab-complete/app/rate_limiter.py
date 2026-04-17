"""
Rate Limiter Module — Sliding Window Counter

Limits the number of requests per user within a time window.
In production: replace with Redis-based rate limiter for horizontal scaling.

Algorithm: Sliding Window Counter
  - Each user has a bucket (deque of timestamps)
  - Remove timestamps older than the window
  - If count >= limit → raise 429 Too Many Requests

Usage:
    from app.rate_limiter import check_rate_limit
    check_rate_limit(user_key)  # raises 429 if exceeded
"""
import time
import logging
from collections import defaultdict, deque
from fastapi import HTTPException

from app.config import settings

logger = logging.getLogger(__name__)

# Per-user sliding windows: key → deque of timestamps
_rate_windows: dict[str, deque] = defaultdict(deque)


def check_rate_limit(key: str) -> dict:
    """
    Check if user has exceeded rate limit.

    Args:
        key: Identifier for rate limiting (API key prefix, user_id, etc.)

    Returns:
        dict with limit info (limit, remaining, reset_at)

    Raises:
        HTTPException(429) if rate limit exceeded.
    """
    now = time.time()
    window = _rate_windows[key]

    # Remove timestamps outside the window (older than 60 seconds)
    while window and window[0] < now - 60:
        window.popleft()

    remaining = settings.rate_limit_per_minute - len(window)
    reset_at = int(now) + 60

    if len(window) >= settings.rate_limit_per_minute:
        oldest = window[0]
        retry_after = int(oldest + 60 - now) + 1
        logger.warning(f"Rate limit exceeded for key={key[:8]}...")
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "limit": settings.rate_limit_per_minute,
                "window_seconds": 60,
                "retry_after_seconds": retry_after,
            },
            headers={
                "X-RateLimit-Limit": str(settings.rate_limit_per_minute),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset_at),
                "Retry-After": str(retry_after),
            },
        )

    # Record this request
    window.append(now)

    return {
        "limit": settings.rate_limit_per_minute,
        "remaining": remaining - 1,
        "reset_at": reset_at,
    }


def get_stats(key: str) -> dict:
    """Get rate limit stats for a key without recording a request."""
    now = time.time()
    window = _rate_windows[key]
    active = sum(1 for t in window if t >= now - 60)
    return {
        "requests_in_window": active,
        "limit": settings.rate_limit_per_minute,
        "remaining": max(0, settings.rate_limit_per_minute - active),
    }
