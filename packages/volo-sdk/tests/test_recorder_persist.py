"""Acceptance test for the Recorder auto-capture path (bible §9.1, ADR-0004)."""

from __future__ import annotations

import json
from pathlib import Path

from volo_sdk import Recorder, RecorderConfig, record


def test_recorder_writes_versioned_recording_json(tmp_path: Path) -> None:
    """Wrapping a proxy-using agent in ``record()`` should auto-capture model + tool calls."""
    from examples.echo_agent import run

    out = tmp_path / "echo.json"
    with record(
        agent_name="examples.echo_agent:run",
        framework="raw",
        config=RecorderConfig(data_dir=tmp_path, apply_redaction=False),
        out=out,
    ) as rec:
        result = run({"text": "hello"})
        rec.set_final_output(result)

    assert out.exists()
    blob = json.loads(out.read_text(encoding="utf-8"))
    assert blob["recording_schema_version"] == "1.0.0"

    types = [s["payload"]["type"] for s in blob["steps"]]
    assert types == ["tool_call", "model_call"], (
        f"Expected one tool_call then one model_call, got: {types}"
    )

    tool_step = blob["steps"][0]
    assert tool_step["payload"]["tool"] == "upper"
    assert tool_step["payload"]["request"] == {"text": "hello"}
    assert tool_step["payload"]["response"] == {"result": "HELLO"}
    assert tool_step["latency_ms"] is not None and tool_step["latency_ms"] >= 0

    model_step = blob["steps"][1]
    assert model_step["payload"]["provider"] == "echo"
    assert model_step["payload"]["request"] == {"prompt": "HELLO"}
    assert model_step["payload"]["response"]["text"] == "HELLO"

    assert blob["final_output"] == {"echo": "HELLO"}


def test_recorder_with_manual_api_still_works(tmp_path: Path) -> None:
    """The pre-proxy manual API (``Recorder.record_step``) must keep working."""
    from volo_core import DecisionPayload

    rec = Recorder(config=RecorderConfig(data_dir=tmp_path, apply_redaction=False))
    rec.record_step(DecisionPayload(label="branch", chosen="left"))
    rec.set_final_output("done")
    path = rec.save()
    blob = json.loads(path.read_text(encoding="utf-8"))
    assert blob["steps"][0]["payload"]["label"] == "branch"
