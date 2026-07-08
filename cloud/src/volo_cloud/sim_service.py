"""Sim-job queue + quota service (M27). Commercial — see cloud/LICENSE.

Pure functions over the engine. Enqueue is refused when the workspace has no remaining
sim-minutes (the hard cap); the worker charges actual usage at completion.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.engine import Engine
from sqlmodel import Session, col, select

from volo_cloud.sim import DEFAULT_QUOTA_MINUTES, SimJob, SimQuota


class QuotaExceeded(RuntimeError):
    """Raised when a workspace has no remaining sim-minutes."""


def _session(engine: Engine) -> Session:
    return Session(engine, expire_on_commit=False)


def get_or_create_quota(engine: Engine, *, workspace_id: int) -> SimQuota:
    with _session(engine) as s:
        row = s.exec(select(SimQuota).where(SimQuota.workspace_id == workspace_id)).first()
        if row is None:
            row = SimQuota(workspace_id=workspace_id, sim_minute_quota=DEFAULT_QUOTA_MINUTES)
            s.add(row)
            s.commit()
            s.refresh(row)
        return row


def set_quota(engine: Engine, *, workspace_id: int, minutes: int) -> SimQuota:
    with _session(engine) as s:
        row = s.exec(select(SimQuota).where(SimQuota.workspace_id == workspace_id)).first()
        if row is None:
            row = SimQuota(workspace_id=workspace_id)
        row.sim_minute_quota = max(0, minutes)
        s.add(row)
        s.commit()
        s.refresh(row)
        return row


def enqueue_job(
    engine: Engine,
    *,
    workspace_id: int,
    agent: str,
    agent_input: dict[str, Any] | None,
    recording: dict[str, Any],
) -> SimJob:
    """Queue a sim job. Refuses when the workspace's sim-minute quota is exhausted."""
    quota = get_or_create_quota(engine, workspace_id=workspace_id)
    if quota.remaining <= 0:
        raise QuotaExceeded(
            f"workspace {workspace_id} has no sim-minutes remaining "
            f"({quota.sim_minutes_used}/{quota.sim_minute_quota})"
        )
    with _session(engine) as s:
        job = SimJob(
            workspace_id=workspace_id,
            agent=agent,
            agent_input_json=json.dumps(agent_input or {}),
            recording_json=json.dumps(recording),
        )
        s.add(job)
        s.commit()
        s.refresh(job)
        return job


def claim_next_job(engine: Engine) -> SimJob | None:
    """Atomically move the oldest queued job to ``running`` and return it (or None)."""
    with _session(engine) as s:
        job = s.exec(
            select(SimJob).where(SimJob.status == "queued").order_by(col(SimJob.created_at))
        ).first()
        if job is None:
            return None
        from volo_cloud.sim import _now

        job.status = "running"
        job.started_at = _now()
        s.add(job)
        s.commit()
        s.refresh(job)
        return job


def complete_job(
    engine: Engine,
    *,
    job_id: int,
    sim_minutes: int,
    result_run_id: str | None,
    result_verdict: str | None,
) -> SimJob:
    """Mark a job done and charge its sim-minutes to the workspace quota."""
    from volo_cloud.sim import _now

    with _session(engine) as s:
        job = s.get(SimJob, job_id)
        if job is None:
            raise ValueError(f"job {job_id} not found")
        job.status = "done"
        job.sim_minutes = sim_minutes
        job.result_run_id = result_run_id
        job.result_verdict = result_verdict
        job.finished_at = _now()
        s.add(job)
        quota = s.exec(select(SimQuota).where(SimQuota.workspace_id == job.workspace_id)).first()
        if quota is not None:
            quota.sim_minutes_used += sim_minutes
            s.add(quota)
        s.commit()
        s.refresh(job)
        return job


def fail_job(engine: Engine, *, job_id: int, error: str) -> SimJob:
    from volo_cloud.sim import _now

    with _session(engine) as s:
        job = s.get(SimJob, job_id)
        if job is None:
            raise ValueError(f"job {job_id} not found")
        job.status = "failed"
        job.error = error
        job.finished_at = _now()
        s.add(job)
        s.commit()
        s.refresh(job)
        return job


def get_job(engine: Engine, *, job_id: int) -> SimJob | None:
    with _session(engine) as s:
        return s.get(SimJob, job_id)


def list_jobs(engine: Engine, *, workspace_id: int) -> list[SimJob]:
    with _session(engine) as s:
        return list(
            s.exec(
                select(SimJob)
                .where(SimJob.workspace_id == workspace_id)
                .order_by(col(SimJob.created_at).desc())
            )
        )
