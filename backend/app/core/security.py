"""API security: token-based auth and rate limiting."""

from __future__ import annotations

import hashlib
import time
from collections import defaultdict
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import Settings, get_settings

bearer_scheme = HTTPBearer(auto_error=False)


def verify_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> bool:
    """Verify bearer token against API_SECRET_KEY. Skipped in dev mode when no token sent."""
    if settings.environment == "development" and credentials is None:
        return True
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token",
        )
    expected = hashlib.sha256(settings.api_secret_key.encode()).hexdigest()
    received = hashlib.sha256(credentials.credentials.encode()).hexdigest()
    if expected != received:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization token",
        )
    return True


class RateLimiter:
    """Simple in-memory sliding-window rate limiter."""

    def __init__(self) -> None:
        self._hits: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str, limit: int, window_seconds: int) -> bool:
        now = time.time()
        cutoff = now - window_seconds
        self._hits[key] = [t for t in self._hits[key] if t > cutoff]
        if len(self._hits[key]) >= limit:
            return False
        self._hits[key].append(now)
        return True


_limiter = RateLimiter()


async def rate_limit(request: Request, settings: Settings = Depends(get_settings)) -> None:
    """Rate-limit by client IP using the configured API_RATE_LIMIT."""
    parts = settings.api_rate_limit.split("/")
    limit = int(parts[0])
    window_name = parts[1] if len(parts) > 1 else "minute"
    window_map = {"second": 1, "minute": 60, "hour": 3600}
    window = window_map.get(window_name, 60)

    client_ip = request.client.host if request.client else "unknown"
    if not _limiter.check(client_ip, limit, window):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {settings.api_rate_limit}",
        )
