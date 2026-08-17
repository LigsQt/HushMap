from __future__ import annotations

import statistics
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from app.core.security import (
    enforce_summary_global_rate_limit,
    enforce_summary_request_rate_limit,
)
from app.dependencies import AIProviderDep, DbSessionDep
from app.models import PointResponse
from app.repositories import (
    PointRepository,
    RecordingRepository,
    SessionRepository,
    is_point_active,
)
from app.services.ai import AIProviderError

router = APIRouter()


def _format_date(value: Any) -> str:
    if hasattr(value, "strftime"):
        return value.strftime("%B %d, %Y")
    return datetime.strptime(str(value), "%Y-%m-%d").strftime("%B %d, %Y")


@router.get("/points/{point_id}", response_model=PointResponse)
async def get_point_with_sessions(point_id: int, session: DbSessionDep) -> dict[str, Any]:
    point = await PointRepository(session).get_with_recordings(point_id)
    if point is None:
        raise HTTPException(status_code=404, detail="Point not found")

    sessions: list[dict[str, Any]] = []
    all_noise_levels: list[float] = []

    for db_session in point.sessions:
        session_noise_levels: list[float] = []
        session_data: dict[str, Any] = {
            "sessionNumber": db_session.session_number,
            "session_id": db_session.session_id,
            "startDate": _format_date(db_session.start_date),
            "endDate": _format_date(db_session.end_date),
            "meanNoiseSession": 0.0,
            "data": [],
            "startTimes": [],
            "descriptions": [],
        }

        for recording in db_session.recordings:
            noise_level = round(float(recording.db_level or 0), 2)
            session_data["data"].append(noise_level)
            session_noise_levels.append(noise_level)
            all_noise_levels.append(noise_level)
            session_data["startTimes"].append(recording.start_time)
            session_data["descriptions"].append(recording.analysis_text or "Normal.")

        if session_noise_levels:
            session_data["meanNoiseSession"] = round(statistics.mean(session_noise_levels), 2)
        sessions.append(session_data)

    return {
        "pointId": str(point.point_id),
        "lat": point.latitude,
        "lon": point.longitude,
        "brgy": point.barangay_name,
        "city": point.city,
        "meanNoise": round(statistics.mean(all_noise_levels) if all_noise_levels else 0, 2),
        "sessions": sessions,
    }


@router.get("/geojson/points")
async def get_points_geojson(session: DbSessionDep) -> dict[str, Any]:
    points = await PointRepository(session).list_with_recordings()

    features: list[dict[str, Any]] = []
    for point in points:
        db_levels = [
            recording.db_level
            for db_session in point.sessions
            for recording in db_session.recordings
            if recording.db_level is not None
        ]
        mean_noise = statistics.mean(db_levels) if db_levels else 0.0
        features.append(
            {
                "type": "Feature",
                "id": point.point_id,
                "geometry": {
                    "type": "Point",
                    "coordinates": [point.longitude, point.latitude],
                },
                "properties": {
                    "noOfSessions": len(point.sessions),
                    "meanNoiseLevel": round(mean_noise, 1),
                    "brgy": point.barangay_name,
                    "city": point.city,
                    "isActive": is_point_active(point),
                },
            }
        )

    return {"type": "FeatureCollection", "features": features}


@router.get("/session_info/{session_id}")
async def get_session_ai_description(
    session_id: int,
    request: Request,
    session: DbSessionDep,
    ai: AIProviderDep,
) -> str:
    await enforce_summary_request_rate_limit(request)
    if not await SessionRepository(session).exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    recordings = await RecordingRepository(session).list_for_session(session_id)
    analysis_texts = "|".join(
        recording.analysis_text or "" for recording in recordings if recording.analysis_text
    )
    await session.rollback()
    if not analysis_texts:
        return "No analysis text available for this session."
    await enforce_summary_global_rate_limit(request)

    try:
        return await ai.summarize_descriptions(analysis_texts)
    except AIProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
