# ADR 0026: adapters v2 reuse the M7 wrap()/otel-import shape; duck-typed, no framework deps

- Status: accepted
- Date: 2026-07-06

## Context

M22 (newplan wave 3) adds AutoGen, Pydantic AI, and Semantic Kernel to the framework integrations
shipped in M7 (LangGraph, OpenAI Agents, CrewAI). The question is how much to bind to each
framework's real API versus keeping the adapters thin and dependency-free.

## Decision

Each new integration mirrors the M7 shape exactly — one package under `integrations/`, exporting
`wrap()` and `import_<framework>_otel()`, depending only on `volo-core` + `volo-sdk`:

- **`wrap()` swaps the framework's model/tool objects with Volo proxies**, duck-typed against the
  framework's documented attributes so no framework dependency (or install) is needed:
  - AutoGen: `model_client` (v0.4 `autogen-agentchat`) or `llm` (legacy 0.2); `tools`.
  - Pydantic AI: `agent.model`; a tool proxy on `_volo_tool_proxy`.
  - Semantic Kernel: every entry in `kernel.services`; `plugins` via `_volo_tool_proxy`.
  Each also decorates the run entrypoint (`run`/`run_sync`/`invoke`/…) to emit a `decision` step,
  so the trajectory keeps the framework's structure visible (as CrewAI's kickoff does).
- **`import_*_otel()` delegates to the shared `import_otel_trace` seam** with the framework tag —
  so any OTel-instrumented run becomes a recording with zero agent code change.
- **Tests use fakes** whose model objects expose `.complete(request)` (the `ModelProvider`
  interface). This is the same fidelity bar as the M7 integrations: the adapter establishes
  Volo's capture seam; a production binding adapts the framework's native call into `.complete`.

## Consequences

- Adding a framework is ~60 lines + a fake test; the pattern is now proven six times.
- Duck-typing means `wrap()` silently no-ops on an attribute a framework renames across versions
  (it targets the first present of a candidate set). That's deliberate — it degrades to
  "captures nothing" rather than crashing — but means a framework API change needs a new attribute
  candidate, not a rewrite. Integrations stay out of the mypy `files` list (like M7's), so this is
  covered by tests, not types.
- The decision-step decoration binds `__orig`/`__label` via default args (not a loop closure), so
  it's re-entrant-safe and lint-clean.

## Alternatives considered

- **Import each framework and bind to real classes** — rejected: adds three heavy optional
  dependencies and version-coupling for a seam whose job is capture; the duck-typed wrapper is
  what M7 established and what keeps the install light.
- **A single generic adapter** parameterized by attribute names — rejected: the per-framework
  files are trivial and read better than a config blob; each documents its framework's shape.
