from __future__ import annotations

import hashlib
import time
from collections import deque

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

    def principal(self, presented: str | None) -> str | None:
        if not presented:
            return None
        digest = hash_api_key(presented)
        return f"device:{digest}" if digest in self._hashes else None

    def verify(self, presented: str | None) -> bool:
        return self.principal(presented) is not None


class SlidingWindowRateLimiter:
    def __init__(
        self,
        limit: int,
        window_seconds: int = 60,
        max_buckets: int = 10_000,
    ) -> None:
        if limit < 1 or window_seconds < 1 or max_buckets < 1:
            raise ValueError("Rate limiter settings must be positive")
        self._limit = limit
        self._window = window_seconds
        self._max_buckets = max_buckets
        self._hits: dict[str, deque[float]] = {}

    def _prune_expired(self, now: float) -> None:
        cutoff = now - self._window
        for key, bucket in list(self._hits.items()):
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if not bucket:
                del self._hits[key]

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self._window
        bucket = self._hits.get(key)
        if bucket is None:
            if len(self._hits) >= self._max_buckets:
                self._prune_expired(now)
            if len(self._hits) >= self._max_buckets:
                return False
            bucket = deque()
            self._hits[key] = bucket
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


def client_scope_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


async def require_device_api_key(
    request: Request,
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> str:
    settings: Settings = request.app.state.settings
    authenticator: DeviceAuthenticator = request.app.state.device_auth
    presented = extract_api_key(authorization, x_api_key)

    if not authenticator.configured:
        if (
            settings.app_env == "development"
            and settings.allow_unauthenticated_device_uploads
        ):
            return f"development:{client_scope_key(request)}"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Device API keys are not configured",
        )

    principal = authenticator.principal(presented)
    if principal is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing device API key",
        )

    return principal


async def enforce_upload_rate_limit(request: Request, principal: str) -> None:
    limiter: SlidingWindowRateLimiter = request.app.state.upload_limiter
    if not limiter.allow(principal):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Upload rate limit exceeded",
        )


async def enforce_summary_request_rate_limit(request: Request) -> None:
    limiter: SlidingWindowRateLimiter = request.app.state.summary_request_limiter
    if not limiter.allow("global"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Summary request limit exceeded",
        )


async def enforce_summary_global_rate_limit(request: Request) -> None:
    limiter: SlidingWindowRateLimiter = request.app.state.summary_global_limiter
    if not limiter.allow("global"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Summary service is temporarily at capacity",
        )
