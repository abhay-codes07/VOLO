"""Sim-minutes worker — claims queued jobs, runs the sim, meters, charges quota (M27).

Commercial — see cloud/LICENSE. This is the process a hosted machine (e.g. one Fly.io instance)
runs; it also runs locally against SQLite. Runs each job's reliability suite against the submitted
recording and agent, and stores the resulting report into the workspace's history (M26).

**Safety (ADR-0012 posture):** running a job resolves and executes an agent entrypoint. That is a
code-execution boundary, so it is **off by default** — a job's agent must be in
``VOLO_SIM_AGENT_ALLOWLIST`` (comma-separated) unless ``VOLO_SIM_TRUST_AGENTS=true``. A production
deployment additionally sandboxes the worker (a container per job). A disallowed agent fails the
job with a clear reason rather than executing.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import time
from typing import Any

from sqlalchemy.engine import Engine

from volo_cloud import service, sim_service
from volo_core import Recording
from volo_core.storage import get_engine, init_schema


def agent_allowed(target: str) -> bool:
    if os.environ.get("VOLO_SIM_TRUST_AGENTS", "false").lower() == "true":
        return True
    allow = {
        a.strip() for a in os.environ.get("VOLO_SIM_AGENT_ALLOWLIST", "").split(",") if a.strip()
    }
    return target in allow


def _sim_minutes(duration_s: float) -> int:
    """Bill wall-clock seconds as whole sim-minutes (min 1 for any completed job)."""
    return max(1, math.ceil(duration_s / 60.0))


def run_next_job(engine: Engine, *, duration_s: float | None = None) -> Any:
    """Claim and run one queued job. Returns the finished ``SimJob`` or None if the queue is empty.

    ``duration_s`` overrides wall-clock metering (used by tests for determinism).
    """
    job = sim_service.claim_next_job(engine)
    if job is None:
        return None
    assert job.id is not None  # a persisted, claimed job always has an id

    if not agent_allowed(job.agent):
        return sim_service.fail_job(
            engine,
            job_id=job.id,
            error=f"agent {job.agent!r} is not allowlisted (set VOLO_SIM_AGENT_ALLOWLIST)",
        )

    started = time.perf_counter()
    try:
        from volo_runner import OrchestratorConfig, orchestrate, resolve_agent

        recording = Recording.from_json(job.recording_json)
        agent_input = json.loads(job.agent_input_json) or None
        report = orchestrate(
            recording,
            resolve_agent(job.agent),
            config=OrchestratorConfig(agent_input=agent_input),
        )
    except Exception as exc:
        return sim_service.fail_job(engine, job_id=job.id, error=f"{type(exc).__name__}: {exc}")

    elapsed = duration_s if duration_s is not None else (time.perf_counter() - started)
    # Store the report into the workspace's hosted history (M26).
    service.ingest_reliability_report(engine, workspace_id=job.workspace_id, report=report)
    return sim_service.complete_job(
        engine,
        job_id=job.id,
        sim_minutes=_sim_minutes(elapsed),
        result_run_id=report.baseline_run_id,
        result_verdict=report.verdict,
    )


def run_worker(engine: Engine, *, poll_s: float = 2.0, once: bool = False) -> None:
    """Drain the queue; with ``once`` process at most the currently-queued jobs then stop."""
    while True:
        job = run_next_job(engine)
        if job is None:
            if once:
                return
            time.sleep(poll_s)


def main() -> None:  # pragma: no cover - process entrypoint
    parser = argparse.ArgumentParser(prog="volo-cloud-worker")
    parser.add_argument("--once", action="store_true", help="drain the queue and exit")
    parser.add_argument("--poll", type=float, default=2.0, help="poll interval seconds")
    args = parser.parse_args()
    engine = get_engine()
    init_schema(engine)
    run_worker(engine, poll_s=args.poll, once=args.once)
