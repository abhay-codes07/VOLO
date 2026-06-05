"""Tripwire: every workspace package must import cleanly.

Catches the "moved a file, forgot the re-export" failure mode early. Cheap and high-signal.
"""

from __future__ import annotations

import importlib

import pytest

PACKAGES = [
    "volo_core",
    "volo_sdk",
    "volo_simulator",
    "volo_scenarios",
    "volo_reliability",
    "volo_runner",
    "volo_diff",
    "volo_models",
    "volo_cli",
]


@pytest.mark.parametrize("pkg", PACKAGES)
def test_workspace_package_imports(pkg: str) -> None:
    importlib.import_module(pkg)


def test_example_agent_runs() -> None:
    from examples.echo_agent import run

    assert run({"text": "hello"}) == {"echo": "HELLO"}
