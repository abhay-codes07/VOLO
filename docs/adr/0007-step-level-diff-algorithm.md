# ADR 0007: Step-level diff algorithm — "git bisect for agents"

- **Status:** accepted
- **Date:** 2026-05-31
- **Deciders:** founder
- **Related:** bible §4 subsystem 6, §9.5

## Context
A core promise of Volo is **root-cause attribution**: when CI fails, point at the exact step
in the trajectory (and ideally the commit) that broke reliability. The MVP shipping in M4 covers
the step-level part. Git-history bisect is deferred but the interface is reserved.

## Decision
A `Diff` is a typed report comparing two `Recording`s (baseline vs candidate):

```python
class Diff(BaseModel):
    baseline_run_id: str
    candidate_run_id: str
    first_diverging_step: int | None       # index, or None if trajectories are identical
    aligned_steps: list[StepDiff]          # one entry per aligned position
    summary: str                            # human-readable headline
```

`StepDiff` carries `kind ∈ {"same", "added", "removed", "changed"}` plus per-side payload
summaries for rendering.

Algorithm — **two-stage**:

1. **Shape alignment** via the LCS (longest common subsequence) of the trajectory *shapes*
   (`(step_type, identity)` tuples — same definition as in `volo_reliability.metrics`).
   This places same-shape steps next to each other and surfaces added/removed steps cleanly.
2. **Payload comparison** on aligned (same-shape) steps: canonical-JSON equality of
   `request`/`response` (model_call, tool_call) or `chosen` (decision). Mismatches become
   `kind="changed"` with the differing keys called out.

Output `first_diverging_step` = index of the first `StepDiff` whose `kind != "same"`. If none,
`first_diverging_step = None` and `summary = "no trajectory divergence"`.

## Consequences
- Cheap (LCS is O(n*m); trajectories are tens to hundreds of steps).
- Deterministic and explainable — investors / users can read the diff and immediately understand
  the failure mode.
- Limitation: the algorithm prioritizes shape over content. A subtle value swap in a step that's
  otherwise identically positioned still surfaces, but as `changed`, not "the agent went down a
  different path". That's the right call: shape changes are usually the catastrophe.
- Git-history bisect is deferred; once added it will live in the same `volo-diff` package and
  reuse `first_diverging_step` to drive the bisection criterion.

## Alternatives considered
- **Naive zip()-level compare** — fast but useless when one trajectory adds/removes a step.
- **Tree-edit distance on the `parent_id` DAG** — interesting for highly branching trajectories,
  overkill for v1 where most trajectories are linear.
