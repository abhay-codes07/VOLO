# Volo — Glossary

Domain terms and metric definitions. Keep this file authoritative; if a term in code disagrees
with the glossary, fix the code or update the glossary in the same change.

## Core domain
- **Agent** — A program that takes natural-language input, plans, calls tools and/or model APIs,
  and produces a final output. Could be LangGraph, OpenAI Agents SDK, CrewAI, or hand-rolled.
- **Trajectory** — The ordered sequence of steps an agent took during a single run.
- **Step** — One unit of trajectory: a `model_call`, a `tool_call`, or a `decision`. Each has
  `input`, `output`, `latency`, optional `tokens` and `cost`, and a `parent_id` for branching.
- **Recording** — A serialized agent run: `RunMeta` + ordered `Step[]` + `final_output` +
  `env_snapshot` + optional `tool_specs[]`. Versioned (`recording_schema_version`).
- **RunMeta** — Agent framework + version, model config, seeds, timestamps, redaction state.
- **ToolSpec** — Optional declarative description of a tool (name, signature, JSON schema for
  inputs/outputs, optional source/OpenAPI pointer). Used by the Tier-2 simulator to answer
  un-recorded inputs faithfully.
- **EnvSnapshot** — Initial state of the simulated world: file system, DB rows, API mock state, etc.
- **Scenario** — A deterministic mutation of a `Recording` that probes a failure class. Examples:
  `drop_tool_result`, `corrupt_field`, `inject_latency`, `ambiguous_user_turn`,
  `prompt_injection`, `reorder_steps`, `long_horizon_repeat`. Each is seeded and labeled.
- **Simulated Environment** — Stateful mock of the agent's external world. Tier-1 = deterministic
  replay from cache; Tier-2 = source-/trace-informed synthesis for un-recorded inputs.
- **Run** — A single execution of an agent against a `SimulatedEnvironment` under a `Scenario`.
- **Reliability Report** — The multi-dimensional output of the Reliability Engine for a Run or a
  set of Runs. Includes the four metrics below + a single ship/no-ship verdict.
- **Diff** — A structural comparison of two `Run`s (or two `Recording`s) that identifies the
  earliest differing step and, where wired up, the responsible git commit.

## Reliability metrics (per DFAH research — bible §9.4)
> Determinism and accuracy are **uncorrelated**. We must report all four; never collapse to one
> score.

- **Trajectory determinism** — Across N repeated runs of the same agent on the same scenario, do
  the trajectories take the same shape (same tools in the same order)? Reported as a fraction
  ∈ [0, 1] plus a per-step divergence map.
- **Decision determinism** — Do repeated runs reach the same final decision / output? Same
  fraction ∈ [0, 1]. May be high even when trajectory determinism is low (multiple paths, same
  conclusion).
- **Faithfulness** — Is the final output **grounded in the evidence and tool results the agent
  actually saw**? Detects hallucinations / fabrications. Scored 0..1 by a local judge model.
- **Consistency-under-repetition** — Distribution of outcomes across N runs. Crucially
  distinguishes "consistent 50% pass" (always borderline) from "catastrophic on some runs"
  (sometimes total failure). Reported as a histogram + a single scalar (e.g., 5th-percentile pass).

## Cost / models
- **Local judge** — A small open-weight model running via Ollama, used as the default LLM-as-judge
  for faithfulness scoring. $0 marginal cost.
- **Frontier API** — Anthropic / OpenAI hosted models. Opt-in only; subject to per-project
  token + dollar cap.
- **Replay mode** — All model and tool calls are served from the recording or the simulator; no
  network calls leave the runner. This is the default for CI.
- **Live mode** — Original behavior (real model APIs, real tools). Used only at record time, or
  explicitly when the developer wants to refresh a recording.

## Operational
- **Resume here** — The single concrete next task listed at the top of `docs/STATUS.md`. The
  session START ritual reads this; the session END ritual updates it.
- **ADR** — Architecture Decision Record. Numbered file in `docs/adr/`. Written for every
  meaningful or hard-to-reverse choice.
- **Self-check / dogfood** — A CI workflow that runs Volo on Volo's own example agents.
  The product proving itself on every push is also marketing.
