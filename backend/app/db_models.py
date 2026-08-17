from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Identity, Index, Integer, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Point(Base):
    __tablename__ = "points"

    point_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    barangay_name: Mapped[str] = mapped_column(Text, nullable=False)
    city: Mapped[str] = mapped_column(Text, nullable=False)

    sessions: Mapped[list["Session"]] = relationship(
        back_populates="point",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Session.session_id",
    )


class Session(Base):
    __tablename__ = "sessions"
    __table_args__ = (Index("ix_sessions_point_id", "point_id"),)

    session_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    point_id: Mapped[int] = mapped_column(
        ForeignKey("points.point_id", ondelete="CASCADE"),
        nullable=False,
    )
    session_number: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)

    point: Mapped[Point] = relationship(back_populates="sessions")
    recordings: Mapped[list["AudioRecording"]] = relationship(
        back_populates="session",
        order_by="AudioRecording.id",
    )


class AudioRecording(Base):
    __tablename__ = "audio_recordings"
    __table_args__ = (Index("ix_audio_recordings_session_id", "session_id"),)

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("sessions.session_id"),
        nullable=False,
    )
    db_level: Mapped[float | None] = mapped_column(Float, nullable=True)
    start_time: Mapped[str | None] = mapped_column(Text, nullable=True)
    analysis_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    session: Mapped[Session] = relationship(back_populates="recordings")
