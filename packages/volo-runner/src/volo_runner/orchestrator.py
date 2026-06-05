"""The runner orchestrator (bible §4 subsystem 5)."""

from __future__ import annotations

import importlib
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, cast

from volo_core import Recording, current_environment, current_recorder
from volo_reliability import (
    ReliabilityReport,
    ScenarioReport,
    aggregate_runs,
    compose_report,
)
from volo_scenarios import generate_default_scenarios
from volo_scenarios.base import Scenario
from volo_sdk import Recorder, RecorderConfig
from volo_simulator import ReplayMiss, Tier1Replayer


@dataclass
class OrchestratorConfig:
    n_runs: int = 3
    seed: int = 0
    fail_under: float = 0.9
    aggregator: str = "p5"
    agent_input: dict[str, Any] | None = None
    # Optional JudgeProvider for faithfulness scoring; None → zero-cost heuristic.
    judge: Any | None = None


def resolve_agent(target: str) -> Callable[..., Any]:
    """Resolve a ``pkg.module:callable`` string, prepending CWD to ``sys.path`` for convenience."""
    if ":" not in target:
        raise ValueError(f"Expected `module:callable`, got {target!r}")
    cwd = os.getcwd()
    if cwd not in sys.path:
        sys.path.insert(0, cwd)
    mod_path, attr = target.split(":", 1)
    fn = getattr(importlib.import_module(mod_path), attr)
    if not callable(fn):
        raise ValueError(f"{target!r} is not callable")
    return cast("Callable[..., Any]", fn)


def _drive_one_run(
    agent: Callable[..., Any],
    mutated: Recording,
    agent_input: dict[str, Any] | None,
) -> Recording:
    """Drive the agent once against a Tier-1 replayer of ``mutated``; return the fresh Recording."""
    env = Tier1Replayer.from_recording(mutated)
    rec = Recorder(config=RecorderConfig(apply_redaction=False))
    with current_recorder(rec), current_environment(env):
        try:
            result = agent(agent_input) if agent_input is not None else agent()
            rec.set_final_output(result)
        except ReplayMiss as e:
            rec.set_final_output({"__replay_miss__": str(e)})
        except Exception as e:
            rec.set_final_output({"__error__": f"{type(e).__name__}: {e}"})
    return rec.recording


def _run_scenario(
    agent: Callable[..., Any],
    scenario: Scenario,
    mutated: Recording,
    *,
    n_runs: int,
    agent_input: dict[str, Any] | None,
    judge: Any | None = None,
) -> ScenarioReport:
    runs = [_drive_one_run(agent, mutated, agent_input) for _ in range(n_runs)]
    return aggregate_runs(
        runs,
        scenario_op=scenario.op_name,
        failure_class=scenario.failure_class,
        seed=scenario.seed,
        applicable=len(mutated.steps) > 0,
        judge=judge,
    )


def orchestrate(
    baseline: Recording,
    agent: Callable[..., Any] | str,
    *,
    config: OrchestratorConfig | None = None,
) -> ReliabilityReport:
    """Run the full record → scenarios → replay → score loop and return a ReliabilityReport."""
    cfg = config or OrchestratorConfig()
    fn = agent if callable(agent) else resolve_agent(agent)

    scenarios = generate_default_scenarios(baseline, seed=cfg.seed)
    reports = [
        _run_scenario(
            fn,
            sc,
            mutated,
            n_runs=cfg.n_runs,
            agent_input=cfg.agent_input,
            judge=cfg.judge,
        )
        for sc, mutated in scenarios
    ]
    return compose_report(
        baseline,
        reports,
        fail_under=cfg.fail_under,
        aggregator=cfg.aggregator,
    )
