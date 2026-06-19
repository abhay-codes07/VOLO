# ADR 0005: Scenario operator taxonomy

- **Status:** accepted
- **Date:** 2026-05-31
- **Deciders:** founder
- **Related:** bible §4 subsystem 3, §9.3

## Context
The Scenario Generator takes a baseline `Recording` and produces "storms in the simulator" —
typed mutations that probe specific failure classes. The taxonomy needs to be (a) small enough
to be auditable, (b) wide enough to surface real production failures, and (c) deterministic so
that a regression report is reproducible.

## Decision
Seven concrete operators, each a subclass of `ScenarioOp` with:
- `name: str` (canonical label, slug-shaped)
- `failure_class: str` (the high-level category the operator probes)
- `seed: int` (defaulted; passed through `Scenario.with_seed(n)`)
- `apply(rec: Recording) -> Recording` (pure function — returns a new Recording, never mutates)

| Operator | Failure class | What it does |
|---|---|---|
| `DropToolResult` | resilience | Removes the response of a random tool step (the tool "returned nothing"). |
| `CorruptField` | robustness | Replaces one leaf field in a tool response with a same-typed but adversarial value. |
| `InjectLatency` | timeout-handling | Bumps `latency_ms` on one step by a configurable factor — exercises retry / timeout code. |
| `AmbiguousUserTurn` | spec-compliance | Replaces the first model_call's prompt with an under-specified version ("do the thing"). |
| `PromptInjection` | security | Embeds a hostile instruction inside a tool response value. |
| `ReorderSteps` | order-sensitivity | Swaps two adjacent tool_calls (when they share a parent). |
| `LongHorizonRepeat` | drift | Duplicates a tool_call segment N times — surfaces accumulation bugs. |

A `Scenario` wraps `(op, seed, params)` so the runner can serialize, log, and reproduce.

## Consequences
- The list is **explicit** — adding an operator means an ADR amendment, which is desirable for
  research reproducibility (cite which operators a report ran).
- Each operator is pure → trivial to test, trivial to compose.
- Operators that can't apply to a given Recording (e.g. `ReorderSteps` on a recording with one
  tool call) skip cleanly and return the original Recording. The runner records `applicable=False`
  for that scenario rather than crashing.

## Alternatives considered
- **LLM-generated scenarios** — interesting later, but non-reproducible and unbounded; ship the
  taxonomy first, layer fuzz-generation on top in M5+.
- **Property-based testing (Hypothesis)** — useful for testing operators themselves; not the
  right primitive for the user-facing scenario library.
