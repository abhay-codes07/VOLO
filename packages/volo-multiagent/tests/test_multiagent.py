"""Multi-agent: an orchestrator delegates to simulated sub-agents; system verdict + message graph."""

from __future__ import annotations

from typing import Any

from volo_core import get_active_environment
from volo_multiagent import (
    Counterparty,
    MultiAgentEnvironment,
    load_counterparties,
    run_multiagent,
)
from volo_personas import Persona


def _researcher() -> Counterparty:
    return Counterparty("researcher", Persona(name="researcher", facts={"research": "3 sources"}))


def _writer() -> Counterparty:
    return Counterparty("writer", Persona(name="writer", facts={"write": "a tidy draft"}))


def _orchestrator(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    env = get_active_environment()
    assert env is not None
    reg = env.tool_registry()
    findings = reg.call("delegate", {"to": "researcher", "message": "research topic"})["reply"]
    draft = reg.call("delegate", {"to": "writer", "message": "write it up"})["reply"]
    return {"findings": findings, "draft": draft}


def test_healthy_system_reaches_all_agents() -> None:
    report = run_multiagent(_orchestrator, [_researcher(), _writer()])
    assert report.verdict == "healthy"
    assert report.reached == ["researcher", "writer"]
    assert report.unreached == [] and report.unknown_agents == []
    assert report.delegations == 2
    assert report.messages[0].to == "researcher" and "3 sources" in (report.messages[0].reply or "")
    assert report.final_output["findings"] == "3 sources"


def test_delegation_to_unknown_agent_is_broken() -> None:
    # only 'researcher' exists; the orchestrator also calls 'writer' → unknown
    report = run_multiagent(_orchestrator, [_researcher()])
    assert report.verdict == "broken"
    assert report.unknown_agents == ["writer"]


def test_unreached_counterparty_reported() -> None:
    report = run_multiagent(
        _orchestrator,
        [_researcher(), _writer(), Counterparty("reviewer", Persona(name="reviewer"))],
    )
    assert "reviewer" in report.unreached
    # unreached alone is not "broken" (the orchestrator may not need every agent)
    assert report.verdict == "healthy"


def test_expected_markers_gate_the_verdict() -> None:
    ok = run_multiagent(_orchestrator, [_researcher(), _writer()], expected=["draft"])
    assert ok.verdict == "healthy" and ok.goal_met
    bad = run_multiagent(_orchestrator, [_researcher(), _writer()], expected=["NONEXISTENT"])
    assert bad.verdict == "broken" and not bad.goal_met


def test_orchestrator_error_is_broken() -> None:
    def boom(payload: Any = None) -> dict[str, Any]:
        raise ValueError("crew collapsed")

    report = run_multiagent(boom, [_researcher()])
    assert report.verdict == "broken" and report.error is not None


def test_agent_prefixed_tool_also_routes() -> None:
    def orch(payload: Any = None) -> dict[str, Any]:
        env = get_active_environment()
        assert env is not None
        r = env.tool_registry().call("agent.researcher", {"message": "go"})
        return {"r": r["reply"]}

    report = run_multiagent(orch, [_researcher()])
    assert report.reached == ["researcher"] and report.verdict == "healthy"


def test_scripted_multi_turn_counterparty() -> None:
    # a persona with no matching fact walks its script across repeated delegations
    cp = Counterparty("helper", Persona(name="helper", script=["first", "second"], default="done"))

    def orch(payload: Any = None) -> dict[str, Any]:
        env = get_active_environment()
        assert env is not None
        reg = env.tool_registry()
        return {
            "turns": [
                reg.call("delegate", {"to": "helper", "message": f"q{i}"})["reply"]
                for i in range(3)
            ]
        }

    report = run_multiagent(orch, [cp])
    assert report.final_output["turns"] == ["first", "second", "done"]


def test_load_counterparties_from_dict() -> None:
    cps = load_counterparties(
        {"researcher": {"facts": {"research": "ok"}}, "writer": {"script": ["draft"]}}
    )
    assert {c.name for c in cps} == {"researcher", "writer"}
    assert cps[0].persona.answer("research this", script_turn=0) == "ok"


def test_report_json_roundtrip() -> None:
    from volo_multiagent import SystemReport

    report = run_multiagent(_orchestrator, [_researcher(), _writer()])
    restored = SystemReport.model_validate_json(report.to_json())
    assert restored.verdict == "healthy" and len(restored.messages) == 2


def test_env_passes_non_delegation_tools_through() -> None:
    from volo_core import Recording, ToolCallPayload

    rec = Recording()
    rec.add_step(ToolCallPayload(tool="search", request={"q": "x"}, response={"hits": 5}))
    env = MultiAgentEnvironment([_researcher()], recording=rec)
    reg = env.tool_registry()
    assert reg.call("search", {"q": "x"}) == {"hits": 5}  # recorded tool replays
    assert reg.call("delegate", {"to": "researcher", "message": "m"})["reply"]  # delegation routes
