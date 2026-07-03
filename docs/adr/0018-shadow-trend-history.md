# ADR 0018: trend history is append-only JSONL; alerts stay exit-code-first

- Status: accepted
- Date: 2026-07-04

## Context

M14 gives the drift sentinel (ADR-0017) a memory and a voice: reliability-over-time for the
dashboard/CLI, and a push alert. The history format is a data contract (the API, dashboard, and
users' tooling read it), so it deserves a recorded decision.

## Decision

1. **History is append-only JSONL** (`./.volo/shadow-history.jsonl`): one
   `{at, snapshot, drift}` line per `volo shadow check`, including the baseline-establishing
   run (`drift: null`). Torn lines are skipped on read, so a crashed run can't poison the
   history. Committable and greppable, consistent with ADR-0017's no-database stance.
2. **Two derived series, computed on read:** `fleet_series` (each dimension averaged across all
   banked traces, per check — the dashboard headline) and `trace_series(run_id)` (one banked
   trace over time). Nothing is precomputed or stored twice.
3. **Alerting stays exit-code-first.** The webhook (`--webhook` / `VOLO_SHADOW_WEBHOOK`) is a
   loud *secondary* path: a Slack-compatible payload (`text` headline + full report under
   `volo`), delivered best-effort — a dead webhook logs a warning and never masks the exit-3
   alert. Stdlib `urllib` only; no HTTP dependency.
4. **Dashboard/API surface:** `GET /shadow/history` returns `{checks: fleet_series, corpus:
   bank inventory}`; `GET /shadow/history/{run_id}` returns one trace's series. The `/shadow`
   web screen renders fleet-average sparklines per dimension plus drifted-night chips, reusing
   the CI sparkline component.

## Consequences

- The history file grows without bound (~1–2 KB per check per 10 traces); rotation/compaction
  is deliberately deferred until a real corpus shows the growth rate. Append-only means
  rotation is a safe external `mv`.
- Averaging the fleet hides a single trace regressing among many healthy ones in the *chart*;
  the alert does not average — `compare` runs per trace, so the exit code still fires. The
  per-trace series exists for the drill-down.
- Slack compatibility via `text` keeps zero config for the most common webhook; consumers
  needing richer formats read the `volo` key.

## Alternatives considered

- **SQLite for history** — rejected for now: the query needs (append, scan) fit JSONL; SQLite
  adds locking/migration surface for no current query we can't do in one pass.
- **Alert-only-webhook (no exit code change)** — rejected: CI schedulers act on exit codes;
  webhooks fail silently.
- **Storing derived series** — rejected: two sources of truth; recompute is O(history) and fast.
