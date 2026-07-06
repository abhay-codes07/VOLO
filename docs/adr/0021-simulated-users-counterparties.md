# ADR 0021: simulated users are a persona-backed environment wrapper; answers are deterministic

- Status: accepted
- Date: 2026-07-06

## Context

M17 (newplan P4) makes multi-turn agents testable by simulating their counterparty — the user
(or a sub-agent / another agent) that answers the agent's clarifying questions. The design has to
plug into the existing deterministic-replay machinery and stay $0 / reproducible.

## Decision

1. **The user is a tool interception, not a new subsystem.** `PersonaEnvironment` wraps any inner
   `SimulatedEnvironment` (Tier-1 replay by default) and its `tool_registry()` intercepts a set of
   "ask the user" tool names (`ask_user`, `user`, `clarify`, `ask`), routing them to a
   `SimulatedUser`; every other tool/model call passes through to the inner sim. So a multi-turn
   agent runs **unchanged** — it just receives persona answers to its questions, and the inner
   recording still serves its other tools. This reuses the `current_environment` ContextVar seam
   the runner already uses.
2. **Answers are deterministic, no model.** A `Persona` resolves a reply in fixed precedence:
   keyword-matched **facts** first (first fact whose key appears in the question wins — order is
   significant), then an ordered **script** of fallback lines consumed one per *unmatched*
   question, then a default. Same question → same answer, every run. This keeps persona tests in
   the "record once, replay free" world; an LLM-backed persona could slot in behind the same
   `SimulatedUser.ask` seam later, opt-in, but is out of scope for the deterministic core.
3. **Goal check via markers.** A persona declares `expected` substrings; `goal_satisfied` is true
   when all appear in the agent's final output. `drive_persona` returns a `ConversationReport`
   (transcript + final output + `goal_met` + any agent error). `volo persona run --require-goal`
   exits **6** on an unmet goal — distinct from reliability (1), drift (3), red-team (4),
   migration (5).
4. **Personas are JSON data** (`load_persona`/`dump_persona`/`volo persona export`) — the same
   pack pattern as attack packs, feeding the marketplace (P6).

## Consequences

- Any agent that talks to its counterparty through a tool call works with zero code changes;
  agents that hard-code a different mechanism need to route through one of the recognized tool
  names (configurable via `user_tools`).
- The same wrapper models sub-agents / other agents — a counterparty is just a persona behind a
  delegation tool — so multi-agent orchestration testing (M32) builds on this, not a new seam.
- Deterministic personas can't improvise beyond their facts/script; genuinely open-ended user
  simulation needs the (future, opt-in) model-backed persona. Accepted: the deterministic core is
  what makes it a CI test.
- Script advances only on *unmatched* questions, so re-asking a fact-covered question doesn't
  burn the script — matches how a real user would just re-state a known fact.

## Alternatives considered

- **A `SimulatedUser` provider injected into the runner config** — rejected: threads a new
  parameter through the whole runner; the environment wrapper composes with everything already.
- **LLM-backed personas as the default** — rejected for the core: nondeterministic and costs
  money, defeating the CI/$0 property; kept as a future opt-in behind the same seam.
- **A dedicated `user_call` step type in the recording** — rejected: it's an ordinary
  `tool_call`; no schema churn needed.
