"""e2e: calc_agent records a 5-step trajectory and replays bit-identically."""

from __future__ import annotations

from examples.calc_agent import run

from volo_core import current_environment, current_recorder
from volo_sdk import Recorder, RecorderConfig
from volo_simulator import Tier1Replayer


def test_records_five_steps() -> None:
    rec = Recorder(config=RecorderConfig(apply_redaction=False))
    with current_recorder(rec):
        result = run({"a": 2, "b": 3, "c": 4})
    assert result == {"answer": 20}
    types = [s.type for s in rec.recording.steps]
    assert types == ["decision", "model_call", "tool_call", "tool_call", "model_call"]


def test_replay_returns_same_answer() -> None:
    rec = Recorder(config=RecorderConfig(apply_redaction=False))
    with current_recorder(rec):
        baseline = run({"a": 2, "b": 3, "c": 4})

    env = Tier1Replayer.from_recording(rec.recording)
    with current_environment(env):
        replayed = run({"a": 2, "b": 3, "c": 4})

    assert baseline == replayed == {"answer": 20}
