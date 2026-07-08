"""Hosted Tier-2 sim-minutes — job queue + per-workspace quota tables (M27).

Commercial — see cloud/LICENSE. A ``SimJob`` is a unit of hosted simulation work submitted to a
workspace; a ``SimQuota`` caps how many sim-minutes a workspace may consume (the hard budget the
bible §11 requires). Both tables are prefixed ``cloud_*`` and run on SQLite locally / Postgres in
production, exactly like the M26 tables.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel

DEFAULT_QUOTA_MINUTES = 60

JobStatus = str  # queued | running | done | failed


def _now() -> datetime:
    return datetime.now(UTC)


class SimQuota(SQLModel, table=True):
    __tablename__ = "cloud_sim_quota"

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="cloud_workspace.id", index=True, unique=True)
    sim_minute_quota: int = DEFAULT_QUOTA_MINUTES
    sim_minutes_used: int = 0

    @property
    def remaining(self) -> int:
        return max(0, self.sim_minute_quota - self.sim_minutes_used)


class SimJob(SQLModel, table=True):
    __tablename__ = "cloud_sim_job"

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="cloud_workspace.id", index=True)
    agent: str
    agent_input_json: str = "{}"
    recording_json: str = "{}"
    status: JobStatus = Field(default="queued", index=True)
    sim_minutes: int = 0
    error: str | None = None
    result_run_id: str | None = None
    result_verdict: str | None = None
    created_at: datetime = Field(default_factory=_now)
    started_at: datetime | None = None
    finished_at: datetime | None = None
