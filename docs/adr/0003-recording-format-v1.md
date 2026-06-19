# ADR 0003: Recording format v1

- **Status:** accepted
- **Date:** 2026-05-31
- **Deciders:** founder
- **Related:** bible §9.1, ADR-0001

## Context
The Recording is the central data structure: every other subsystem either produces or consumes it.
We need a format that is human-diffable (so a PR reviewer can see what changed), versioned (so we
can evolve without breaking old recordings), framework-agnostic (LangGraph and CrewAI both fit),
and amenable to OTel-style span import later.

## Decision
- Pydantic v2 models in `packages/volo-core/src/volo_core/recording.py`.
- Top-level model `Recording` with required fields: `recording_schema_version` (semver string,
  starts at `"1.0.0"`), `run_id` (UUID v7 string), `agent_meta` (`RunMeta`), `created_at`
  (ISO-8601 UTC), `redaction_applied` (bool), `steps` (ordered list of `Step`), `final_output`
  (free-form JSON), `env_snapshot` (optional), `tool_specs` (optional list of `ToolSpec`).
- `Step` is a discriminated union over `type ∈ {"model_call", "tool_call", "decision"}` with a
  common envelope: `step_id`, `parent_id` (nullable, enables branching), `started_at`, `latency_ms`,
  `tokens` (optional), `cost_usd` (optional), and a `type`-specific `input` / `output` payload.
- Serialization: JSON only at v1. (Protobuf/Arrow can come later in a v2 ADR for large recordings.)
- Storage: pretty-printed JSON to disk, one file per recording, at
  `./.volo/recordings/<run_id>.json` in local mode.

## Consequences
- **Easy:** human-readable diffs, trivial to load in tests, no codegen pipeline.
- **Hard:** very large recordings (multi-MB) will be slow to load. Acceptable for v1; revisit when
  someone hits the wall.
- We must write a migration path the first time we bump `recording_schema_version`. Migrations
  live in `volo-core/migrations/` (file-per-version).

## Alternatives considered
- **OTel JSON directly** — too verbose, too tied to OTel semantics. We import from OTel into our
  schema instead.
- **Protobuf** — fast, compact, but kills human-diffability and adds a codegen step. Defer.
- **JSONL (one step per line)** — better for streaming, worse for git-diff and inspection. Defer.
