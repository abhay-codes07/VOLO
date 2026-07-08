"""Audit log — an append-only record of who did what (M30). Commercial — see cloud/LICENSE.

Every management mutation (create team/workspace/key, set quota, role change) writes an
``AuditEvent``. The log is append-only by discipline (no update/delete API) so it can back a
compliance trail.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.engine import Engine
from sqlmodel import Field, Session, SQLModel, col, select


def _now() -> datetime:
    return datetime.now(UTC)


class AuditEvent(SQLModel, table=True):
    __tablename__ = "cloud_audit_event"

    id: int | None = Field(default=None, primary_key=True)
    subject: str = Field(index=True)  # who (auth subject)
    action: str = Field(index=True)  # e.g. "team.create", "quota.set"
    target: str = ""  # what (e.g. "workspace:3")
    team_id: int | None = Field(default=None, index=True)
    at: datetime = Field(default_factory=_now)


def record_audit(
    engine: Engine,
    *,
    subject: str,
    action: str,
    target: str = "",
    team_id: int | None = None,
) -> AuditEvent:
    with Session(engine, expire_on_commit=False) as s:
        ev = AuditEvent(subject=subject, action=action, target=target, team_id=team_id)
        s.add(ev)
        s.commit()
        s.refresh(ev)
        return ev


def list_audit(engine: Engine, *, team_id: int | None = None, limit: int = 200) -> list[AuditEvent]:
    with Session(engine, expire_on_commit=False) as s:
        stmt = select(AuditEvent).order_by(col(AuditEvent.at).desc()).limit(limit)
        if team_id is not None:
            stmt = stmt.where(AuditEvent.team_id == team_id)
        return list(s.exec(stmt))
