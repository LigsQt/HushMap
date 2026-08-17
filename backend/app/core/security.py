from __future__ import annotations

import hashlib
import time
from collections import defaultdict, deque

from fastapi import Header, HTTPException, Request, status

from app.config import Settings


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


class DeviceAuthenticator:
    def __init__(self, raw_keys: list[str]) -> None:
        self._hashes = {hash_api_key(key) for key in raw_keys}

    @property
    def configured(self) -> bool:
        return bool(self._hashes)

    def verify(self, presented: str | None) -> bool:
        if not presented:
            return False
        return hash_api_key(presented) in self._hashes


class SlidingWindowRateLimiter:
    def __init__(self, limit: int, window_seconds: int = 60) -> None:
        self._limit = limit
        self._window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        bucket = self._hits[key]
        cutoff = now - self._window
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= self._limit:
            return False
        bucket.append(now)
        return True


def extract_api_key(
    authorization: str | None,
    x_api_key: str | None,
) -> str | None:
    if x_api_key:
        return x_api_key.strip()
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and token:
            return token.strip()
    return authorization.strip() if authorization else None


async def require_device_api_key(
    request: Request,
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> str:
    settings: Settings = request.app.state.settings
    authenticator: DeviceAuthenticator = request.app.state.device_auth
    presented = extract_api_key(authorization, x_api_key)

    if not authenticator.configured:
        if settings.app_env == "development":
            return "development-unauthenticated"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Device API keys are not configured",
        )

    if not authenticator.verify(presented):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing device API key",
        )

    assert presented is not None
    return presented


async def enforce_upload_rate_limit(request: Request, api_key: str) -> None:
    limiter: SlidingWindowRateLimiter = request.app.state.upload_limiter
    bucket_key = api_key if api_key != "development-unauthenticated" else (
        request.client.host if request.client else "unknown"
    )
    if not limiter.allow(bucket_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Upload rate limit exceeded",
        )
