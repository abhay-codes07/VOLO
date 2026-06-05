"""End-to-end runner test: baseline → scenarios → replay → ReliabilityReport."""

from __future__ import annotations

from examples.calc_agent import run

from volo_core import current_recorder
from volo_runner import OrchestratorConfig, orchestrate
from volo_sdk import Recorder, RecorderConfig


def _baseline() -> object:
    rec = Recorder(config=RecorderConfig(apply_redaction=False))
    with current_recorder(rec):
        result = run({"a": 2, "b": 3, "c": 4})
        rec.set_final_output(result)
    return rec.recording


def test_runner_produces_report_with_seven_scenarios() -> None:
    baseline = _baseline()
    report = orchestrate(
        baseline,
        run,
        config=OrchestratorConfig(n_runs=2, agent_input={"a": 2, "b": 3, "c": 4}),
    )
    assert len(report.scenarios) == 7
    assert set(report.aggregate.keys()) == {
        "trajectory_determinism",
        "decision_determinism",
        "faithfulness",
        "consistency_under_repetition",
    }
    assert report.verdict in {"ship", "no_ship"}


def test_runner_report_is_json_serializable() -> None:
    baseline = _baseline()
    report = orchestrate(
        baseline,
        run,
        config=OrchestratorConfig(n_runs=1, agent_input={"a": 2, "b": 3, "c": 4}),
    )
    blob = report.to_json()
    assert '"verdict"' in blob
    assert '"scenarios"' in blob


def test_runner_threads_judge_through_to_faithfulness() -> None:
    """A supplied JudgeProvider overrides the heuristic faithfulness score end-to-end."""
    import json
    from typing import Any

    from volo_core.interfaces import ModelProvider
    from volo_reliability import OllamaJudge

    class _ConstJudge(ModelProvider):
        def complete(self, request: dict[str, Any]) -> dict[str, Any]:
            return {"text": json.dumps({"score": 0.42})}

    baseline = _baseline()
    report = orchestrate(
        baseline,
        run,
        config=OrchestratorConfig(
            n_runs=1,
            agent_input={"a": 2, "b": 3, "c": 4},
            judge=OllamaJudge(provider=_ConstJudge()),
        ),
    )
    applicable = [s for s in report.scenarios if s.applicable and s.n_runs > 0]
    assert applicable, "expected at least one applicable scenario"
    assert all(s.metrics["faithfulness"] == 0.42 for s in applicable)
