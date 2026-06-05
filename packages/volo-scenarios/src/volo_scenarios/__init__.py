"""volo-scenarios — adversarial scenario generator (bible §4 subsystem 3, §9.3, ADR-0005).

Seven typed operators. Each is pure: ``apply(rec) -> Recording`` returns a new Recording without
mutating the input.
"""

from volo_scenarios.base import Scenario, ScenarioOp
from volo_scenarios.library import default_library, generate_default_scenarios
from volo_scenarios.operators import (
    AmbiguousUserTurn,
    CorruptField,
    DropToolResult,
    InjectLatency,
    LongHorizonRepeat,
    PromptInjection,
    ReorderSteps,
)

__all__ = [
    "AmbiguousUserTurn",
    "CorruptField",
    "DropToolResult",
    "InjectLatency",
    "LongHorizonRepeat",
    "PromptInjection",
    "ReorderSteps",
    "Scenario",
    "ScenarioOp",
    "default_library",
    "generate_default_scenarios",
]
