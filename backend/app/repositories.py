from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db_models import AudioRecording, Point, Session

MANILA = ZoneInfo("Asia/Manila")


class PointRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_with_recordings(self, point_id: int) -> Point | None:
        statement = (
            select(Point)
            .where(Point.point_id == point_id)
            .options(selectinload(Point.sessions).selectinload(Session.recordings))
        )
        return await self._session.scalar(statement)

    async def list_with_recordings(self) -> list[Point]:
        statement = (
            select(Point)
            .order_by(Point.point_id)
            .options(selectinload(Point.sessions).selectinload(Session.recordings))
        )
        return list((await self._session.scalars(statement)).all())


class SessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def exists(self, session_id: int) -> bool:
        statement = select(Session.session_id).where(Session.session_id == session_id)
        return await self._session.scalar(statement) is not None


class RecordingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_session(self, session_id: int) -> list[AudioRecording]:
        statement = (
            select(AudioRecording)
            .where(AudioRecording.session_id == session_id)
            .order_by(AudioRecording.id)
        )
        return list((await self._session.scalars(statement)).all())

    async def add(
        self,
        *,
        session_id: int,
        db_level: float,
        start_time: str,
        analysis_text: str,
    ) -> AudioRecording:
        recording = AudioRecording(
            session_id=session_id,
            db_level=db_level,
            start_time=start_time,
            analysis_text=analysis_text,
        )
        self._session.add(recording)
        await self._session.flush()
        return recording


def is_point_active(point: Point, now: datetime | None = None) -> bool:
    if not point.sessions:
        return False
    latest_session = max(point.sessions, key=lambda item: item.session_id)
    if not latest_session.recordings:
        return False
    latest_recording = max(latest_session.recordings, key=lambda item: item.id)
    if not latest_recording.start_time:
        return False

    current = now.astimezone(MANILA) if now else datetime.now(MANILA)
    if latest_session.end_date != current.date():
        return False
    try:
        recorded_time = datetime.strptime(latest_recording.start_time, "%H:%M").time()
    except ValueError:
        return False
    recorded_at = datetime.combine(current.date(), recorded_time, tzinfo=MANILA)
    age = current - recorded_at
    return timedelta(0) < age < timedelta(hours=1)
