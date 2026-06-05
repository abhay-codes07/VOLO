"""Volo storage layer — SQLModel + SQLite default, Postgres seam for cloud (§10, §11).

Three responsibilities:

1. **Engine factory.** ``get_engine(url=None)`` returns a SQLAlchemy engine. URL resolution
   order: explicit arg → ``VOLO_DB_URL`` env → ``sqlite:///./.volo/volo.db``.
2. **Schema bootstrap.** ``init_schema(engine)`` creates all tables. Idempotent. The OSS
   path uses this; cloud will swap in Alembic when migrations matter.
3. **Domain tables.** ``Project``, ``AgentVersion``, ``RecordingRow``, ``RunRow``,
   ``ReportRow`` — relational rows that mirror the Pydantic models in
   ``volo_core.recording`` and ``volo_reliability.report`` without depending on either
   (storage is a thin edge — the Pydantic models stay canonical).

The OSS dashboard reads filesystem JSON by default. When ``VOLO_DB_URL`` is set or the
default ``.volo/volo.db`` exists, the API layer prefers the DB. Bridge functions
``store_recording(...)`` and ``store_report(...)`` keep both paths in sync.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.engine import Engine
from sqlmodel import Field, Session, SQLModel, col, create_engine, select


def _default_sqlite_url() -> str:
    data_dir = Path(os.environ.get("VOLO_DATA_DIR", "./.volo"))
    data_dir.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{(data_dir / 'volo.db').as_posix()}"


def get_engine(url: str | None = None) -> Engine:
    """Return a SQLAlchemy engine. Resolution: arg → ``VOLO_DB_URL`` → SQLite default."""
    resolved = url or os.environ.get("VOLO_DB_URL") or _default_sqlite_url()
    # SQLite needs check_same_thread=False under FastAPI's threadpool.
    connect_args = {"check_same_thread": False} if resolved.startswith("sqlite") else {}
    return create_engine(resolved, connect_args=connect_args)


def init_schema(engine: Engine) -> None:
    """Create all Volo tables if they don't exist. Idempotent."""
    SQLModel.metadata.create_all(engine)


def session(engine: Engine) -> Session:
    """Return a fresh ``Session`` bound to the given engine."""
    return Session(engine)


# ── domain tables ────────────────────────────────────────────────────────────


def _now() -> datetime:
    return datetime.now(UTC)


class Project(SQLModel, table=True):
    """A logical project — multiple ``AgentVersion``s live under one project (bible §10)."""

    __tablename__ = "project"

    id: int | None = Field(default=None, primary_key=True)
    slug: str = Field(index=True, unique=True)
    name: str
    created_at: datetime = Field(default_factory=_now)


class AgentVersion(SQLModel, table=True):
    """A specific version of an agent within a project (bible §10).

    Maps to one or more ``RecordingRow``s. The ``commit`` is whatever hash the user supplies
    — usually a git SHA, but free-form for non-git workflows.
    """

    __tablename__ = "agent_version"

    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", index=True)
    commit: str = Field(index=True)
    framework: str = "raw"
    label: str | None = None
    created_at: datetime = Field(default_factory=_now)


class RecordingRow(SQLModel, table=True):
    """One row per recording on disk (or imported from OTel)."""

    __tablename__ = "recording"

    id: int | None = Field(default=None, primary_key=True)
    run_id: str = Field(index=True, unique=True)
    agent_version_id: int | None = Field(default=None, foreign_key="agent_version.id", index=True)
    stem: str = Field(index=True)
    path: str
    schema_version: str = "1.0.0"
    n_steps: int = 0
    # Safe-by-default: never *claim* redaction unless a writer explicitly says so.
    # `store_recording` sets this from the Recording's own flag.
    redaction_applied: bool = False
    final_output_json: str | None = None
    created_at: datetime = Field(default_factory=_now)


class RunRow(SQLModel, table=True):
    """One row per replay execution against a scenario (M3 onward)."""

    __tablename__ = "run"

    id: int | None = Field(default=None, primary_key=True)
    baseline_recording_id: int | None = Field(default=None, foreign_key="recording.id", index=True)
    scenario_op: str
    seed: int = 0
    verdict: str = "unknown"
    created_at: datetime = Field(default_factory=_now)


class ReportRow(SQLModel, table=True):
    """One row per ``ReliabilityReport`` written by ``volo run`` / ``volo ci``."""

    __tablename__ = "report"

    id: int | None = Field(default=None, primary_key=True)
    baseline_run_id: str = Field(index=True)
    stem: str = Field(index=True)
    path: str
    agent_name: str | None = None
    verdict: str = "unknown"
    aggregate_json: str = "{}"
    n_scenarios: int = 0
    created_at: datetime = Field(default_factory=_now)


# ── bridge helpers (filesystem ↔ DB) ─────────────────────────────────────────


def store_recording(
    engine: Engine,
    recording: Any,  # volo_core.Recording — typed Any to avoid import cycle
    *,
    path: str,
    stem: str,
    agent_version_id: int | None = None,
) -> RecordingRow:
    """Upsert a ``RecordingRow`` from a Pydantic ``Recording``."""
    import json as _json

    with session(engine) as s:
        existing = s.exec(
            select(RecordingRow).where(RecordingRow.run_id == recording.run_id),
        ).first()
        row = existing or RecordingRow(run_id=recording.run_id, stem=stem, path=path)
        row.agent_version_id = agent_version_id
        row.stem = stem
        row.path = path
        row.schema_version = recording.recording_schema_version
        row.n_steps = len(recording.steps)
        row.redaction_applied = recording.redaction_applied
        row.final_output_json = _json.dumps(recording.final_output, default=str)
        s.add(row)
        s.commit()
        s.refresh(row)
        return row


def store_report(
    engine: Engine,
    report: Any,  # volo_reliability.ReliabilityReport
    *,
    path: str,
    stem: str,
) -> ReportRow:
    """Upsert a ``ReportRow`` from a Pydantic ``ReliabilityReport``."""
    import json as _json

    with session(engine) as s:
        existing = s.exec(
            select(ReportRow).where(ReportRow.baseline_run_id == report.baseline_run_id),
        ).first()
        row = existing or ReportRow(baseline_run_id=report.baseline_run_id, stem=stem, path=path)
        row.path = path
        row.stem = stem
        row.agent_name = report.agent_name
        row.verdict = report.verdict
        row.aggregate_json = _json.dumps(report.aggregate)
        row.n_scenarios = len(report.scenarios)
        s.add(row)
        s.commit()
        s.refresh(row)
        return row


def list_recordings(engine: Engine) -> list[RecordingRow]:
    with session(engine) as s:
        return list(s.exec(select(RecordingRow).order_by(col(RecordingRow.created_at).desc())))


def list_reports(engine: Engine) -> list[ReportRow]:
    with session(engine) as s:
        return list(s.exec(select(ReportRow).order_by(col(ReportRow.created_at).desc())))


__all__ = [
    "AgentVersion",
    "Project",
    "RecordingRow",
    "ReportRow",
    "RunRow",
    "get_engine",
    "init_schema",
    "list_recordings",
    "list_reports",
    "session",
    "store_recording",
    "store_report",
]
