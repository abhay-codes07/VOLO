"""MCP fuzz: operators mutate inside result envelopes; meta steps and errors stay intact."""

from __future__ import annotations

import io
from typing import Any, cast

from volo_core import Recording, ToolCallPayload
from volo_mcp import (
    MCPRecorder,
    MCPReplayServer,
    MessageBuffer,
    default_mcp_fuzz_library,
    encode_message,
    fuzz_change_summary,
    fuzz_recording,
    mcp_fuzz_scenarios,
    serve_stdio,
)
from volo_scenarios import CorruptField, DropToolResult, PromptInjection, ReorderSteps


def _req(msg_id: int, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    msg: dict[str, Any] = {"jsonrpc": "2.0", "id": msg_id, "method": method}
    if params is not None:
        msg["params"] = params
    return msg


def _res(msg_id: int, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def _baseline() -> Recording:
    """initialize + tools/list (meta), two tool results, one protocol error."""
    rec = MCPRecorder(server_name="calc")
    convo: list[tuple[dict[str, Any], dict[str, Any]]] = [
        (
            _req(1, "initialize", {"protocolVersion": "2025-06-18"}),
            _res(1, {"protocolVersion": "2025-06-18", "serverInfo": {"name": "calc"}}),
        ),
        (
            _req(2, "tools/list"),
            _res(2, {"tools": [{"name": "add", "inputSchema": {"type": "object"}}]}),
        ),
        (
            _req(3, "tools/call", {"name": "add", "arguments": {"a": 1, "b": 2}}),
            _res(3, {"content": [{"type": "text", "text": "3"}], "isError": False}),
        ),
        (
            _req(4, "tools/call", {"name": "add", "arguments": {"a": 5, "b": 6}}),
            _res(4, {"content": [{"type": "text", "text": "11"}], "isError": False}),
        ),
        (
            _req(5, "tools/call", {"name": "boom", "arguments": {}}),
            {"jsonrpc": "2.0", "id": 5, "error": {"code": -32602, "message": "bad params"}},
        ),
    ]
    for request, response in convo:
        rec.on_client_message(request)
        rec.on_server_message(response)
    return rec.recording


def _tool(rec: Recording, idx: int) -> ToolCallPayload:
    return cast(ToolCallPayload, rec.steps[idx].payload)


def test_meta_and_error_steps_are_never_mutated() -> None:
    base = _baseline()
    for _scenario, mutated in mcp_fuzz_scenarios(base, seed=0):
        assert _tool(mutated, 0).response == _tool(base, 0).response  # initialize
        assert _tool(mutated, 1).response == _tool(base, 1).response  # tools/list
        assert _tool(mutated, 4).response == _tool(base, 4).response  # protocol error


def test_drop_tool_result_empties_inside_envelope() -> None:
    mutated = fuzz_recording(_baseline(), DropToolResult(seed=0))
    dropped = [i for i in (2, 3) if _tool(mutated, i).response == {"result": {}}]
    assert len(dropped) == 1


def test_corrupt_field_flips_a_leaf_inside_the_result() -> None:
    base = _baseline()
    mutated = fuzz_recording(base, CorruptField(seed=0))
    changed = [i for i in (2, 3) if _tool(mutated, i).response != _tool(base, i).response]
    assert len(changed) == 1
    resp = _tool(mutated, changed[0]).response
    assert resp is not None and set(resp) == {"result"}  # envelope intact
    assert resp["result"]["isError"] is True  # the only top-level leaf, flipped


def test_prompt_injection_lands_inside_the_result() -> None:
    base = _baseline()
    mutated = fuzz_recording(base, PromptInjection(seed=1))
    changed = [i for i in (2, 3) if _tool(mutated, i).response != _tool(base, i).response]
    assert len(changed) == 1
    resp = _tool(mutated, changed[0]).response
    assert resp is not None and set(resp) == {"result"}
    assert "IGNORE PREVIOUS INSTRUCTIONS" in str(resp["result"])


def test_reorder_swaps_tool_responses_in_place() -> None:
    base = _baseline()
    mutated = fuzz_recording(base, ReorderSteps(seed=0))
    assert _tool(mutated, 2).response == _tool(base, 3).response
    assert _tool(mutated, 3).response == _tool(base, 2).response
    # meta + error positions untouched
    assert _tool(mutated, 0).tool == "mcp:initialize"
    assert _tool(mutated, 4).tool == "mcp.tool:boom"


def test_same_seed_same_mutations() -> None:
    base = _baseline()
    a = [m.to_json() for _, m in mcp_fuzz_scenarios(base, seed=7)]
    b = [m.to_json() for _, m in mcp_fuzz_scenarios(base, seed=7)]
    assert a == b


def test_change_summary_names_the_touched_steps() -> None:
    base = _baseline()
    mutated = fuzz_recording(base, CorruptField(seed=0))
    changes = fuzz_change_summary(base, mutated)
    assert len(changes) == 1
    assert changes[0]["change"] == "response"
    assert changes[0]["tool"].startswith("mcp.tool:")


def test_mutated_recording_serves_the_mutated_answer() -> None:
    base = _baseline()
    mutated = fuzz_recording(base, CorruptField(seed=0))
    changed = [i for i in (2, 3) if _tool(mutated, i).response != _tool(base, i).response]
    request = _tool(base, changed[0]).request

    out = io.BytesIO()
    call = _req(9, "tools/call", {"name": "add", "arguments": request})
    serve_stdio(MCPReplayServer.from_recording(mutated), io.BytesIO(encode_message(call)), out)
    (reply,) = MessageBuffer().feed(out.getvalue())
    assert reply["result"]["isError"] is True  # the agent sees the corrupted world


def test_default_library_covers_four_failure_classes() -> None:
    classes = {op.failure_class for op in default_mcp_fuzz_library()}
    assert classes == {"resilience", "robustness", "security", "order_sensitivity"}
