"""Cloud control-plane tables (M26). Commercial — see cloud/LICENSE.

Teams own workspaces; workspaces hold hosted reliability-report history and are accessed via
API keys. Tables are prefixed ``cloud_*`` so they coexist with the OSS schema on one engine.
Runs on SQLite locally (zero accounts) and Postgres in production via ``VOLO_DB_URL``.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


def _now() -> datetime:
    return datetime.now(UTC)


class Team(SQLModel, table=True):
    __tablename__ = "cloud_team"

    id: int | None = Field(default=None, primary_key=True)
    slug: str = Field(index=True, unique=True)
    name: str
    created_at: datetime = Field(default_factory=_now)


class Workspace(SQLModel, table=True):
    __tablename__ = "cloud_workspace"

    id: int | None = Field(default=None, primary_key=True)
    team_id: int = Field(foreign_key="cloud_team.id", index=True)
    slug: str = Field(index=True)
    name: str
    created_at: datetime = Field(default_factory=_now)


class Membership(SQLModel, table=True):
    __tablename__ = "cloud_membership"

    id: int | None = Field(default=None, primary_key=True)
    team_id: int = Field(foreign_key="cloud_team.id", index=True)
    subject: str = Field(index=True)  # user id from the auth vendor (or "local" in dev)
    role: str = "member"  # owner | member
    created_at: datetime = Field(default_factory=_now)


class ApiKey(SQLModel, table=True):
    __tablename__ = "cloud_api_key"

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="cloud_workspace.id", index=True)
    name: str
    prefix: str = Field(index=True)  # first chars, shown in listings
    key_hash: str = Field(index=True)  # sha256 of the full key; the key itself is shown once
    revoked: bool = False
    created_at: datetime = Field(default_factory=_now)


class WorkspaceReport(SQLModel, table=True):
    """A reliability report ingested into a workspace's hosted history."""

    __tablename__ = "cloud_workspace_report"

    id: int | None = Field(default=None, primary_key=True)
    workspace_id: int = Field(foreign_key="cloud_workspace.id", index=True)
    baseline_run_id: str = Field(index=True)
    agent_name: str | None = None
    verdict: str = "unknown"
    aggregate_json: str = "{}"
    n_scenarios: int = 0
    created_at: datetime = Field(default_factory=_now)
