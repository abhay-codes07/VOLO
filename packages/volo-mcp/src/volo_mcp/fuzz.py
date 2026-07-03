"""MCP fuzz — the M2 scenario operators applied at the MCP boundary (newplan M11).

An MCP recording is an ordinary Volo Recording, so the generic ``volo-scenarios`` operators
apply — with two MCP-specific rules this module enforces:

* **Only real tool responses are fuzz targets.** Handshake/meta steps (``mcp:initialize``,
  ``mcp:tools/list``, …) and recorded *protocol errors* are left byte-intact, so a fuzzed
  session still gets past ``initialize`` and error behavior stays authentic.
* **Mutation happens inside the ``{"result": ...}`` envelope.** Operators see the bare result
  object (so ``corrupt_field`` flips ``isError``, ``prompt_injection`` lands inside the payload
  the agent actually reads), and the envelope is restored afterwards so the mutated recording
  replays through ``MCPReplayServer`` unchanged.

``inject_latency`` and ``ambiguous_user_turn`` are deliberately not in the default set: latency
metadata is never served over the wire, and MCP recordings contain no model calls.
"""

from __future__ import annotations

from typing import Any, cast

from volo_core import Recording, ToolCallPayload
from volo_mcp.messages import TOOL_PREFIX
from volo_scenarios import (
    CorruptField,
    DropToolResult,
    PromptInjection,
    ReorderSteps,
    Scenario,
    ScenarioOp,
)

MCP_FUZZ_OPS: tuple[type[ScenarioOp], ...] = (
    DropToolResult,
    CorruptField,
    PromptInjection,
    ReorderSteps,
)


def default_mcp_fuzz_library(seed: int = 0) -> list[ScenarioOp]:
    """One seeded instance of each MCP-relevant operator (mirrors ``default_library``)."""
    return [cls(seed=seed + i) for i, cls in enumerate(MCP_FUZZ_OPS)]


def _clone(recording: Recording) -> Recording:
    return Recording.model_validate(recording.model_dump(mode="python", by_alias=True))


def _is_fuzz_target(step_payload: Any) -> bool:
    """A real tool call whose recorded response is a ``{"result": <object>}`` envelope."""
    if step_payload.type != "tool_call" or not step_payload.tool.startswith(TOOL_PREFIX):
        return False
    resp = step_payload.response
    return isinstance(resp, dict) and set(resp) == {"result"} and isinstance(resp["result"], dict)


def fuzz_recording(recording: Recording, op: ScenarioOp) -> Recording:
    """Apply one generic operator to the fuzz-target steps of an MCP recording.

    The operator runs against a sub-recording of unwrapped tool results; the mutated steps are
    merged back into their original positions (extra steps an operator appends land at the end).
    """
    full = _clone(recording)
    positions = [i for i, s in enumerate(full.steps) if _is_fuzz_target(s.payload)]
    if not positions:
        return full

    sub = _clone(full)
    sub.steps = [full.steps[i] for i in positions]
    for step in sub.steps:
        payload = cast(ToolCallPayload, step.payload)  # guaranteed by _is_fuzz_target
        payload.response = cast(dict[str, Any], payload.response)["result"]

    mutated = op.apply(sub)
    for step in mutated.steps:
        if step.payload.type == "tool_call":
            resp = step.payload.response
            step.payload.response = {"result": {} if resp is None else resp}

    for pos, new_step in zip(positions, mutated.steps, strict=False):
        full.steps[pos] = new_step
    full.steps.extend(mutated.steps[len(positions) :])
    return full


def mcp_fuzz_scenarios(
    recording: Recording,
    *,
    seed: int = 0,
    ops: list[ScenarioOp] | None = None,
) -> list[tuple[Scenario, Recording]]:
    """Materialize the MCP fuzz library against a recording → (metadata, mutated) pairs."""
    library = ops if ops is not None else default_mcp_fuzz_library(seed=seed)
    return [(op.scenario(), fuzz_recording(recording, op)) for op in library]


def fuzz_change_summary(baseline: Recording, mutated: Recording) -> list[dict[str, Any]]:
    """Human/CI-readable list of what a mutation touched (for the fuzz report)."""
    changes: list[dict[str, Any]] = []
    for i, (a, b) in enumerate(zip(baseline.steps, mutated.steps, strict=False)):
        if a.payload.type != "tool_call" or b.payload.type != "tool_call":
            continue
        pa, pb = a.payload, b.payload
        if a.step_id != b.step_id:
            changes.append({"index": i, "tool": pb.tool, "change": "moved"})
        elif pa.response != pb.response:
            changes.append({"index": i, "tool": pb.tool, "change": "response"})
    if len(mutated.steps) > len(baseline.steps):
        changes.append({"index": len(baseline.steps), "tool": "*", "change": "steps_appended"})
    return changes
