"""baseline application schema

Revision ID: 0001_baseline
Revises:
Create Date: 2026-08-05
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "points",
        sa.Column("point_id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("barangay_name", sa.Text(), nullable=False),
        sa.Column("city", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("point_id"),
    )
    op.create_table(
        "sessions",
        sa.Column("session_id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("point_id", sa.Integer(), nullable=False),
        sa.Column("session_number", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(["point_id"], ["points.point_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("session_id"),
    )
    op.create_index("ix_sessions_point_id", "sessions", ["point_id"])
    op.create_table(
        "audio_recordings",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("db_level", sa.Float(), nullable=True),
        sa.Column("start_time", sa.Text(), nullable=True),
        sa.Column("analysis_text", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.session_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audio_recordings_session_id", "audio_recordings", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_audio_recordings_session_id", table_name="audio_recordings")
    op.drop_table("audio_recordings")
    op.drop_index("ix_sessions_point_id", table_name="sessions")
    op.drop_table("sessions")
    op.drop_table("points")
