from __future__ import annotations

import io
import wave
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.core.security import enforce_upload_rate_limit, require_device_api_key
from app.dependencies import AIProviderDep, AudioStoreDep, DbSessionDep, SettingsDep
from app.repositories import RecordingRepository, SessionRepository
from app.services.ai import AIProviderError
from app.services.audio_ingest import AppendStatus, AudioBufferError
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


async def _read_limited_body(request: Request, max_bytes: int) -> bytes:
    content_length = request.headers.get("Content-Length")
    if content_length is not None:
        try:
            declared_length = int(content_length)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid Content-Length") from exc
        if declared_length < 0:
            raise HTTPException(status_code=400, detail="Invalid Content-Length")
        if declared_length > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="Audio chunk exceeds configured maximum",
            )

    body = bytearray()
    async for part in request.stream():
        if len(body) + len(part) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="Audio chunk exceeds configured maximum",
            )
        body.extend(part)
    return bytes(body)


@router.post("/upload/{session_id}")
async def receive_audio_chunk(
    session_id: int,
    request: Request,
    settings: SettingsDep,
    audio_store: AudioStoreDep,
    ai: AIProviderDep,
    db: DbSessionDep,
    device_principal: str = Depends(require_device_api_key),
) -> Response:
    await enforce_upload_rate_limit(request, device_principal)
    if not await SessionRepository(db).exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    await db.rollback()

    sequence_header = request.headers.get("X-Chunk-Sequence")
    try:
        sequence = int(sequence_header) if sequence_header is not None else None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid X-Chunk-Sequence") from exc
    idempotency_key = request.headers.get("Idempotency-Key")
    if idempotency_key and await audio_store.is_completed_duplicate(
        session_id,
        idempotency_key,
        device_principal,
    ):
        return Response(status_code=status.HTTP_200_OK)

    chunk = await _read_limited_body(request, settings.audio_max_chunk_bytes)
    if not chunk:
        raise HTTPException(status_code=400, detail="Empty audio chunk")

    try:
        complete = await audio_store.append(
            session_id,
            chunk,
            sequence=sequence,
            idempotency_key=idempotency_key,
            owner_key=device_principal,
        )
    except AudioBufferError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if complete is AppendStatus.DUPLICATE_COMPLETED:
        return Response(status_code=status.HTTP_200_OK)
    if complete is AppendStatus.PROCESSING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Previous audio window is still processing",
            headers={"Retry-After": "1"},
        )
    if complete is None:
        return Response(status_code=status.HTTP_202_ACCEPTED)

    persisted = False
    try:
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
        await db.commit()
        persisted = True
    finally:
        if not persisted:
            await audio_store.abort_completion(session_id, device_principal)

    await audio_store.finalize_completion(session_id, device_principal)
    return Response(status_code=status.HTTP_201_CREATED)
