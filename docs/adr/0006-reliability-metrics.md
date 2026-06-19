# ADR 0006: Reliability metrics — DFAH-aligned, four orthogonal dimensions

- **Status:** accepted
- **Date:** 2026-05-31
- **Deciders:** founder
- **Related:** bible §9.4, §2.2; ADR-0003, ADR-0005

## Context
The bible (citing DFAH research) requires that we **never collapse reliability to one number**:
determinism and accuracy are uncorrelated, and a single score hides the difference between
"consistent borderline" and "occasionally catastrophic." We need four metrics, computed
independently and presented together, plus a clearly-defined verdict function on top.

## Decision
Four metrics, each ∈ `[0, 1]` (higher is better):

1. **Trajectory determinism** — across `N` repeated runs of the agent on the same scenario, the
   fraction whose trajectory shape matches the most-common shape. "Shape" = the ordered tuple of
   `(step.type, payload-key)` summaries: `(model_call, provider/model)`, `(tool_call, tool)`,
   `(decision, label)`. This is robust to value-level noise but catches "took a different tool".
2. **Decision determinism** — fraction of runs whose `final_output` equals the most-common
   final output (deep equality on canonical JSON).
3. **Faithfulness** — fraction of runs whose final output is "grounded" in evidence: every literal
   value in `final_output` that is a primitive string/number must appear somewhere in a recorded
   tool response or model response, OR be derivable as a sum/product of recorded numbers. The
   Tier-1 implementation is a deterministic heuristic (no LLM). The Tier-2 implementation
   (M2 later) will use a local judge model via `volo-models`.
4. **Consistency-under-repetition** — `1 - dispersion`, where dispersion is the fraction of unique
   `final_output`s among the `N` runs (a "perfectly consistent" agent has 1 unique output → score
   1.0; "every run different" → score near 0). Reported alongside the histogram so consumers can
   distinguish "consistent 50% pass" from "catastrophic on some runs".

### Aggregation
A `ReliabilityReport` has per-scenario sub-reports plus an aggregate. Aggregate score per metric
is the **5th percentile** across scenarios (we ship on worst-case, not average).

### Verdict
`verdict ∈ {"ship", "no_ship"}`. Compute as:
```
ship  iff  all four aggregates >= fail_under  AND  no individual scenario score == 0.0
```
Default `fail_under = 0.9` (matches the CLI default).

## Consequences
- Metrics are cheap, deterministic, and explainable — no LLM required for v1.
- Faithfulness as a deterministic heuristic will miss cases real LLM judges catch. That's
  acceptable as a v1 floor; the design slot is reserved for swapping to an LLM judge via
  `volo-models`.
- The 5th-percentile aggregation is a deliberate choice: averaging hides the long tail. If
  a project wants a different aggregator we expose `aggregator: "p5" | "mean" | "median"`.

## Alternatives considered
- **Single composite score** — explicitly forbidden by the research basis (DFAH). Rejected.
- **LLM judge from day 1** — adds a hard dependency on Ollama or frontier APIs before the rest of
  the pipeline is shipping. Defer to M2 swap-in.
- **Trajectory edit-distance instead of shape-match** — softer and arguably better, but harder to
  explain in a single test failure. Defer.
