"""In-memory sliding-window rate limiter (Milestone 12).

Deployment scope (IMPORTANT, documented): this limiter is PER-PROCESS. The
application is configured for a single uvicorn worker (settings.workers=1;
backend/Dockerfile CMD runs one process), so in-memory enforcement is correct
there. If the deployment ever scales to multiple workers or replicas, each
process maintains independent counters and global limits become
count × N — a shared backend (Redis, or a gateway-level limiter) is then
REQUIRED before distributed enforcement can be claimed.

Keys are bounded: fixed prefixes + normalized UUID/IP values only. No
usernames, filenames, tokens, or other user-supplied strings are used as
limiter keys or metrics labels.
"""

from __future__ import annotations

import ipaddress
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from backend.config import settings

_WINDOW_SECONDS = 60.0
_MAX_KEYS = 10_000          # bounded memory; defensive cap against key spam
_MAX_KEY_LEN = 128


class SlidingWindowLimiter:
    """Thread-safe sliding window (per-minute by default) rate limiter."""

    def __init__(self, window_seconds: float = _WINDOW_SECONDS, max_events: int = 1000) -> None:
        self._lock = threading.Lock()
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._window = window_seconds
        self._max_events = max_events

    def check(self, key: str, limit: int) -> float:
        """Record one hit; return retry-after seconds, 0.0 when allowed."""
        if limit <= 0:
            return 0.0
        now = time.monotonic()
        cutoff = now - self._window
        with self._lock:
            if len(self._events) > _MAX_KEYS:
                self._prune(now)
            bucket = self._events.get(key) or self._events.setdefault(key, deque())
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                retry_after = self._window - (now - bucket[0])
                return max(1.0, round(retry_after, 1))
            bucket.append(now)
            return 0.0

    def _prune(self, now: float) -> None:
        cutoff = now - self._window
        stale = [k for k, v in self._events.items() if not v or v[-1] < cutoff]
        for k in stale:
            del self._events[k]
        if len(self._events) > _MAX_KEYS:  # pathological flood: reset oldest half
            for k in sorted(self._events.keys())[: _MAX_KEYS // 2]:
                del self._events[k]


limiter = SlidingWindowLimiter()


def _bounded_client_ip(request: Request) -> str:
    """Internally-determined client IP; bounded and normalized."""
    client = request.client.host if request.client else "unknown"
    try:
        return str(ipaddress.ip_address(client))
    except ValueError:
        return "unknown"


def _safe_key_length(key: str) -> str:
    return key[:_MAX_KEY_LEN]


def _limit_exceeded(retry_after: float) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Rate limit exceeded. Please try again later.",
        headers={"Retry-After": str(int(retry_after))},
    )


async def enforce_login_rate_limit(request: Request) -> None:
    """5 login attempts / minute / client IP."""
    retry = limiter.check(
        _safe_key_length(f"login:{_bounded_client_ip(request)}"),
        settings.rate_limit_login_per_minute,
    )
    if retry:
        raise _limit_exceeded(retry)


async def enforce_scan_rate_limit(request: Request) -> None:
    return None  # enforced per-user after auth resolution (see auth_scan_rate_limit)


def auth_scan_rate_limit_key(request: Request) -> str:
    return _safe_key_length(f"scan:{_bounded_client_ip(request)}")


async def enforce_scans_rate(request: Request) -> None:
    """10 scans / minute / client IP (bounded key; no 401 leakage of usernames)."""
    retry = limiter.check(
        auth_scan_rate_limit_key(request),
        settings.rate_limit_scan_per_minute,
    )
    if retry:
        raise _limit_exceeded(retry)
