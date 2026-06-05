"""Tier-1 Replayer acceptance tests (bible §9.2, ADR-0003)."""

from __future__ import annotations

import pytest

from volo_core import (
    ModelCallPayload,
    Recording,
    ToolCallPayload,
    current_environment,
)
from volo_simulator import ReplayMiss, Tier1Replayer


def _recording_with_calls() -> Recording:
    r = Recording()
    r.add_step(
        ModelCallPayload(
            provider="echo",
            model="echo-1",
            request={"prompt": "HELLO"},
            response={"text": "HELLO", "stop_reason": "end_turn"},
        ),
    )
    r.add_step(
        ToolCallPayload(
            tool="upper",
            request={"text": "hello"},
            response={"result": "HELLO"},
        ),
    )
    return r


def test_replayer_stats_reflect_recording() -> None:
    r = Tier1Replayer.from_recording(_recording_with_calls())
    assert r.stats() == {
        "model_entries": 1,
        "model_keys": 1,
        "tool_entries": 1,
        "tool_keys": 1,
    }


def test_model_hit_returns_recorded_response() -> None:
    r = Tier1Replayer.from_recording(_recording_with_calls())
    provider = r.model_provider("echo", "echo-1")
    assert provider.complete({"prompt": "HELLO"}) == {"text": "HELLO", "stop_reason": "end_turn"}


def test_model_miss_raises_replaymiss() -> None:
    r = Tier1Replayer.from_recording(_recording_with_calls())
    provider = r.model_provider("echo", "echo-1")
    with pytest.raises(ReplayMiss):
        provider.complete({"prompt": "this prompt was never recorded"})


def test_tool_hit_returns_recorded_response() -> None:
    r = Tier1Replayer.from_recording(_recording_with_calls())
    tools = r.tool_registry()
    assert tools.call("upper", {"text": "hello"}) == {"result": "HELLO"}


def test_tool_miss_raises_replaymiss() -> None:
    r = Tier1Replayer.from_recording(_recording_with_calls())
    tools = r.tool_registry()
    with pytest.raises(ReplayMiss):
        tools.call("upper", {"text": "novel-input"})


def test_replay_is_robust_to_dict_key_ordering() -> None:
    r = Tier1Replayer.from_recording(_recording_with_calls())
    tools = r.tool_registry()
    # Same content, different key insertion order — must still hit cache.
    assert tools.call("upper", dict({"text": "hello"})) == {"result": "HELLO"}


def test_echo_agent_replays_bit_identical_under_environment() -> None:
    """Run the echo agent under a Tier-1 replayer of its own recording — outputs must match."""
    from examples.echo_agent import run

    from volo_sdk import Recorder, RecorderConfig

    # Record once.
    rec = Recorder(config=RecorderConfig(apply_redaction=False))
    from volo_core import current_recorder

    with current_recorder(rec):
        first = run({"text": "hello"})
        rec.set_final_output(first)

    # Replay through Tier-1 — no live calls allowed (no model_provider/tool_registry inner used).
    env = Tier1Replayer.from_recording(rec.recording)
    with current_environment(env):
        second = run({"text": "hello"})

    assert first == second == {"echo": "HELLO"}
