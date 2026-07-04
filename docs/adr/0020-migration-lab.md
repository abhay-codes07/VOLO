# ADR 0020: migration lab compares two recorded corpora; model identity is normalized out

- Status: accepted
- Date: 2026-07-04

## Context

M16 (newplan P5) answers "will my agent survive the next model?". Volo's replay is deterministic
cache-replay keyed on `(provider, model, request)`, so a model the agent was never recorded under
has no responses to replay. The design question is how to compare model A vs model B within that
constraint, honestly and cheaply.

## Decision

**Compare two recorded corpora, not one corpus replayed two ways.** The user records their corpus
under model A (already done — it's the baseline) and re-records it once under model B (the only
live cost). `volo migrate` then pairs the two corpora and scores the difference offline. This
keeps the near-$0 promise: exactly one live pass, everything else deterministic.

- **Pairing** (`pair_corpora`) is by file **stem** — re-recording keeps names, so `a/checkout.json`
  ↔ `b/checkout.json`. Two explicit *files* pair positionally even with different stems; stems
  present on only one side are reported as `unpaired`, never dropped.
- **Model identity is normalized out of the trajectory comparison.** `_tool_path` collapses every
  `model_call` to a bare marker (unlike `trajectory_shape`, which includes `provider/model`), so a
  *pure* model swap does not, by itself, register as a path change — only a genuine change in the
  agent's tool usage / decisions does.
- **Per-pair outcome** from three signals: faithfulness delta (heuristic or any `JudgeProvider`),
  output change (canonical JSON), tool-path change. `improved` / `regressed` on faithfulness
  movement; else `changed` if behavior differs; else `unchanged`.
- **Roll-up**: any regression ⇒ `block` (exit 5); else any behavior change ⇒ `review` (exit 0);
  else `recommend` (exit 0). Exit 5 is distinct from reliability (1), shadow drift (3), red-team
  (4).
- **Cost** uses recorded spend when present, else a token estimate (50/50 in/out split) from a
  **promoted public `volo_models.pricing`** module — the private frontier pricing table is now
  shared, not duplicated.

## Consequences

- Requires a candidate corpus re-recorded under B; the lab does not itself call model B (it never
  spends money or hits the network). The one live pass is the user's, done with their own tooling.
- The 50/50 token split and placeholder price sheet make the cost delta directional, not
  invoice-accurate; documented as "projected". Recorded `cost_usd` overrides the estimate when
  present.
- Faithfulness is the regression signal; a model that changes wording but stays grounded reads as
  `changed` (review), not `regressed` — intentional, to avoid blocking on benign rephrasing.
- Pairing by stem assumes the re-record preserves names; disjoint corpora surface as `unpaired`
  rather than mispairing.

## Alternatives considered

- **Splice model-B responses into the agent's model calls and re-drive** — rejected: the agent's
  prompts to the model depend on prior outputs, so B's recorded responses stop matching after the
  first divergence; it collapses to Tier-2 synthesis and low fidelity.
- **A single reliability score per model, compared** — rejected: hides *which* traces regressed;
  the per-pair verdict is the actionable unit.
- **Calling model B live inside `migrate`** — rejected: breaks the offline/$0 property and
  duplicates the recorder's job.
