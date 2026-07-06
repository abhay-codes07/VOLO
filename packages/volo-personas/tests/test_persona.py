"""Persona: fact-match precedence, script fallback, goal check, JSON round-trip."""

from __future__ import annotations

from pathlib import Path

import pytest

from volo_personas import Persona, default_personas, dump_persona, goal_satisfied, load_persona


def _p() -> Persona:
    return Persona(
        name="t",
        goal="g",
        facts={"destination": "Tokyo", "class": "economy"},
        script=["first", "second"],
        default="dunno",
        expected=["Tokyo"],
    )


def test_facts_match_by_keyword_first() -> None:
    p = _p()
    assert p.answer("What is your destination?", script_turn=0) == "Tokyo"
    assert p.answer("Which class?", script_turn=0) == "economy"


def test_script_fallback_advances_only_on_unmatched() -> None:
    p = _p()
    # unmatched questions consume the script in order
    assert p.answer("anything?", script_turn=0) == "first"
    assert p.answer("more?", script_turn=1) == "second"
    assert p.answer("even more?", script_turn=2) == "dunno"  # exhausted -> default


def test_goal_satisfied_requires_all_markers() -> None:
    p = _p()
    assert goal_satisfied({"summary": "flight to Tokyo"}, p) is True
    assert goal_satisfied({"summary": "flight to Paris"}, p) is False
    assert goal_satisfied(None, Persona(name="x")) is True  # no expectations → vacuously met


def test_json_roundtrip(tmp_path: Path) -> None:
    p = _p()
    path = dump_persona(p, tmp_path / "p.json")
    assert load_persona(path) == p


def test_from_dict_requires_name() -> None:
    with pytest.raises(ValueError, match="missing required field 'name'"):
        Persona.from_dict({"goal": "x"})


def test_default_personas_present() -> None:
    names = {p.name for p in default_personas()}
    assert "decisive-traveler" in names
