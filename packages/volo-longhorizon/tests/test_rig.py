"""Long-horizon rig: a stable agent holds; a drifting agent decays and is named at its episode."""

from __future__ import annotations

from typing import Any

import pytest

from volo_core import Recording, ToolCallPayload, get_active_environment
from volo_longhorizon import LongHorizonReport, run_long_horizon


def _baseline() -> Recording:
    rec = Recording()
    rec.add_step(ToolCallPayload(tool="search", request={"q": "volo"}, response={"hits": 3}))
    return rec


def _stable(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    env = get_active_environment()
    assert env is not None
    return {"hits": env.tool_registry().call("search", {"q": "volo"})["hits"]}


def _drifting(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    env = get_active_environment()
    assert env is not None
    grounded = env.tool_registry().call("search", {"q": "volo"})["hits"]
    memory = (payload or {}).get("memory", [])
    return {"hits": 99999} if len(memory) >= 3 else {"hits": grounded}


def test_stable_agent_holds_over_episodes() -> None:
    report = run_long_horizon(_baseline(), _stable, episodes=8)
    assert report.verdict == "stable"
    assert report.stability == 1.0 and report.output_consistency == 1.0
    assert report.faithfulness_start == report.faithfulness_end == 1.0
    assert report.first_degraded_episode is None


def test_drifting_agent_degrades_at_its_rot_episode() -> None:
    report = run_long_horizon(_baseline(), _drifting, episodes=8)
    assert report.verdict == "degrades"
    assert report.first_degraded_episode == 3  # memory hits threshold on episode 3
    assert report.faithfulness_start == 1.0 and report.faithfulness_end == 0.0
    assert report.faithfulness_slope < 0.0
    assert report.output_consistency < 1.0


def test_memory_is_threaded_forward() -> None:
    seen: list[int] = []

    def spy(payload: dict[str, Any] | None = None) -> dict[str, Any]:
        seen.append(len((payload or {}).get("memory", [])))
        return {"ok": True}

    run_long_horizon(_baseline(), spy, episodes=4)
    assert seen == [0, 1, 2, 3]  # memory grows by one each episode


def test_episode_error_counts_as_degradation() -> None:
    def boom(payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if (payload or {}).get("episode") == 2:
            raise ValueError("rot")
        return {"hits": 3}

    report = run_long_horizon(_baseline(), boom, episodes=5)
    assert report.verdict == "degrades"
    assert report.first_degraded_episode == 2
    assert report.results[2].error is not None


def test_episodes_must_be_positive() -> None:
    with pytest.raises(ValueError, match="episodes must be >= 1"):
        run_long_horizon(_baseline(), _stable, episodes=0)


def test_report_json_roundtrip() -> None:
    report = run_long_horizon(_baseline(), _drifting, episodes=6)
    restored = LongHorizonReport.model_validate_json(report.to_json())
    assert restored.verdict == "degrades"
    assert len(restored.results) == 6
