# ADR 0004: Active-recorder + proxy capture pattern

- **Status:** accepted
- **Date:** 2026-05-31
- **Deciders:** founder
- **Related:** bible §4 subsystem 1, §7.1, §9.1; ADR-0003

## Context
The Recorder needs to observe every `ModelProvider.complete()` and `ToolRegistry.call()` an agent
makes during a run, without forcing the agent author to thread a `recorder` argument through
every layer. Frameworks like LangGraph and CrewAI hide the call sites — we cannot reasonably ask
users to instrument each call manually.

We also want the SAME mechanism to work in two modes:
- **record mode** — proxy captures input/output and appends a `Step` to the active Recorder.
- **replay mode** — proxy serves the cached output from the recording, with no live call.

## Decision
Two layers:

1. **`ContextVar`-based active recorder.** `volo_core.context` exposes
   `set_active_recorder(rec)`, `get_active_recorder()`, and a `current_recorder()` context
   manager. The SDK's `Recorder.__enter__` sets itself active; `__exit__` restores. `ContextVar`
   is async-safe and survives `asyncio.create_task` so async agents work.
2. **`Proxy` wrappers** in `volo_sdk.proxies`:
   - `ModelProviderProxy(provider)` — wraps any `ModelProvider`; on `.complete(req)`, looks up
     the active recorder, records a `ModelCallPayload`, delegates to the wrapped provider, fills
     in the response, and returns it.
   - `ToolRegistryProxy(registry)` — same shape for `ToolRegistry.call(tool, req)`.
   These proxies are stateless given the active recorder, so they are safe to share.

Framework adapters (`integrations/raw`, `integrations/langgraph`, etc.) install proxies into the
agent's runtime once at construction time; the agent code is unchanged.

## Consequences
- **Easy:** zero-friction capture — wrap an agent with `record()`, the rest is automatic.
- **Easy:** symmetric replay — same proxies, different `ModelProvider`/`ToolRegistry` injected
  (a `ReplayModelProvider` looks up cached responses).
- **Easy:** async-safety via `ContextVar`; nested recorders compose (inner takes precedence).
- **Hard:** code that bypasses the proxies (raw `httpx` calls, direct SDK use) is invisible to
  capture. Mitigation: framework adapters install proxies at the canonical extension points; for
  raw agents, users instantiate `ModelProviderProxy` explicitly (see `examples/calc_agent`).

## Alternatives considered
- **Monkey-patching `openai`/`anthropic` modules globally** — wider net, but breaks when the user
  has parallel agents running in the same process with different recorders. Rejected.
- **Thread-local active recorder** — fails for `asyncio` agents that span tasks. Rejected.
- **Explicit `recorder` parameter threading** — clean but viral; rejected for the user-experience
  reasons above.
