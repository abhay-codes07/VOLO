"""Cloud control-plane FastAPI app (M26). Commercial — see cloud/LICENSE.

Management routes (create team / workspace / key) are gated by the OSS ``require_principal`` seam
— open locally, and denied to anonymous callers when ``VOLO_REQUIRE_AUTH=true`` (where a
deployment swaps ``get_principal`` for a real auth vendor, e.g. Clerk/Supabase). Data routes
(read/ingest a workspace's reports) are gated by a **workspace API key** (``X-Volo-Key`` header).

Everything runs on SQLite locally with zero accounts and on Postgres via ``VOLO_DB_URL``.
"""

from __future__ import annotations

from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

from volo_api.auth import Principal, auth_required
from volo_cloud import audit, rbac, service, sim_service
from volo_cloud.models import ApiKey
from volo_core.storage import get_engine, init_schema

_engine = None


def _get_engine() -> Any:
    global _engine
    if _engine is None:
        _engine = get_engine()
        init_schema(_engine)
    return _engine


def authed_principal(authorization: str | None = Header(default=None)) -> Principal:
    """Resolve the caller via the vendor-neutral JWT seam (M30), then apply the auth-required gate.

    No ``VOLO_JWT_SECRET`` → anonymous (local dev). A valid HS256 bearer token → an authenticated
    principal. When ``VOLO_REQUIRE_AUTH=true``, anonymous is denied.
    """
    try:
        principal = rbac.jwt_principal(authorization)
    except rbac.AccessDenied as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    if auth_required() and principal.is_anonymous:
        raise HTTPException(status_code=401, detail="authentication required")
    return principal


def _enforce_role(principal: Principal, team_id: int, minimum: str) -> None:
    try:
        rbac.require_role(
            _get_engine(), subject=principal.subject, team_id=team_id, minimum=minimum
        )
    except rbac.AccessDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


def require_api_key(x_volo_key: str | None = Header(default=None)) -> ApiKey:
    """Resolve the workspace API key from ``X-Volo-Key``; 401 if missing/invalid."""
    if not x_volo_key:
        raise HTTPException(status_code=401, detail="missing X-Volo-Key")
    key = service.resolve_api_key(_get_engine(), x_volo_key)
    if key is None:
        raise HTTPException(status_code=401, detail="invalid or revoked API key")
    return key


class TeamIn(BaseModel):
    slug: str
    name: str


class WorkspaceIn(BaseModel):
    slug: str
    name: str


class KeyIn(BaseModel):
    name: str


class ReportIn(BaseModel):
    baseline_run_id: str
    agent_name: str | None = None
    verdict: str = "unknown"
    aggregate: dict[str, float] = {}
    n_scenarios: int = 0


class SimJobIn(BaseModel):
    agent: str
    agent_input: dict[str, Any] = {}
    recording: dict[str, Any]


class QuotaIn(BaseModel):
    minutes: int


class MemberIn(BaseModel):
    subject: str
    role: str


def create_cloud_app() -> FastAPI:
    app = FastAPI(title="Volo Cloud", version="0.1.0", description="Commercial control plane.")

    @app.get("/cloud/healthz")
    def healthz() -> dict[str, Any]:
        return {"status": "ok", "plane": "cloud"}

    @app.post("/cloud/teams")
    def create_team(
        body: TeamIn, principal: Principal = Depends(authed_principal)
    ) -> dict[str, Any]:
        try:
            team = service.create_team(
                _get_engine(), slug=body.slug, name=body.name, owner=principal.subject
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        audit.record_audit(
            _get_engine(),
            subject=principal.subject,
            action="team.create",
            target=f"team:{team.id}",
            team_id=team.id,
        )
        return {"id": team.id, "slug": team.slug, "name": team.name}

    @app.post("/cloud/teams/{team_id}/workspaces")
    def create_workspace(
        team_id: int, body: WorkspaceIn, principal: Principal = Depends(authed_principal)
    ) -> dict[str, Any]:
        _enforce_role(principal, team_id, "admin")
        try:
            ws = service.create_workspace(
                _get_engine(), team_id=team_id, slug=body.slug, name=body.name
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        audit.record_audit(
            _get_engine(),
            subject=principal.subject,
            action="workspace.create",
            target=f"workspace:{ws.id}",
            team_id=team_id,
        )
        return {"id": ws.id, "team_id": ws.team_id, "slug": ws.slug, "name": ws.name}

    @app.post("/cloud/workspaces/{workspace_id}/keys")
    def create_key(
        workspace_id: int, body: KeyIn, principal: Principal = Depends(authed_principal)
    ) -> dict[str, Any]:
        team_id = service.workspace_team_id(_get_engine(), workspace_id=workspace_id)
        if team_id is None:
            raise HTTPException(status_code=404, detail=f"workspace {workspace_id} not found")
        _enforce_role(principal, team_id, "admin")
        try:
            row, plaintext = service.mint_api_key(
                _get_engine(), workspace_id=workspace_id, name=body.name
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        audit.record_audit(
            _get_engine(),
            subject=principal.subject,
            action="key.create",
            target=f"workspace:{workspace_id}",
            team_id=team_id,
        )
        # plaintext is returned exactly once and never stored
        return {"id": row.id, "name": row.name, "prefix": row.prefix, "key": plaintext}

    @app.get("/cloud/workspaces/{workspace_id}/reports")
    def list_reports(
        workspace_id: int, key: ApiKey = Depends(require_api_key)
    ) -> list[dict[str, Any]]:
        if key.workspace_id != workspace_id:
            raise HTTPException(status_code=403, detail="key does not grant this workspace")
        return [
            {
                "baseline_run_id": r.baseline_run_id,
                "agent_name": r.agent_name,
                "verdict": r.verdict,
                "aggregate": _load(r.aggregate_json),
                "n_scenarios": r.n_scenarios,
                "created_at": r.created_at.isoformat(),
            }
            for r in service.list_reports(_get_engine(), workspace_id=workspace_id)
        ]

    @app.post("/cloud/workspaces/{workspace_id}/reports")
    def ingest_report(
        workspace_id: int, body: ReportIn, key: ApiKey = Depends(require_api_key)
    ) -> dict[str, Any]:
        if key.workspace_id != workspace_id:
            raise HTTPException(status_code=403, detail="key does not grant this workspace")
        row = service.ingest_report(
            _get_engine(),
            workspace_id=workspace_id,
            baseline_run_id=body.baseline_run_id,
            agent_name=body.agent_name,
            verdict=body.verdict,
            aggregate=body.aggregate,
            n_scenarios=body.n_scenarios,
        )
        return {"id": row.id, "baseline_run_id": row.baseline_run_id, "verdict": row.verdict}

    # ── hosted Tier-2 sim-minutes (M27) ──────────────────────────────────────

    @app.get("/cloud/workspaces/{workspace_id}/quota")
    def get_quota(workspace_id: int, key: ApiKey = Depends(require_api_key)) -> dict[str, Any]:
        _scope(key, workspace_id)
        q = sim_service.get_or_create_quota(_get_engine(), workspace_id=workspace_id)
        return {
            "sim_minute_quota": q.sim_minute_quota,
            "sim_minutes_used": q.sim_minutes_used,
            "remaining": q.remaining,
        }

    @app.put("/cloud/workspaces/{workspace_id}/quota")
    def set_quota(
        workspace_id: int, body: QuotaIn, principal: Principal = Depends(authed_principal)
    ) -> dict[str, Any]:
        team_id = service.workspace_team_id(_get_engine(), workspace_id=workspace_id)
        if team_id is None:
            raise HTTPException(status_code=404, detail=f"workspace {workspace_id} not found")
        _enforce_role(principal, team_id, "admin")
        q = sim_service.set_quota(_get_engine(), workspace_id=workspace_id, minutes=body.minutes)
        audit.record_audit(
            _get_engine(),
            subject=principal.subject,
            action="quota.set",
            target=f"workspace:{workspace_id}",
            team_id=team_id,
        )
        return {"sim_minute_quota": q.sim_minute_quota, "sim_minutes_used": q.sim_minutes_used}

    # ── RBAC members + audit log (M30) ───────────────────────────────────────

    @app.post("/cloud/teams/{team_id}/members")
    def set_member(
        team_id: int, body: MemberIn, principal: Principal = Depends(authed_principal)
    ) -> dict[str, Any]:
        _enforce_role(principal, team_id, "owner")
        try:
            m = rbac.set_member_role(
                _get_engine(), team_id=team_id, subject=body.subject, role=body.role
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        audit.record_audit(
            _get_engine(),
            subject=principal.subject,
            action="member.set_role",
            target=f"{body.subject}={body.role}",
            team_id=team_id,
        )
        return {"team_id": m.team_id, "subject": m.subject, "role": m.role}

    @app.get("/cloud/teams/{team_id}/audit")
    def list_team_audit(
        team_id: int, principal: Principal = Depends(authed_principal)
    ) -> list[dict[str, Any]]:
        _enforce_role(principal, team_id, "member")
        return [
            {"subject": e.subject, "action": e.action, "target": e.target, "at": e.at.isoformat()}
            for e in audit.list_audit(_get_engine(), team_id=team_id)
        ]

    @app.post("/cloud/workspaces/{workspace_id}/sim-jobs")
    def enqueue_sim_job(
        workspace_id: int, body: SimJobIn, key: ApiKey = Depends(require_api_key)
    ) -> dict[str, Any]:
        _scope(key, workspace_id)
        try:
            job = sim_service.enqueue_job(
                _get_engine(),
                workspace_id=workspace_id,
                agent=body.agent,
                agent_input=body.agent_input,
                recording=body.recording,
            )
        except sim_service.QuotaExceeded as exc:
            raise HTTPException(status_code=402, detail=str(exc)) from exc
        return {"id": job.id, "status": job.status}

    @app.get("/cloud/workspaces/{workspace_id}/sim-jobs")
    def list_sim_jobs(
        workspace_id: int, key: ApiKey = Depends(require_api_key)
    ) -> list[dict[str, Any]]:
        _scope(key, workspace_id)
        return [
            _job_dict(j) for j in sim_service.list_jobs(_get_engine(), workspace_id=workspace_id)
        ]

    @app.get("/cloud/workspaces/{workspace_id}/sim-jobs/{job_id}")
    def get_sim_job(
        workspace_id: int, job_id: int, key: ApiKey = Depends(require_api_key)
    ) -> dict[str, Any]:
        _scope(key, workspace_id)
        job = sim_service.get_job(_get_engine(), job_id=job_id)
        if job is None or job.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail=f"sim job {job_id} not found")
        return _job_dict(job)

    return app


def _scope(key: ApiKey, workspace_id: int) -> None:
    if key.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="key does not grant this workspace")


def _job_dict(job: Any) -> dict[str, Any]:
    return {
        "id": job.id,
        "agent": job.agent,
        "status": job.status,
        "sim_minutes": job.sim_minutes,
        "result_run_id": job.result_run_id,
        "result_verdict": job.result_verdict,
        "error": job.error,
    }


def _load(raw: str) -> dict[str, Any]:
    import json

    try:
        return dict(json.loads(raw))
    except (ValueError, TypeError):
        return {}


app = create_cloud_app()
