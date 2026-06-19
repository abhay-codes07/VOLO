# ADR 0010: Tier-2 fidelity benchmark methodology

- **Status:** accepted
- **Date:** 2026-06-01
- **Deciders:** founder
- **Related:** ADR-0009 (Tier-2 algorithm), bible §9.2

## Context

ADR-0009 commits us to fidelity targets — ≥75% for Tier-2 (a) alone, ≥95% for (a)+(b),
≥99% stretch — but doesn't pin down what "fidelity" means in our codebase. Without a
methodology, the targets are unfalsifiable.

The MIRAGE paper (the source of the 62% / 99% numbers) measures fidelity as the fraction
of un-recorded inputs for which the simulator's response, fed back into the agent, results
in the same downstream observable behaviour as a live call would have.

We need a Volo-specific concretization of that idea — narrow enough to be implementable on
day one, broad enough to actually catch regressions.

## Decision

Fidelity is measured by **head-to-head comparison of live-mode and simulator-mode runs of
the same agent on a sample of held-out inputs**, with output equivalence judged at three
levels.

### Sampling

For a target agent (today: `examples/research_agent`):

1. Author a **seed set** of 5 recorded queries (cache-hit baseline).
2. Generate a **held-out set** of N=20 fresh queries by mutating the seed queries with a
   seeded RNG. Each fresh query exercises the same tool schemas but with inputs the
   simulator has *not* seen.

### Comparison

For each held-out query `q`:

* **Live result** `L(q)` — agent run with `_FakeWeb` (the ground-truth tool registry).
* **Sim result** `S(q)` — same agent run under `Tier2Replayer` built from the seed
  recordings, with the synthesizer chain `[SourceInformedSynthesizer(),
  OllamaConstrainedSynthesizer()]`.

### Equivalence levels

A run pair is **identical** when `canonical_json(L(q)) == canonical_json(S(q))`.
A run pair is **shape-equivalent** when the trajectory shapes match (per
`agentsim_reliability.metrics.trajectory_shape`) AND the final output passes a per-field
type check against the agent's declared output schema.
A run pair is **flagged** when `S(q)` raises `Tier2Miss` — the simulator refused to
hallucinate.

**Fidelity** = `identical / N`.
**Soft fidelity** = `(identical + shape_equivalent) / N`.
**Flagged rate** = `flagged / N`.

A simulator that returns the wrong answer is **strictly worse than one that flags** — a
flagged result is signal, a wrong result is noise. The verdict function consequently
favours flagging over wrong: if `wrong > 0`, the benchmark verdict is `degraded` regardless
of `identical` count.

### Targets per ADR-0009

| Configuration                              | Fidelity target |
|---|---|
| Tier-2 (a) only — Ollama constrained gen    | ≥ 75% |
| Tier-2 (a) + (b) — source-informed first    | ≥ 95% |
| Stretch — full source-informed coverage     | ≥ 99% |

The benchmark must be **deterministic**: the seeded mutator + seeded synthesizer chain
should produce identical fidelity numbers across runs. Numbers go into the CHANGELOG.

### Harness location

`tests/test_research_agent_fidelity.py` runs the benchmark as a test that asserts on the
targets above. CI runs it as `pytest -m fidelity`. The harness uses the existing
`research_agent` and its `tools.json` source-hints — no benchmark-specific fixtures.

## Consequences

- **Easy:** the benchmark is just another pytest. Numbers are reproducible.
- **Easy:** the verdict's "wrong > 0 → degraded" rule means we never accidentally accept a
  regression that increases hallucinated outputs.
- **Hard:** the held-out mutator is a single function — its quality bounds the benchmark's
  signal. A pure shadow synthesizer can pass even a weak mutator. Replace this when we
  ship M7 framework integrations with real-world traces.
- **Hard:** the trajectory-shape equivalence check rules out evaluating soft regressions
  where the agent does more steps but lands on the right answer. Acceptable trade — we
  optimise for determinism first.

## Alternatives considered

- **LLM-judged equivalence.** Too non-deterministic for a fidelity *floor*; defer to a
  separate "soft fidelity" channel under the existing `OllamaJudge`.
- **Per-tool fidelity rather than per-agent.** Simpler to measure but doesn't capture the
  compounding-error problem the bible §9.2 calls out. Rejected.
- **N = 100 instead of 20.** Higher confidence, slower test. Defer to a `--slow` mode
  once we have CI time to burn.
