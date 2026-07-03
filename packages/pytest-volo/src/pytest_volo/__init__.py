"""pytest-volo — agent reliability tests as plain pytest tests (newplan M12).

The plugin (auto-registered via the ``pytest11`` entry point) provides the
``@pytest.mark.volo_recording`` marker and the ``volo_recording`` / ``volo_env`` /
``volo_scenario`` / ``volo_run`` fixtures; this module holds the assertion helpers.
"""

from __future__ import annotations

from pytest_volo.plugin import VoloScenario
from volo_reliability import ReliabilityReport

__all__ = ["ReliabilityReport", "VoloScenario", "assert_no_ship", "assert_ship"]


def _describe(report: ReliabilityReport) -> str:
    lines = [f"verdict={report.verdict!r} (fail_under={report.fail_under})"]
    lines.append(f"  aggregate: {report.aggregate}")
    for s in report.scenarios:
        lines.append(f"  {s.scenario_op:20} [{s.failure_class}] {s.metrics}")
    return "\n".join(lines)


def assert_ship(report: ReliabilityReport) -> None:
    """Fail the test unless the reliability verdict is ``ship``, with the surface attached."""
    if report.verdict != "ship":
        raise AssertionError(f"expected verdict 'ship'\n{_describe(report)}")


def assert_no_ship(report: ReliabilityReport) -> None:
    """Fail the test unless the verdict is ``no_ship`` — for tests that prove a gate closes."""
    if report.verdict != "no_ship":
        raise AssertionError(f"expected verdict 'no_ship'\n{_describe(report)}")
