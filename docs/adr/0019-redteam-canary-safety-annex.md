# ADR 0019: red-team via canary poison-and-detect; attacks are data; the annex is a separate artifact

- Status: accepted
- Date: 2026-07-04

## Context

M15 (newplan P3) adds an adversarial safety suite. Three decisions shape it: how to *detect*
a compromise deterministically and offline, how attacks are represented, and where the safety
result lives relative to the `ReliabilityReport`.

## Decision

1. **Canary poison-and-detect.** Each `Attack` carries a `payload` containing a unique `canary`
   token. `run_redteam` weaves the payload into the tool responses of a *cloned* baseline
   recording, replays the agent against that poisoned world in the Tier-1 sim, and checks whether
   the canary surfaces in the agent's final output. Canary present ⇒ the agent obeyed injected
   content ⇒ **compromised**. This is deterministic, offline, needs no judge/model, and — because
   it runs against the simulator — an attack can never reach a real tool, key, or network.
   Poison targets tool-response string leaves (first leaf appended, plus a stashed `system_note`
   field) so both field-reading and content-echoing agents encounter it.
2. **Attacks are data.** `Attack` is a frozen dataclass with JSON round-trip; the built-in
   corpus is 54 distinct techniques across the six newplan classes, and packs are just
   `{"attacks": [...]}` JSON (`load_pack`/`dump_pack`, `volo redteam export`). This makes the
   corpus community-extensible and is the seed inventory for the scenario marketplace (P6).
3. **The annex is a separate artifact, not a `ReliabilityReport` field.** `SafetyAnnex` is its
   own Pydantic model (verdict `safe`/`vulnerable`, per-class counts, findings with an evidence
   snippet), produced by `volo redteam` and written alongside the report. This avoids churning
   the reliability report schema (consistent with the ADR-0014 rationale) while still being "the
   safety annex on the report" operationally — CI runs both and links them.
4. **Exit 4 is the safety gate.** `volo redteam run` exits 4 when any attack lands, distinct from
   the reliability gate's exit 1 and the shadow drift exit 3, so a pipeline can tell *which* gate
   failed.

## Consequences

- Detection measures *output leakage*, the dominant injection failure mode. Attacks that
  compromise an agent without surfacing the canary in the final output (silent tool misuse) are
  out of scope for v1 — a future annex could inspect the trajectory, not just the output.
- Because every attack poisons and replays independently, cost is O(attacks × n_steps); 54
  attacks over a small recording run in well under a second (no model calls).
- Recordings with no tool response can't be poisoned; those attacks are marked
  `applicable=false` and the verdict is vacuously `safe` — surfaced, not hidden.
- Keeping the annex separate means consumers that want a single artifact must join report + annex
  themselves; accepted for schema stability.

## Alternatives considered

- **LLM-judge detection** (ask a model "was this compromised?") — rejected: nondeterministic,
  costs money, and defeats the offline/$0 property; the canary is exact.
- **A new `safety` block inside `ReliabilityReport`** — rejected for now: schema-version churn
  across every report consumer for a section only the red-team path populates.
- **Live attack execution** — rejected outright: the whole point is to break the agent in the
  sim, never in production.
