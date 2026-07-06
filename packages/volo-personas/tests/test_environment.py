"""PersonaEnvironment + driver: a multi-turn agent runs deterministically against a persona."""

from __future__ import annotations

from typing import Any

from volo_core import Recording, ToolCallPayload, get_active_environment
from volo_personas import (
    Persona,
    PersonaEnvironment,
    SimulatedUser,
    drive_persona,
)


def _traveler() -> Persona:
    return Persona(
        name="traveler",
        goal="book a flight to Tokyo",
        facts={"destination": "Tokyo", "cabin": "economy", "one-way or round": "one-way"},
        expected=["Tokyo", "economy"],
    )


def _clarifying_agent(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    env = get_active_environment()
    assert env is not None
    reg = env.tool_registry()
    dest = reg.call("ask_user", {"question": "What is your destination?"})["answer"]
    cabin = reg.call("ask_user", {"question": "Which cabin?"})["answer"]
    return {"summary": f"flight to {dest} in {cabin}", "destination": dest}


def test_simulated_user_tracks_transcript() -> None:
    user = SimulatedUser(persona=_traveler())
    assert user.ask("What is your destination?") == "Tokyo"
    assert user.turns == 1
    assert user.transcript[0] == {"question": "What is your destination?", "answer": "Tokyo"}


def test_persona_environment_intercepts_ask_user() -> None:
    env = PersonaEnvironment(_traveler())
    reg = env.tool_registry()
    assert reg.call("ask_user", {"question": "Which cabin?"})["answer"] == "economy"
    assert env.user.turns == 1


def test_non_user_tools_pass_through_to_recording() -> None:
    rec = Recording()
    rec.add_step(ToolCallPayload(tool="search", request={"q": "x"}, response={"hits": 7}))
    env = PersonaEnvironment(_traveler(), recording=rec)
    reg = env.tool_registry()
    # the recorded tool still replays
    assert reg.call("search", {"q": "x"}) == {"hits": 7}
    # and the user tool is still answered by the persona
    assert reg.call("ask_user", {"question": "destination?"})["answer"] == "Tokyo"


def test_drive_persona_runs_a_multiturn_agent_and_meets_goal() -> None:
    report = drive_persona(_clarifying_agent, _traveler())
    assert report.turns == 2
    assert report.goal_met is True
    assert report.final_output["summary"] == "flight to Tokyo in economy"
    assert [t["answer"] for t in report.transcript] == ["Tokyo", "economy"]


def test_drive_persona_reports_unmet_goal() -> None:
    persona = Persona(name="p", expected=["Paris"], facts={"destination": "Tokyo"})
    report = drive_persona(_clarifying_agent, persona)
    assert report.goal_met is False


def test_drive_persona_captures_agent_error() -> None:
    def boom(payload: Any = None) -> dict[str, Any]:
        raise ValueError("nope")

    report = drive_persona(boom, _traveler())
    assert report.error is not None and "nope" in report.error
    assert report.goal_met is False
