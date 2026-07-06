# ADR 0023: recording persistence v2 — gzip + a migration seam; schema stays additive

- Status: accepted
- Date: 2026-07-06

## Context

M19 (v2.0 hardening) has three fronts: replay performance, recording-format evolution, and docs.
The format decisions are the ones that outlive the milestone — how recordings compress, and how a
future schema change avoids breaking every recording already on disk.

## Decision

1. **Compression is a transparent capability, not a format change.** `volo_core.persistence`
   adds `save_recording` / `load_recording` that gzip when the path ends in `.gz` and otherwise
   behave exactly as before. The on-disk JSON is unchanged; `.json.gz` is just the same bytes
   compressed. `RecorderConfig.compress` opts a recorder in (writes `<run_id>.json.gz`). Banked
   corpora and long recordings compress ~5-15× with zero schema impact.
2. **Schema evolution is additive-first with an explicit migration seam.** The recording schema
   stays `1.0.0` — this release adds *no* breaking field. The policy (enforced by the seam):
   - **Additive** changes (new optional field) are backward-compatible and do **not** bump the
     version; older readers ignore unknown-but-optional data via the model defaults.
   - **Breaking** changes bump the version **and** ship a `register_migration(from, to, fn)` that
     upgrades a raw recording dict one step. `load_recording` walks the chain to the current
     version *before* validation, so old recordings keep loading.
   - `Recording.from_json` stays **strict** (current version only) for internal round-trips;
     `load_recording` is the **tolerant** front door for anything read off disk.
   Migration functions operate on the raw dict (pre-Pydantic), are pure, and are cycle-checked.
3. **Performance is measured and guarded, not assumed.** `benchmarks/replay_throughput.py` times
   the Tier-1 cache build and replay; a test asserts end-to-end throughput stays above a generous
   10k-steps/min floor. Measured ≫ 5M steps/min, so the target is met with no code change — the
   guard exists to catch a future order-of-magnitude regression, and no premature optimization was
   added.

## Consequences

- Callers that read recordings off disk should prefer `load_recording` over
  `Recording.from_json(path.read_text())` to get gzip + migration for free; existing call sites
  keep working (plain JSON is a subset). Migrating every loader is deferred, not required.
- Keeping the schema at `1.0.0` means the migration chain is currently empty — the seam is
  infrastructure for the *next* breaking change, validated by tests with a synthetic migration.
- `recording_header` reads metadata + step count without validating every `Step`, so listing a
  large corpus is cheap; it trusts the file shape (no validation), appropriate for display only.
- gzip is stdlib — no new dependency, consistent with the bible's zero-dep-where-possible stance.

## Alternatives considered

- **A new binary/columnar format** (parquet, msgpack) — rejected: loses the human-diffable JSON
  that makes recordings reviewable in PRs (bible §9.1); gzip keeps diffability (decompress) while
  solving size.
- **A hard version bump now to "2.0.0"** — rejected: nothing in the schema actually changed;
  bumping without a breaking change would force a no-op migration and churn every consumer.
- **True streaming parse (ijson)** — deferred: needs a dependency for a case (recordings too big
  to fit in memory) we haven't hit; `recording_header` covers cheap inspection meanwhile.
