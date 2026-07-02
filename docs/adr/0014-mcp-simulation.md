# ADR 0014: MCP simulation — map Model Context Protocol traffic onto the existing simulator

- Status: accepted
- Date: 2026-07-03

## Context

The expansion charter (local `newplan.md`, pillar P1 / milestone M10) points the record→replay
engine at the Model Context Protocol. MCP is now the dominant tool-connection standard for
agents, and nobody offers deterministic record/replay/fuzz *of MCP servers themselves*. The
question is how to represent MCP traffic so the whole existing stack (Tier-1/Tier-2 simulator,
scenario operators, reliability metrics, CLI, CI) applies without modification.

## Decision

A new package, `volo-mcp`, with three transport-free cores (transports land in M10 slice 2):

1. **Representation:** every MCP JSON-RPC *request* becomes an ordinary `ToolCallPayload` step in
   the existing Recording schema. The cache identity is produced by one function,
   `messages.tool_key`:
   - `tools/call` → tool `mcp.tool:<name>`, request = the `arguments` object (so the same logical
     call replays regardless of JSON-RPC id);
   - every other method (`initialize`, `tools/list`, `resources/read`, …) → tool
     `mcp:<method>`, request = `params`.
2. **Responses are enveloped** as `{"result": ...}` or `{"error": ...}` so protocol errors —
   real server behavior — round-trip through replay exactly like successes.
3. **`MCPRecorder`** pairs requests/responses by JSON-RPC id and additionally distills a recorded
   `tools/list` result into `ToolSpec` entries (name/description/inputSchema/outputSchema) and the
   `initialize` result into `agent_meta.extra` — recorded MCP sessions arrive Tier-2-ready with
   zero user effort.
4. **`MCPReplayServer`** answers requests from any `SimulatedEnvironment`. On `ReplayMiss` /
   `Tier2Miss` it returns JSON-RPC error **-32042** (`SIM_MISS_CODE`, in the implementation-defined
   -32000..-32099 range) — the ADR-0009 flag-on-unknown invariant at the MCP boundary. It never
   hallucinates a response.
5. **Notifications and server→client requests** (e.g. `sampling/createMessage`) are counted in
   stats but not recorded/replayed in v1 — they carry no response to cache. Recording
   server-initiated sampling is future work.
6. Everything protocol-version-sensitive is confined to `messages.py`, since MCP spec churn is the
   pillar's top risk.

Dependencies: `volo-core`, `volo-sdk`, `volo-simulator` only. Zero third-party additions.

## Consequences

- Recordings of MCP traffic are plain Volo recordings: scenario mutation (M11 fuzz), reliability
  scoring, diffing, and the dashboard all work on them unchanged.
- The envelope means MCP recordings' `tool_call.response` is one level deeper than non-MCP
  recordings; consumers that inspect raw tool outputs must unwrap (`result`/`error`). Accepted as
  the price of faithful error replay.
- `initialize` replay is byte-faithful to the recorded handshake; a client demanding a *newer*
  protocol version than recorded will get the recorded answer (correct for regression testing,
  surprising for spec exploration).

## Alternatives considered

- **A new `mcp_call` step type** in the Recording schema — rejected: schema v2 churn, and every
  downstream package would need to learn it; the `(tool, request)` mapping loses nothing.
- **Storing bare `result` without an envelope** — rejected: protocol errors could not round-trip,
  and errors are exactly the behavior regression tests must reproduce.
- **Depending on the official `mcp` Python SDK** — rejected for v1: we only need message-level
  semantics, JSON-RPC framing is ~40 lines, and zero-dep install is a bible §11 value. Revisit if
  slice 2 transports get hairy.
