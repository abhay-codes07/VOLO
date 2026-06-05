"""volo-reliability — the metrics engine (bible §4 subsystem 4, §9.4, ADR-0006).

Four orthogonal dimensions, then aggregated to a single ship/no-ship verdict.
"""

from volo_reliability.judge import (
    FrontierJudge,
    HeuristicJudge,
    JudgeProvider,
    OllamaJudge,
    OpenAICompatJudge,
    default_judge,
)
from volo_reliability.metrics import (
    consistency_under_repetition,
    decision_determinism,
    faithfulness,
    trajectory_determinism,
    trajectory_shape,
)
from volo_reliability.report import (
    METRIC_NAMES,
    ReliabilityReport,
    ScenarioReport,
    Verdict,
    aggregate_runs,
    compose_report,
)

__all__ = [
    "METRIC_NAMES",
    "FrontierJudge",
    "HeuristicJudge",
    "JudgeProvider",
    "OllamaJudge",
    "OpenAICompatJudge",
    "ReliabilityReport",
    "ScenarioReport",
    "Verdict",
    "aggregate_runs",
    "compose_report",
    "consistency_under_repetition",
    "decision_determinism",
    "default_judge",
    "faithfulness",
    "trajectory_determinism",
    "trajectory_shape",
]
