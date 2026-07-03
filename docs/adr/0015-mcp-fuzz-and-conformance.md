# ADR 0015: MCP fuzz targets result envelopes only; conformance replays against the live server

- Status: accepted
- Date: 2026-07-03

## Context

M11 brings adversarial testing to the MCP boundary (ADR-0014). Two design questions:
(1) *what* may the fuzzer mutate in a recorded MCP session, and (2) what does "conformance"
mean for an MCP-server author using Volo as a regression gate?

## Decision

**Fuzz (`volo_mcp.fuzz`)** reuses the generic `volo-scenarios` operators unchanged, wrapped by
two MCP-specific rules:

1. **Fuzz targets are only real tool responses** — `tool_call` steps with an `mcp.tool:` prefix
   whose response is a `{"result": <object>}` envelope. Handshake/meta steps
   (`mcp:initialize`, `mcp:tools/list`, …) and recorded *protocol errors* are byte-intact in
   every mutation, so a fuzzed session still boots and error behavior stays authentic.
2. **Operators run inside the envelope.** The fuzzer extracts the target steps into a
   sub-recording, unwraps `{"result": X}` → `X`, applies the operator, re-wraps, and merges the
   steps back into their original positions. Operators therefore mutate the object the agent
   actually reads (e.g. `corrupt_field` flips `isError`; `prompt_injection` lands inside the
   content), and the mutated recording replays through `MCPReplayServer` with no special cases.

Default library: `drop_tool_result`, `corrupt_field`, `prompt_injection`, `reorder_steps`
(failure classes: resilience, robustness, security, order_sensitivity). Excluded:
`inject_latency` (latency metadata is never served over the wire) and `ambiguous_user_turn`
(MCP recordings contain no model calls). Mutations are seeded → reproducible in CI.

**Conformance (`volo_mcp.conformance`)** treats a recording as a behavioral contract: every
recorded request is rebuilt (`messages.request_message`, the inverse of `tool_key`) and sent to
a freshly spawned live server; each reply is compared to the recorded envelope. Verdicts:
`identical` / `different` / `no_reply`; anything non-identical fails (exit 1 in the CLI).
Recorded protocol errors are part of the contract and must reproduce.

## Consequences

- Every fuzz output is itself a valid, servable recording — `volo mcp serve` and future
  reliability scoring work on hostile worlds with zero extra machinery.
- Restricting targets to result envelopes means the fuzzer never breaks the transport layer —
  by design. Malformed-protocol fuzzing (bad JSON-RPC framing, wrong ids) is a separate future
  concern, closer to the transport tests than to scenario operators.
- Conformance request reconstruction is lossy for `tools/call` params beyond
  `name`/`arguments` (deliberately dropped from the cache identity in ADR-0014). Servers keying
  behavior on exotic params need a fresh recording rather than conformance replay.
- Conformance compares byte-equal envelopes; servers with legitimately nondeterministic fields
  (timestamps, ids) will report `different`. A normalization hook is future work if demanded.

## Alternatives considered

- **MCP-specific operator implementations** — rejected: duplicates the M2 taxonomy and forks
  the failure-class vocabulary the reliability engine already understands.
- **Fuzzing everything, including handshake/meta and error envelopes** — rejected: trivially
  broken sessions (failed `initialize`) mask the interesting failures, and mutating a recorded
  error's shape produces worlds no real server can express.
- **Conformance via the simulator (replay both sides offline)** — rejected: that tests Volo
  against itself; the author's question is whether the *live build* still honors the contract.
