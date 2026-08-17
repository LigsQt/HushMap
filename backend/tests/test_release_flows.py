from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.config import Settings
from app.core.security import DeviceAuthenticator, SlidingWindowRateLimiter, require_device_api_key
from app.repositories import PointRepository, RecordingRepository, SessionRepository
from app.routers.audio import receive_audio_chunk
from app.routers.points import get_points_geojson, get_session_ai_description
from app.services.audio_ingest import AppendStatus, AudioBufferStore, BufferLimitError


def _request_state(client_host="127.0.0.1", **state):
    return SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(**state)),
        client=SimpleNamespace(host=client_host),
        headers={},
    )


class _NeverAudioStore:
    async def append(self, *args, **kwargs):
        raise AssertionError("invalid sessions must not reach the audio buffer")


class _FakeSession:
    def __init__(self) -> None:
        self.rollback_calls = 0

    async def rollback(self) -> None:
        self.rollback_calls += 1


class _StreamingRequest:
    def __init__(self, payload: bytes, headers=None) -> None:
        self.app = SimpleNamespace(
            state=SimpleNamespace(upload_limiter=SlidingWindowRateLimiter(10))
        )
        self.client = SimpleNamespace(host="127.0.0.1")
        self.headers = headers or {}
        self.payload = payload
        self.stream_calls = 0

    async def stream(self):
        self.stream_calls += 1
        yield self.payload


class _CountingAI:
    def __init__(self) -> None:
        self.description_calls = 0
        self.summary_calls = 0

    async def describe_audio(self, audio: bytes) -> str:
        self.description_calls += 1
        return "description"

    async def summarize_descriptions(self, descriptions: str) -> str:
        self.summary_calls += 1
        return "summary"


@pytest.mark.asyncio
async def test_upload_rejects_missing_session_before_body_buffer_or_ai(monkeypatch):
    async def session_missing(self, session_id):
        return False

    monkeypatch.setattr(SessionRepository, "exists", session_missing)
    request = _StreamingRequest(b"must not be read")
    ai = _CountingAI()

    with pytest.raises(HTTPException) as exc_info:
        await receive_audio_chunk(
            session_id=999,
            request=request,
            settings=Settings(),
            audio_store=_NeverAudioStore(),
            ai=ai,
            db=object(),
            device_principal="device:test",
        )

    assert exc_info.value.status_code == 404
    assert request.stream_calls == 0
    assert ai.description_calls == 0


@pytest.mark.asyncio
async def test_upload_rejects_invalid_headers_and_oversized_streams_before_buffering(
    monkeypatch,
):
    async def session_exists(self, session_id):
        return True

    monkeypatch.setattr(SessionRepository, "exists", session_exists)
    ai = _CountingAI()

    invalid_sequence = _StreamingRequest(
        b"must not be read",
        headers={"X-Chunk-Sequence": "not-a-number"},
    )
    invalid_session = _FakeSession()
    with pytest.raises(HTTPException) as exc_info:
        await receive_audio_chunk(
            session_id=1,
            request=invalid_sequence,
            settings=Settings(audio_max_chunk_bytes=4),
            audio_store=_NeverAudioStore(),
            ai=ai,
            db=invalid_session,
            device_principal="device:test",
        )
    assert exc_info.value.status_code == 400
    assert invalid_sequence.stream_calls == 0
    assert invalid_session.rollback_calls == 1

    oversized = _StreamingRequest(b"12345")
    oversized_session = _FakeSession()
    with pytest.raises(HTTPException) as exc_info:
        await receive_audio_chunk(
            session_id=1,
            request=oversized,
            settings=Settings(audio_max_chunk_bytes=4),
            audio_store=_NeverAudioStore(),
            ai=ai,
            db=oversized_session,
            device_principal="device:test",
        )
    assert exc_info.value.status_code == 413
    assert oversized.stream_calls == 1
    assert oversized_session.rollback_calls == 1
    assert ai.description_calls == 0


@pytest.mark.asyncio
async def test_invalid_summary_session_cannot_trigger_ai(monkeypatch):
    async def session_missing(self, session_id):
        return False

    async def unexpected_recording_lookup(self, session_id):
        raise AssertionError("invalid sessions must not load recordings")

    monkeypatch.setattr(SessionRepository, "exists", session_missing)
    monkeypatch.setattr(RecordingRepository, "list_for_session", unexpected_recording_lookup)
    request = _request_state(
        summary_request_limiter=SlidingWindowRateLimiter(10),
        summary_global_limiter=SlidingWindowRateLimiter(10),
    )
    ai = _CountingAI()

    with pytest.raises(HTTPException) as exc_info:
        await get_session_ai_description(999, request, object(), ai)

    assert exc_info.value.status_code == 404
    assert ai.summary_calls == 0


@pytest.mark.asyncio
async def test_summary_request_rate_limit_bounds_ai_calls(monkeypatch):
    async def session_exists(self, session_id):
        return True

    async def recordings(self, session_id):
        return [SimpleNamespace(analysis_text="Distant traffic")]

    monkeypatch.setattr(SessionRepository, "exists", session_exists)
    monkeypatch.setattr(RecordingRepository, "list_for_session", recordings)
    request = _request_state(
        summary_request_limiter=SlidingWindowRateLimiter(1),
        summary_global_limiter=SlidingWindowRateLimiter(10),
    )
    session = _FakeSession()
    ai = _CountingAI()

    assert await get_session_ai_description(1, request, session, ai) == "summary"
    with pytest.raises(HTTPException) as exc_info:
        await get_session_ai_description(1, request, session, ai)

    assert exc_info.value.status_code == 429
    assert ai.summary_calls == 1
    assert session.rollback_calls == 1


@pytest.mark.asyncio
async def test_global_summary_rate_limit_bounds_calls_across_clients(monkeypatch):
    async def session_exists(self, session_id):
        return True

    async def recordings(self, session_id):
        return [SimpleNamespace(analysis_text="Distant traffic")]

    monkeypatch.setattr(SessionRepository, "exists", session_exists)
    monkeypatch.setattr(RecordingRepository, "list_for_session", recordings)
    global_limiter = SlidingWindowRateLimiter(1)
    first_request = _request_state(
        client_host="127.0.0.1",
        summary_request_limiter=SlidingWindowRateLimiter(10),
        summary_global_limiter=global_limiter,
    )
    second_request = _request_state(
        client_host="127.0.0.2",
        summary_request_limiter=SlidingWindowRateLimiter(10),
        summary_global_limiter=global_limiter,
    )
    ai = _CountingAI()

    assert (
        await get_session_ai_description(1, first_request, _FakeSession(), ai) == "summary"
    )
    with pytest.raises(HTTPException) as exc_info:
        await get_session_ai_description(1, second_request, _FakeSession(), ai)

    assert exc_info.value.status_code == 429
    assert ai.summary_calls == 1


@pytest.mark.asyncio
async def test_device_authentication_fails_closed_outside_explicit_development_bypass():
    production = _request_state(
        settings=Settings(
            app_env="production",
            allow_unauthenticated_device_uploads=True,
        ),
        device_auth=DeviceAuthenticator([]),
    )
    with pytest.raises(HTTPException) as exc_info:
        await require_device_api_key(production, None, None)
    assert exc_info.value.status_code == 503

    development = _request_state(
        settings=Settings(
            app_env="development",
            allow_unauthenticated_device_uploads=True,
        ),
        device_auth=DeviceAuthenticator([]),
    )
    principal = await require_device_api_key(development, None, None)
    assert principal == "development:127.0.0.1"


def test_rate_limiter_bounds_and_evicts_client_buckets(monkeypatch):
    timestamps = iter([0.0, 0.0, 0.0, 61.0])
    monkeypatch.setattr("app.core.security.time.monotonic", lambda: next(timestamps))
    limiter = SlidingWindowRateLimiter(1, window_seconds=60, max_buckets=2)

    assert limiter.allow("client-a")
    assert limiter.allow("client-b")
    assert not limiter.allow("client-c")
    assert limiter.allow("client-c")


@pytest.mark.asyncio
async def test_audio_buffers_enforce_device_quota_and_ownership():
    store = AudioBufferStore(
        target_bytes=8,
        max_chunk_bytes=8,
        max_buffer_bytes=16,
        ttl_seconds=60,
        max_active_sessions=10,
        max_active_sessions_per_owner=1,
    )

    assert await store.append(1, b"aaaa", owner_key="device:a") is None
    with pytest.raises(BufferLimitError, match="too many active"):
        await store.append(2, b"bbbb", owner_key="device:a")

    assert await store.append(2, b"bbbb", owner_key="device:b") is None
    with pytest.raises(BufferLimitError, match="another device"):
        await store.append(1, b"bbbb", owner_key="device:b")

    assert await store.append(1, b"cccc", owner_key="device:a") == b"aaaacccc"
    await store.finalize_completion(1, "device:a")
    assert await store.append(3, b"aaaa", owner_key="device:a") is None


@pytest.mark.asyncio
async def test_completed_idempotency_keys_prevent_duplicate_processing():
    store = AudioBufferStore(
        target_bytes=8,
        max_chunk_bytes=8,
        max_buffer_bytes=16,
        ttl_seconds=60,
        max_active_sessions=10,
    )

    assert (
        await store.append(
            1,
            b"aaaa",
            idempotency_key="chunk-1",
            owner_key="device:a",
        )
        is None
    )
    assert await store.append(
        1,
        b"bbbb",
        idempotency_key="chunk-2",
        owner_key="device:a",
    ) == b"aaaabbbb"
    assert not await store.is_completed_duplicate(1, "chunk-2", "device:a")
    await store.abort_completion(1, "device:a")
    assert await store.append(
        1,
        b"bbbb",
        idempotency_key="chunk-2",
        owner_key="device:a",
    ) == b"aaaabbbb"
    await store.finalize_completion(1, "device:a")
    assert await store.is_completed_duplicate(1, "chunk-2", "device:a")
    assert (
        await store.append(
            1,
            b"bbbb",
            idempotency_key="chunk-2",
            owner_key="device:a",
        )
        is AppendStatus.DUPLICATE_COMPLETED
    )


@pytest.mark.asyncio
async def test_chunks_are_retryably_rejected_while_previous_window_processes(monkeypatch):
    async def session_exists(self, session_id):
        return True

    monkeypatch.setattr(SessionRepository, "exists", session_exists)
    store = AudioBufferStore(
        target_bytes=4,
        max_chunk_bytes=8,
        max_buffer_bytes=8,
        ttl_seconds=60,
        max_active_sessions=10,
    )
    assert await store.append(1, b"aaaa", owner_key="device:a") == b"aaaa"
    request = _StreamingRequest(b"bbbb")
    ai = _CountingAI()

    with pytest.raises(HTTPException) as exc_info:
        await receive_audio_chunk(
            session_id=1,
            request=request,
            settings=Settings(audio_max_chunk_bytes=8),
            audio_store=store,
            ai=ai,
            db=_FakeSession(),
            device_principal="device:a",
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.headers == {"Retry-After": "1"}
    assert ai.description_calls == 0


@pytest.mark.asyncio
async def test_empty_database_returns_valid_geojson(monkeypatch):
    async def no_points(self):
        return []

    monkeypatch.setattr(PointRepository, "list_with_recordings", no_points)

    assert await get_points_geojson(object()) == {
        "type": "FeatureCollection",
        "features": [],
    }
