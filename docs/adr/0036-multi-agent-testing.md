# ADR 0036: multi-agent testing simulates sub-agents as counterparties via delegation interception

- Status: accepted
- Date: 2026-07-08

## Context

M32 (newplan P4) tests multi-agent systems — an orchestrator (LangGraph graph, CrewAI crew,
hand-rolled router) that delegates to sub-agents — as *systems*, not single trajectories. It must
build on what exists (the M17 persona counterparty, the simulator) and stay deterministic.

## Decision

1. **A sub-agent is a persona behind a delegation tool.** M17 established that a simulated
   counterparty is a `Persona` (facts → script → default). M32 generalizes the M17 environment
   from one user to N **named** counterparties: `MultiAgentEnvironment` intercepts the
   orchestrator's *delegation* tool calls (`delegate` / `call_agent` / `handoff` with a
   `to` + `message`, or an `agent.<name>` tool) and routes each to the named counterparty's
   persona; every other tool/model call passes through to Tier-1 replay. So the orchestrator runs
   unchanged and Volo captures the whole inter-agent message graph.
2. **The verdict is system-level.** `run_multiagent` returns a `SystemReport`: which counterparties
   were *reached*, which were declared but *unreached*, any delegation to an *unknown* agent, the
   full message list, and a `healthy` / `broken` verdict. `broken` iff the orchestrator errored, it
   delegated to an unknown agent, or an `expected` output marker was unmet. `unreached` alone is
   *not* broken — an orchestrator needn't use every available agent.
3. **Counterparties are data.** `{name: persona_dict}` JSON (the same persona pack shape as M17),
   so a crew's members are a shareable spec. `volo multiagent run` drives an orchestrator against
   them and exits **9** on `broken` (the next distinct gate code after compliance's 8).

## Consequences

- Because delegation is a tool interception, any orchestrator that delegates through a tool call
  works with zero code changes; frameworks that use a different mechanism route through one of the
  recognized tool names (configurable). This is the same seam personas (M17) use, so multi-agent
  reuses that machinery rather than a new one.
- The message graph makes a broken hand-off legible: you see exactly which agent was called with
  what and what came back (or that the target didn't exist) — the debugging a single end-to-end
  trajectory hides.
- Counterparties are deterministic personas, so a crew test is reproducible and free; genuinely
  open-ended sub-agent behavior needs the (future, opt-in) model-backed persona from M17.
- Verdict is intentionally simple (reachability + unknown-agent + goal markers); richer topology
  assertions (ordering, required hand-off sequences) are additive on top of the recorded message
  list.

## Alternatives considered

- **Actually run the sub-agents' real code** — rejected: non-deterministic, costly, and it's the
  orchestrator under test, not the members; simulating members is the point (and the safe posture,
  cf. ADR-0033's agent-execution boundary).
- **A new `delegation` step type** — rejected: a delegation is an ordinary `tool_call`; recording
  it as one keeps the whole stack (diff/score) working, same reasoning as ADR-0014/0034.
- **A separate orchestration package unrelated to personas** — rejected: a sub-agent *is* a
  counterparty; reusing `Persona` avoids a second responder model.
