"""Cloud service layer — teams, workspaces, API keys, hosted report history (M26).

Commercial — see cloud/LICENSE. Pure functions over a SQLAlchemy engine; the FastAPI app is a
thin shell over these. API keys are stored as a sha256 hash — the plaintext is returned exactly
once at mint time, never persisted.
"""

from __future__ import annotations

import hashlib
import json
import secrets
from typing import Any

from sqlalchemy.engine import Engine
from sqlmodel import Session, col, select

from volo_cloud.models import ApiKey, Membership, Team, Workspace, WorkspaceReport

KEY_PREFIX = "volo_sk_"


def _session(engine: Engine) -> Session:
    # expire_on_commit=False keeps returned rows' attributes readable after the session closes.
    return Session(engine, expire_on_commit=False)


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def create_team(engine: Engine, *, slug: str, name: str, owner: str = "local") -> Team:
    with _session(engine) as s:
        if s.exec(select(Team).where(Team.slug == slug)).first():
            raise ValueError(f"team slug {slug!r} already exists")
        team = Team(slug=slug, name=name)
        s.add(team)
        s.commit()
        s.refresh(team)
        s.add(Membership(team_id=team.id, subject=owner, role="owner"))
        s.commit()
        return team


def create_workspace(engine: Engine, *, team_id: int, slug: str, name: str) -> Workspace:
    with _session(engine) as s:
        if not s.get(Team, team_id):
            raise ValueError(f"team {team_id} not found")
        dup = s.exec(
            select(Workspace).where(Workspace.team_id == team_id, Workspace.slug == slug)
        ).first()
        if dup:
            raise ValueError(f"workspace slug {slug!r} already exists in team {team_id}")
        ws = Workspace(team_id=team_id, slug=slug, name=name)
        s.add(ws)
        s.commit()
        s.refresh(ws)
        return ws


def workspace_team_id(engine: Engine, *, workspace_id: int) -> int | None:
    """The team that owns a workspace (for role checks scoped to the team)."""
    with _session(engine) as s:
        ws = s.get(Workspace, workspace_id)
        return ws.team_id if ws is not None else None


def mint_api_key(engine: Engine, *, workspace_id: int, name: str) -> tuple[ApiKey, str]:
    """Create an API key for a workspace. Returns ``(row, plaintext)`` — plaintext shown once."""
    with _session(engine) as s:
        if not s.get(Workspace, workspace_id):
            raise ValueError(f"workspace {workspace_id} not found")
        plaintext = KEY_PREFIX + secrets.token_hex(24)
        row = ApiKey(
            workspace_id=workspace_id,
            name=name,
            prefix=plaintext[: len(KEY_PREFIX) + 6],
            key_hash=_hash_key(plaintext),
        )
        s.add(row)
        s.commit()
        s.refresh(row)
        return row, plaintext


def resolve_api_key(engine: Engine, key: str) -> ApiKey | None:
    """Return the live (non-revoked) ApiKey for a plaintext key, or None."""
    with _session(engine) as s:
        row = s.exec(select(ApiKey).where(ApiKey.key_hash == _hash_key(key))).first()
        return row if row is not None and not row.revoked else None


def revoke_api_key(engine: Engine, key_id: int) -> bool:
    with _session(engine) as s:
        row = s.get(ApiKey, key_id)
        if row is None:
            return False
        row.revoked = True
        s.add(row)
        s.commit()
        return True


def ingest_report(
    engine: Engine,
    *,
    workspace_id: int,
    baseline_run_id: str,
    agent_name: str | None,
    verdict: str,
    aggregate: dict[str, float],
    n_scenarios: int,
) -> WorkspaceReport:
    """Store a reliability report's summary into a workspace's history."""
    with _session(engine) as s:
        row = WorkspaceReport(
            workspace_id=workspace_id,
            baseline_run_id=baseline_run_id,
            agent_name=agent_name,
            verdict=verdict,
            aggregate_json=json.dumps(aggregate),
            n_scenarios=n_scenarios,
        )
        s.add(row)
        s.commit()
        s.refresh(row)
        return row


def ingest_reliability_report(engine: Engine, *, workspace_id: int, report: Any) -> WorkspaceReport:
    """Convenience: ingest a ``volo_reliability.ReliabilityReport`` object."""
    return ingest_report(
        engine,
        workspace_id=workspace_id,
        baseline_run_id=report.baseline_run_id,
        agent_name=report.agent_name,
        verdict=report.verdict,
        aggregate=dict(report.aggregate),
        n_scenarios=len(report.scenarios),
    )


def list_reports(engine: Engine, *, workspace_id: int) -> list[WorkspaceReport]:
    with _session(engine) as s:
        return list(
            s.exec(
                select(WorkspaceReport)
                .where(WorkspaceReport.workspace_id == workspace_id)
                .order_by(col(WorkspaceReport.created_at).desc())
            )
        )
