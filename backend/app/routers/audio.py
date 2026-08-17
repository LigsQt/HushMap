from __future__ import annotations

import io
import wave
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.core.security import enforce_upload_rate_limit, require_device_api_key
from app.dependencies import AIProviderDep, AudioStoreDep, DbSessionDep, SettingsDep
from app.repositories import RecordingRepository
from app.services.ai import AIProviderError
from app.services.audio_ingest import AudioBufferError
from app.services.process_audio import process_audio

router = APIRouter()
MANILA = ZoneInfo("Asia/Manila")


def _build_wav_bytes(
    pcm: bytes,
    *,
    channels: int,
    sample_width: int,
    sample_rate: int,
    gain: float,
) -> bytes:
    audio_array = np.frombuffer(pcm, dtype=np.int32)
    amplified = audio_array.astype(np.float64) * gain
    amplified = np.clip(amplified, -2147483648, 2147483647).astype(np.int32)

    buffer_file = io.BytesIO()
    with wave.open(buffer_file, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(amplified.tobytes())
    return buffer_file.getvalue()


@router.post("/upload/{session_id}")
async def receive_audio_chunk(
    session_id: int,
    request: Request,
    settings: SettingsDep,
    audio_store: AudioStoreDep,
    ai: AIProviderDep,
    db: DbSessionDep,
    api_key: str = Depends(require_device_api_key),
) -> Response:
    await enforce_upload_rate_limit(request, api_key)
    chunk = await request.body()
    if not chunk:
        raise HTTPException(status_code=400, detail="Empty audio chunk")

    sequence_header = request.headers.get("X-Chunk-Sequence")
    sequence = int(sequence_header) if sequence_header is not None else None
    idempotency_key = request.headers.get("Idempotency-Key")

    try:
        complete = await audio_store.append(
            session_id,
            chunk,
            sequence=sequence,
            idempotency_key=idempotency_key,
        )
    except AudioBufferError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if complete is None:
        return Response(status_code=status.HTTP_202_ACCEPTED)

    dba = float(process_audio(settings.samples_per_leq, complete))
    wav_bytes = _build_wav_bytes(
        complete,
        channels=settings.audio_channels,
        sample_width=settings.audio_sample_width,
        sample_rate=settings.audio_sample_rate,
        gain=settings.audio_gain,
    )

    try:
        analysis_text = await ai.describe_audio(wav_bytes)
    except AIProviderError:
        analysis_text = "AI description unavailable"

    timestamp = datetime.now(MANILA).strftime("%H:%M")
    await RecordingRepository(db).add(
        session_id=session_id,
        db_level=dba,
        start_time=timestamp,
        analysis_text=analysis_text,
    )
    return Response(status_code=status.HTTP_201_CREATED)
