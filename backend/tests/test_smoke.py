from __future__ import annotations

import io
import wave

import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings, get_settings
from app.main import app
from app.services.audio_ingest import AudioBufferStore, ChunkOrderError
from app.services.process_audio import process_audio


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_root_and_liveness():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        root = await client.get("/")
        live = await client.get("/health/live")
    assert root.status_code == 200
    assert root.json() == {"message": "Working!"}
    assert live.status_code == 200
    assert live.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_audio_buffers_are_session_scoped():
    store = AudioBufferStore(
        target_bytes=8,
        max_chunk_bytes=8,
        max_buffer_bytes=16,
        ttl_seconds=60,
        max_active_sessions=10,
    )
    assert await store.append(1, b"aaaa") is None
    assert await store.append(2, b"bbbb") is None
    first = await store.append(1, b"cccc")
    second = await store.append(2, b"dddd")
    assert first == b"aaaacccc"
    assert second == b"bbbbdddd"


@pytest.mark.asyncio
async def test_audio_buffer_rejects_out_of_order_chunks():
    store = AudioBufferStore(
        target_bytes=100,
        max_chunk_bytes=10,
        max_buffer_bytes=100,
        ttl_seconds=60,
        max_active_sessions=10,
    )
    await store.append(1, b"a", sequence=0)
    with pytest.raises(ChunkOrderError):
        await store.append(1, b"b", sequence=2)


def test_process_audio_returns_finite_level():
    samples = np.zeros(16000 * 20, dtype=np.int32)
    samples[1000:1200] = 1_000_000
    dba = process_audio(16000 * 20, samples.tobytes())
    assert np.isfinite(dba)
    assert dba >= 30.0


def test_settings_split_cors():
    settings = Settings(cors_origins="http://a.example,http://b.example")
    assert settings.cors_origins == ["http://a.example", "http://b.example"]


def _silent_wav() -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(4)
        wf.setframerate(16000)
        wf.writeframes(np.zeros(1600, dtype=np.int32).tobytes())
    return buffer.getvalue()
