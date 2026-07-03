# ADR 0017: shadow corpus is content-addressed and redacted-at-ingest; drift = surface deltas vs a snapshot

- Status: accepted
- Date: 2026-07-03

## Context

M13 closes the record→replay loop in production: sampled traces become a permanent regression
corpus, replayed nightly. Three decisions with long shadows: the corpus identity/dedup rule,
where redaction happens, and what "drift" formally means.

## Decision

1. **Corpus identity is a content digest** (`sha256` over the step payloads + final output,
   ignoring run ids, step ids, and timestamps). Re-pulling an overlapping production window is
   idempotent; the same incident adopted twice is a no-op. The bank is a plain directory of
   Recording JSON files plus an `index.json` — committable, diffable, no database.
2. **Redaction always runs at ingest, before anything touches disk** (`pull` unconditionally;
   `adopt` unless the file is already marked `redaction_applied`). Banked traces are fixtures
   people commit to repos; an unredacted corpus must be unrepresentable.
3. **Drift is defined against a snapshot, not recomputed history.** `snapshot` replays every
   corpus entry through the full adversarial scenario suite (`orchestrate`) and keeps each
   entry's aggregate reliability dimensions + verdict as plain JSON. `compare(baseline,
   current, threshold)` yields a finding when a dimension drops by more than `threshold`
   (default 0.05) or a verdict flips ship → no_ship. Improvements and new/missing corpus
   entries are reported but are not alerts.
4. **The alert is the exit code.** `volo shadow check` exits 3 on drift (0 = quiet, 2 = empty
   corpus), so any scheduler — the shipped `examples/workflows/volo-nightly.yml`, cron, Jenkins —
   can page without parsing output. The first run establishes the baseline;
   `--update-baseline` accepts an intentional change as the new normal.

## Consequences

- Committing the corpus + baseline into git gives full provenance of "what regressed when" for
  free; large corpora may later need the object-store path (bible §5), which slots behind
  `CorpusBank` without API change.
- Digest-dedup means a trace whose *content* legitimately changed (same user journey, new
  correct answer) banks as a new entry rather than replacing the old one — curation
  (retire/expire) is deliberately left to M14.
- Verdict flips no_ship → ship (improvement) don't alert; teams that want symmetric alerting
  can diff the JSON reports.
- `snapshot` inherits `orchestrate`'s determinism (seeded scenarios, Tier-1 replay), so a quiet
  night is byte-reproducible and a finding is always replayable.

## Alternatives considered

- **Dedup by run_id** — rejected: production exporters regenerate ids; the same traffic would
  bank endlessly.
- **Redaction as a separate `volo shadow scrub` step** — rejected: an unscrubbed bank would be
  a footgun the security review (ADR-0012) exists to prevent.
- **Alert on any aggregate change** — rejected: sub-threshold jitter (judge heuristics,
  histogram ties) would page nightly; a tolerance with a verdict-flip override captures both
  slow decay and cliff-edge failures.
