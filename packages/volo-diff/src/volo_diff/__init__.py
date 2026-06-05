"""volo-diff — "git bisect for agents" (bible §4 subsystem 6, ADR-0007).

Step-level diff between two ``Recording``s using LCS over trajectory shape, with per-step payload
comparison on aligned steps. ``compute_diff`` returns a ``Diff`` Pydantic model;
``format_diff`` renders a terminal-friendly report.
"""

from volo_diff.diff import Diff, StepDiff, compute_diff, format_diff

__all__ = ["Diff", "StepDiff", "compute_diff", "format_diff"]
