"""Basic Recorder API tests. The deep capture-path tests live in ``test_recorder_persist.py``."""

from __future__ import annotations

import json
from pathlib import Path

from volo_core import (
    DecisionPayload,
    ModelCallPayload,
    ToolCallPayload,
)
from volo_sdk import Recorder, RecorderConfig, record


def test_recorder_builds_recording_via_manual_api(tmp_path: Path) -> None:
    rec = Recorder(
        agent_name="demo",
        framework="raw",
        config=RecorderConfig(data_dir=tmp_path, apply_redaction=False),
    )
    rec.record_step(ModelCallPayload(provider="ollama", model="llama3.2:3b", request={"p": "hi"}))
    rec.record_step(ToolCallPayload(tool="search", request={"q": "x"}, response={"hits": []}))
    rec.set_final_output({"answer": "ok"})

    path = rec.save()
    assert path.exists()
    blob = json.loads(path.read_text(encoding="utf-8"))
    assert blob["recording_schema_version"] == "1.0.0"
    assert blob["final_output"] == {"answer": "ok"}
    assert [s["payload"]["type"] for s in blob["steps"]] == ["model_call", "tool_call"]
    assert blob["agent_meta"]["framework"] == "raw"


def test_context_manager_saves_on_exit(tmp_path: Path) -> None:
    out = tmp_path / "demo.json"
    with record(
        agent_name="ctx",
        framework="raw",
        config=RecorderConfig(data_dir=tmp_path, apply_redaction=False),
        out=out,
    ) as rec:
        rec.record_step(DecisionPayload(label="terminate", chosen="yes"))
        rec.set_final_output({"done": True})

    assert out.exists()
    blob = json.loads(out.read_text(encoding="utf-8"))
    assert blob["final_output"] == {"done": True}
    assert blob["steps"][0]["payload"]["type"] == "decision"


def test_save_redacts_by_default(tmp_path: Path) -> None:
    """Recordings saved through the SDK must be redacted unless explicitly opted out."""
    rec = Recorder(config=RecorderConfig(data_dir=tmp_path))
    rec.record_step(
        ModelCallPayload(
            provider="anthropic",
            model="claude-haiku",
            request={"messages": [{"content": "key=sk-ant-AAAA1111BBBB2222CCCC3333DDDD4444EEEE"}]},
        ),
    )
    path = rec.save()
    blob = path.read_text(encoding="utf-8")
    assert "sk-ant-" not in blob
    assert "[REDACTED]" in blob
    parsed = json.loads(blob)
    assert parsed["redaction_applied"] is True
