"""Run an agent through reliability + red-team and certify it (M33)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from volo_certify.certificate import CertCriteria, Certificate, evaluate
from volo_core import Recording
from volo_redteam import run_redteam
from volo_reliability import METRIC_NAMES
from volo_runner import OrchestratorConfig, orchestrate


def certify(
    baseline: Recording,
    agent: Callable[..., Any],
    *,
    agent_name: str | None = None,
    agent_input: dict[str, Any] | None = None,
    criteria: CertCriteria | None = None,
    n_runs: int = 3,
    issued_at: str | None = None,
) -> Certificate:
    """Run the reliability suite + the red-team corpus against ``agent`` and issue a Certificate."""
    report = orchestrate(
        baseline,
        agent,
        config=OrchestratorConfig(n_runs=n_runs, agent_input=agent_input),
    )
    annex = run_redteam(baseline, agent, agent_input=agent_input, agent_name=agent_name)
    aggregate = {m: report.aggregate.get(m, 0.0) for m in METRIC_NAMES}
    return evaluate(
        agent_name=agent_name or report.agent_name or "agent",
        reliability_verdict=report.verdict,
        aggregate=aggregate,
        safety_verdict=annex.verdict,
        attacks_run=annex.attacks_run,
        compromised=annex.compromised,
        criteria=criteria,
        issued_at=issued_at,
    )
