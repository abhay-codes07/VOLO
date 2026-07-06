# ADR 0022: long-horizon rig threads memory forward and scores longitudinal decay

- Status: accepted
- Date: 2026-07-06

## Context

M18 (newplan P4) tests the failure class that single-shot reliability misses: an agent that works
on turn 1 and rots over a long session (memory bloat, context drift, accumulation bugs). It must
stay deterministic and $0 — a for-loop over the sim, not a live 50-turn session.

## Decision

1. **Memory is threaded via the ordinary agent payload.** `run_long_horizon` replays the same
   task `N` times; each episode's payload is `{"episode": i, "memory": [prior outputs],
   **base_input}`. No new calling convention — a plain `agent(payload)` works. Agents that read
   `memory` and let it corrupt them degrade; agents that ignore it stay flat. Tools replay from
   Tier-1 every episode (identical responses), so the *only* thing that varies across episodes is
   the agent's own state — which is exactly what we want to isolate.
2. **Longitudinal dimensions on top of DFAH.** Per episode we record faithfulness (heuristic or
   any judge) and the trajectory shape. The report adds four cross-episode dimensions:
   `stability` (fraction of episodes matching episode 0's tool path), `output_consistency`
   (fraction matching episode 0's output), `faithfulness_slope` (least-squares slope — negative =
   decay), and `first_degraded_episode` (first faithfulness drop or error). The task is repeated
   identically, so output variation *is* drift.
3. **Verdict + gate.** `degrades` if any of: a degraded episode exists, stability < 1,
   output_consistency < 1, or slope < 0; else `stable`. `volo horizon` exits **7** on `degrades`
   — distinct from reliability (1), drift (3), red-team (4), migration (5), persona (6). A
   faithfulness sparkline makes the decay legible at a glance.

## Consequences

- The rig measures state-driven decay specifically; it holds tools constant, so it won't catch
  drift that only manifests with changing tool inputs (that's the scenario suite's job). Clean
  separation of concerns.
- Repeating the task identically means `output_consistency < 1` is a true drift signal, not
  benign variation — appropriate here, unlike the general reliability run.
- An episode that raises is scored faithfulness 0 and marked the first degradation — a crash mid
  session is a degradation, not a silent pass.
- `memory` is the prior *outputs*; richer state (full trajectories, token budgets) can extend the
  payload later without changing the contract.

## Alternatives considered

- **A `long_horizon_repeat` scenario operator** (M2 already has one) — that duplicates steps
  inside one recording to stress a single run; it does not thread agent state across independent
  episodes or measure a decay slope. The rig is the longitudinal complement, not a replacement.
- **A stateful environment that persists memory for the agent implicitly** — rejected: hides the
  state in the harness; threading it through the payload keeps the agent contract explicit and the
  test reproducible.
- **Model-backed episodes** — rejected for the core: nondeterministic and costly; the point is a
  free, deterministic for-loop.
