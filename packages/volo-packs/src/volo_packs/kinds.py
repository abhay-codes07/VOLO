"""Pack kinds — per-kind item validation + starter content (newplan M20).

A pack is generic transport (manifest + items); each *kind* knows how to validate its items and
how to seed a starter pack from Volo's built-ins. Adding a kind is one entry here.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

from volo_personas import Persona, default_personas
from volo_redteam import Attack, default_attack_library
from volo_scenarios import default_library

PackKind = Literal["attacks", "personas", "scenarios"]
PACK_KINDS: tuple[PackKind, ...] = ("attacks", "personas", "scenarios")

_SCENARIO_OPS: frozenset[str] = frozenset(op.name for op in default_library())


def _validate_attack(item: dict[str, Any]) -> None:
    Attack.from_dict(item)  # raises ValueError on bad shape / canary mismatch


def _validate_persona(item: dict[str, Any]) -> None:
    Persona.from_dict(item)  # raises ValueError when 'name' is missing


def _validate_scenario(item: dict[str, Any]) -> None:
    op = item.get("op")
    if op not in _SCENARIO_OPS:
        raise ValueError(f"unknown scenario op {op!r}; known: {sorted(_SCENARIO_OPS)}")
    if "seed" in item and not isinstance(item["seed"], int):
        raise ValueError(f"scenario {op!r}: seed must be an integer")


_VALIDATORS: dict[str, Callable[[dict[str, Any]], None]] = {
    "attacks": _validate_attack,
    "personas": _validate_persona,
    "scenarios": _validate_scenario,
}


def validate_items(kind: str, items: list[dict[str, Any]]) -> list[str]:
    """Return a list of per-item problems (empty ⇒ all valid)."""
    if kind not in _VALIDATORS:
        return [f"unknown pack kind {kind!r}; known: {list(PACK_KINDS)}"]
    validator = _VALIDATORS[kind]
    problems: list[str] = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            problems.append(f"item {i}: not an object")
            continue
        try:
            validator(item)
        except ValueError as exc:
            problems.append(f"item {i}: {exc}")
    return problems


def starter_items(kind: str) -> list[dict[str, Any]]:
    """Seed content for ``volo pack init`` — the built-in library for the kind."""
    if kind == "attacks":
        return [a.to_dict() for a in default_attack_library()]
    if kind == "personas":
        return [p.to_dict() for p in default_personas()]
    if kind == "scenarios":
        return [
            {"op": op.name, "seed": op.seed, "params": dict(op.params)} for op in default_library()
        ]
    raise ValueError(f"unknown pack kind {kind!r}; known: {list(PACK_KINDS)}")
