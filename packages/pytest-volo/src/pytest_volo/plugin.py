"""The pytest plugin: one marker, four fixtures (newplan M12).

Usage::

    @pytest.mark.volo_recording("recordings/checkout.json")
    def test_agent_survives_adversity(volo_scenario):
        result = my_agent()           # agent uses volo proxies → hits the mutated sim
        assert result["status"] == "ok"

Marker: ``volo_recording(path, *, tier=1, fuzz=None, seed=0)``.
``path`` resolves against (in order) an absolute path, the ``volo_recordings_dir`` ini option
(relative to rootdir), the test file's directory, then rootdir.

Fixtures:

* ``volo_recording`` — the loaded baseline ``Recording``.
* ``volo_env`` — a ``SimulatedEnvironment`` over the baseline (Tier-1, or Tier-2 with
  ``tier=2``), installed as the active environment for the test's duration.
* ``volo_scenario`` — parametrizes the test over the adversarial scenario library (the MCP fuzz
  library when the recording came from ``volo mcp record``, or ``fuzz="mcp"|"default"`` to
  force). Each param is a ``VoloScenario`` with the mutated world already active.
* ``volo_run`` — ``volo_run(agent, ...) -> ReliabilityReport``: the full scenarios → replay →
  score loop, for asserting on the ship/no-ship verdict (see ``pytest_volo.assert_ship``).
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from volo_core import Recording
from volo_core.context import reset_active_environment, set_active_environment
from volo_core.interfaces import SimulatedEnvironment
from volo_mcp import mcp_fuzz_scenarios
from volo_reliability import ReliabilityReport
from volo_runner import OrchestratorConfig, orchestrate
from volo_scenarios import Scenario, generate_default_scenarios
from volo_simulator import Tier1Replayer, Tier2Replayer

MARKER = "volo_recording"


@dataclass(frozen=True)
class VoloScenario:
    """One adversarial world: the scenario metadata + the mutated recording + its live env."""

    scenario: Scenario
    recording: Recording
    env: SimulatedEnvironment


# ---- plugin hooks ----


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addini(
        "volo_recordings_dir",
        help="Base directory (relative to rootdir) for volo_recording marker paths.",
        default="",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "volo_recording(path, *, tier=1, fuzz=None, seed=0): bind a Volo Recording to this "
        "test; enables the volo_recording / volo_env / volo_scenario / volo_run fixtures.",
    )


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """Parametrize any test that asks for ``volo_scenario`` over the scenario library."""
    if "volo_scenario" not in metafunc.fixturenames:
        return
    marker = metafunc.definition.get_closest_marker(MARKER)
    if marker is None:
        return  # the fixture itself will fail with a usage message at setup time
    recording = _load_recording(marker, Path(metafunc.definition.path), metafunc.config)
    seed = int(marker.kwargs.get("seed", 0))
    pairs = _scenario_pairs(recording, marker.kwargs.get("fuzz"), seed)
    metafunc.parametrize(
        "volo_scenario",
        pairs,
        ids=[scenario.op_name for scenario, _ in pairs],
        indirect=True,
    )


# ---- fixtures ----


@pytest.fixture
def volo_recording(request: pytest.FixtureRequest) -> Recording:
    """The baseline Recording named by this test's ``volo_recording`` marker."""
    marker = _require_marker(request)
    return _load_recording(marker, Path(request.node.path), request.config)


@pytest.fixture
def volo_env(
    request: pytest.FixtureRequest, volo_recording: Recording
) -> Iterator[SimulatedEnvironment]:
    """A simulated environment over the baseline, active for the test's duration."""
    marker = _require_marker(request)
    env = _build_env(volo_recording, marker)
    token = set_active_environment(env)
    try:
        yield env
    finally:
        reset_active_environment(token)


@pytest.fixture
def volo_scenario(request: pytest.FixtureRequest) -> Iterator[VoloScenario]:
    """One (scenario, mutated world) pair; the mutated world is the active environment."""
    if not hasattr(request, "param"):  # requested without the marker → no parametrization ran
        _require_marker(request)
        raise pytest.UsageError("volo_scenario could not be parametrized")  # pragma: no cover
    scenario, mutated = request.param
    env = Tier1Replayer.from_recording(mutated)
    token = set_active_environment(env)
    try:
        yield VoloScenario(scenario=scenario, recording=mutated, env=env)
    finally:
        reset_active_environment(token)


@pytest.fixture
def volo_run(
    volo_recording: Recording,
) -> Callable[..., ReliabilityReport]:
    """Run the full scenarios → replay → score loop against the baseline; returns the report."""

    def _run(
        agent: Callable[..., Any] | str,
        *,
        n_runs: int = 2,
        fail_under: float = 0.9,
        seed: int = 0,
        agent_input: dict[str, Any] | None = None,
        judge: Any | None = None,
    ) -> ReliabilityReport:
        config = OrchestratorConfig(
            n_runs=n_runs,
            seed=seed,
            fail_under=fail_under,
            agent_input=agent_input,
            judge=judge,
        )
        return orchestrate(volo_recording, agent, config=config)

    return _run


# ---- internals ----


def _require_marker(request: pytest.FixtureRequest) -> pytest.Mark:
    marker: pytest.Mark | None = request.node.get_closest_marker(MARKER)
    if marker is None or not marker.args:
        pytest.fail(
            "this fixture needs @pytest.mark.volo_recording(<path-to-recording.json>) "
            "on the test (or its class/module)",
            pytrace=False,
        )
    return marker


def _load_recording(marker: pytest.Mark, test_path: Path, config: pytest.Config) -> Recording:
    if not marker.args:
        raise pytest.UsageError(
            "@pytest.mark.volo_recording needs a path argument: volo_recording('rec.json')"
        )
    path = _resolve_path(str(marker.args[0]), test_path, config)
    if not path.exists():
        raise pytest.UsageError(f"volo_recording: recording not found: {path}")
    return Recording.from_json(path.read_text(encoding="utf-8"))


def _resolve_path(raw: str, test_path: Path, config: pytest.Config) -> Path:
    p = Path(raw)
    if p.is_absolute():
        return p
    ini_dir = str(config.getini("volo_recordings_dir") or "")
    if ini_dir:
        candidate = config.rootpath / ini_dir / p
        if candidate.exists():
            return candidate
    candidate = test_path.parent / p
    if candidate.exists():
        return candidate
    return config.rootpath / p


def _build_env(recording: Recording, marker: pytest.Mark) -> SimulatedEnvironment:
    tier = int(marker.kwargs.get("tier", 1))
    seed = int(marker.kwargs.get("seed", 0))
    if tier == 1:
        return Tier1Replayer.from_recording(recording)
    if tier == 2:
        return Tier2Replayer(recording, seed=seed)
    raise pytest.UsageError(f"volo_recording: tier must be 1 or 2, got {tier!r}")


def _scenario_pairs(
    recording: Recording, fuzz: str | None, seed: int
) -> list[tuple[Scenario, Recording]]:
    """Pick the scenario library: explicit ``fuzz=`` wins, else MCP recordings auto-detect."""
    kind = fuzz or ("mcp" if recording.agent_meta.framework == "mcp" else "default")
    if kind == "mcp":
        return mcp_fuzz_scenarios(recording, seed=seed)
    if kind == "default":
        return generate_default_scenarios(recording, seed=seed)
    raise pytest.UsageError(f"volo_recording: fuzz must be 'mcp' or 'default', got {fuzz!r}")
