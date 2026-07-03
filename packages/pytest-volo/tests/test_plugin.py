"""pytest-volo, tested with pytester: real inner test suites against real recordings."""

from __future__ import annotations

import pytest

from volo_core import ModelCallPayload, Recording, RunMeta, ToolCallPayload


def _baseline_json() -> str:
    rec = Recording()
    rec.add_step(ToolCallPayload(tool="search", request={"q": "x"}, response={"hits": 1}))
    rec.add_step(
        ModelCallPayload(
            provider="ollama",
            model="llama3.2:3b",
            request={"prompt": "summarize"},
            response={"text": "one hit"},
        )
    )
    rec.final_output = {"answer": "one hit"}
    return rec.to_json()


def _mcp_json() -> str:
    rec = Recording(agent_meta=RunMeta(framework="mcp"))
    rec.add_step(
        ToolCallPayload(
            tool="mcp.tool:add",
            request={"a": 1, "b": 2},
            response={"result": {"content": [{"type": "text", "text": "3"}], "isError": False}},
        )
    )
    return rec.to_json()


@pytest.fixture
def project(pytester: pytest.Pytester) -> pytest.Pytester:
    pytester.path.joinpath("baseline.json").write_text(_baseline_json(), encoding="utf-8")
    pytester.path.joinpath("mcp.json").write_text(_mcp_json(), encoding="utf-8")
    return pytester


def test_volo_recording_fixture_loads_the_marker_path(project: pytest.Pytester) -> None:
    project.makepyfile(
        """
        import pytest

        @pytest.mark.volo_recording("baseline.json")
        def test_loads(volo_recording):
            assert len(volo_recording.steps) == 2
            assert volo_recording.final_output == {"answer": "one hit"}
        """
    )
    project.runpytest().assert_outcomes(passed=1)


def test_missing_marker_fails_with_usage_hint(project: pytest.Pytester) -> None:
    project.makepyfile(
        """
        def test_no_marker(volo_recording):
            pass
        """
    )
    result = project.runpytest()
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(["*needs @pytest.mark.volo_recording*"])


def test_missing_file_is_a_usage_error(project: pytest.Pytester) -> None:
    project.makepyfile(
        """
        import pytest

        @pytest.mark.volo_recording("nope.json")
        def test_gone(volo_recording):
            pass
        """
    )
    result = project.runpytest()
    result.stdout.fnmatch_lines(["*recording not found*"])


def test_volo_env_replays_and_is_active(project: pytest.Pytester) -> None:
    project.makepyfile(
        """
        import pytest
        from volo_core.context import get_active_environment

        @pytest.mark.volo_recording("baseline.json")
        def test_env(volo_env):
            assert get_active_environment() is volo_env
            assert volo_env.tool_registry().call("search", {"q": "x"}) == {"hits": 1}
        """
    )
    project.runpytest().assert_outcomes(passed=1)


def test_volo_env_tier2_flags_instead_of_hallucinating(project: pytest.Pytester) -> None:
    project.makepyfile(
        """
        import pytest
        from volo_simulator import Tier2Miss

        @pytest.mark.volo_recording("baseline.json", tier=2)
        def test_tier2(volo_env):
            with pytest.raises(Tier2Miss):
                volo_env.tool_registry().call("search", {"q": "never-recorded"})
        """
    )
    project.runpytest().assert_outcomes(passed=1)


def test_volo_scenario_parametrizes_over_the_default_library(project: pytest.Pytester) -> None:
    project.makepyfile(
        """
        import pytest
        from volo_core.context import get_active_environment

        @pytest.mark.volo_recording("baseline.json")
        def test_world(volo_scenario):
            assert volo_scenario.scenario.op_name
            assert volo_scenario.scenario.failure_class
            assert get_active_environment() is volo_scenario.env
        """
    )
    result = project.runpytest("-v")
    result.assert_outcomes(passed=7)  # the seven default operators
    result.stdout.fnmatch_lines(["*corrupt_field*", "*prompt_injection*"])


def test_mcp_recording_auto_selects_the_fuzz_library(project: pytest.Pytester) -> None:
    project.makepyfile(
        """
        import pytest

        @pytest.mark.volo_recording("mcp.json")
        def test_world(volo_scenario):
            # every MCP mutation is still a servable envelope world
            for step in volo_scenario.recording.steps:
                assert set(step.payload.response) <= {"result", "error"}
        """
    )
    result = project.runpytest()
    result.assert_outcomes(passed=4)  # the four MCP fuzz operators


def test_fuzz_kwarg_forces_the_library(project: pytest.Pytester) -> None:
    project.makepyfile(
        """
        import pytest

        @pytest.mark.volo_recording("mcp.json", fuzz="default")
        def test_world(volo_scenario):
            pass
        """
    )
    project.runpytest().assert_outcomes(passed=7)


def test_volo_run_produces_a_report_and_helpers_agree(project: pytest.Pytester) -> None:
    project.makepyfile(
        """
        import pytest
        from pytest_volo import assert_no_ship, assert_ship

        @pytest.mark.volo_recording("baseline.json")
        def test_verdict(volo_run):
            report = volo_run(lambda payload=None: {"answer": "one hit"}, n_runs=2)
            assert report.verdict in ("ship", "no_ship")
            assert len(report.scenarios) == 7
            if report.verdict == "ship":
                assert_ship(report)
                with pytest.raises(AssertionError, match="expected verdict 'no_ship'"):
                    assert_no_ship(report)
            else:
                assert_no_ship(report)
                with pytest.raises(AssertionError, match="expected verdict 'ship'"):
                    assert_ship(report)
        """
    )
    project.runpytest().assert_outcomes(passed=1)


def test_recordings_dir_ini_option(project: pytest.Pytester) -> None:
    sub = project.path / "fixtures"
    sub.mkdir()
    (project.path / "baseline.json").replace(sub / "baseline.json")
    project.makeini(
        """
        [pytest]
        volo_recordings_dir = fixtures
        """
    )
    project.makepyfile(
        """
        import pytest

        @pytest.mark.volo_recording("baseline.json")
        def test_loads(volo_recording):
            assert len(volo_recording.steps) == 2
        """
    )
    project.runpytest().assert_outcomes(passed=1)
