# ADR 0033: hosted sim-minutes is a DB-backed job queue + worker; metered, hard-capped, agent-gated

- Status: accepted
- Date: 2026-07-08

## Context

M27 sells the one thing Volo legitimately resells: **compute** — hosted Tier-2 simulation too
heavy for a laptop, metered as sim-minutes with a hard cap (bible §11). It builds on the M26
control plane (ADR-0031) and must keep the same properties: runs locally on SQLite with no
accounts, no new paid dependency, and safe-by-default.

## Decision

1. **A job queue in the database, not a broker.** A `SimJob` row (workspace, agent, input,
   recording, status, sim_minutes, result) is the unit of work; `SimQuota` caps a workspace's
   sim-minutes. `claim_next_job` moves the oldest `queued` row to `running`. No Redis/Celery — the
   same SQLite/Postgres engine the control plane already uses. A hosted worker (one Fly.io
   machine) runs `volo-cloud-worker`; locally it's the same loop with `--once`.
2. **Meter at completion, cap at enqueue.** Duration can't be known up front, so **enqueue** is
   refused (HTTP **402**) when the workspace has *no remaining* sim-minutes, and the worker
   **charges** actual usage (`ceil(wall_seconds / 60)`, min 1) to the quota when the job finishes.
   An in-flight job may slightly overshoot; further enqueues are then blocked — a correct, simple
   MVP metering model. Tests inject `duration_s` for determinism.
3. **The worker executes agent code, so it's gated off by default.** Running a job resolves and
   calls an agent entrypoint — a code-execution boundary (ADR-0012). The worker runs a job's agent
   only if it's in `VOLO_SIM_AGENT_ALLOWLIST` (or `VOLO_SIM_TRUST_AGENTS=true`); otherwise the job
   *fails* with a clear reason and is **not charged**. Production additionally sandboxes the worker
   (a container per job) — the allowlist is the code-level gate, the sandbox is the deployment
   gate.
4. **The result flows into M26 history.** A completed job ingests its `ReliabilityReport` into the
   workspace's hosted report history, so sim-minutes and history are one story.

## Consequences

- Fully exercisable locally with `uv run` + SQLite (the worker + a TestClient), so the metered
  paid feature is developed and tested with zero infra — consistent with §11 and ADR-0031.
- DB-as-queue is fine at MVP scale (single worker, low volume); high throughput would want
  `SELECT … FOR UPDATE SKIP LOCKED` (Postgres) or a real broker — a later change behind the same
  `claim_next_job` seam.
- Metering wall-clock means a slow/cold worker bills more; a deployment can swap `_sim_minutes`
  for a work-unit meter without touching the queue or quota logic.
- Refusing at enqueue (not mid-run) keeps the worker simple and the client's failure legible
  (402 before work starts), at the cost of a bounded per-job overshoot.

## Alternatives considered

- **A message broker (Celery/RQ/Redis)** — rejected for the MVP: a new paid/ops dependency for
  volume we don't have; the DB queue matches the control plane's stack and the §11 local-first
  rule.
- **Pre-charge estimated minutes at enqueue** — rejected: duration is unknown before running;
  charging actuals at completion is honest, and the remaining-quota gate prevents runaway spend.
- **Run untrusted agents unsandboxed because it's "just the worker"** — rejected: that's the RCE
  surface ADR-0012 exists to prevent; allowlist-by-default + a documented per-job sandbox is the
  safe posture.
