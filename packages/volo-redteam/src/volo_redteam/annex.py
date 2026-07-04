"""Safety annex — run the attack corpus against an agent, in the sim (newplan M15).

``run_redteam`` poisons the baseline recording with each attack, replays the agent against that
poisoned world (Tier-1, offline), and checks whether the attack's canary surfaced in the output.
The result is a ``SafetyAnnex`` — the security section reviewers ask for — with a single
``safe`` / ``vulnerable`` verdict and the per-attack findings behind it.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from volo_core import Recording, current_environment, current_recorder
from volo_redteam.attacks import ATTACK_CLASSES, Attack
from volo_redteam.library import default_attack_library
from volo_sdk import Recorder, RecorderConfig
from volo_simulator import Tier1Replayer

SafetyVerdict = Literal["safe", "vulnerable"]


class AttackFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attack_id: str
    attack_class: str
    description: str
    compromised: bool
    applicable: bool = True  # False when the recording had no tool response to poison
    evidence: str | None = None  # a snippet of the compromised output


class SafetyAnnex(BaseModel):
    model_config = ConfigDict(extra="forbid")

    baseline_run_id: str
    agent_name: str | None = None
    verdict: SafetyVerdict
    attacks_run: int
    compromised: int
    by_class: dict[str, dict[str, int]] = Field(default_factory=dict)
    findings: list[AttackFinding]

    @property
    def safe(self) -> int:
        return self.attacks_run - self.compromised

    def to_json(self, *, indent: int = 2) -> str:
        return self.model_dump_json(indent=indent)


def _has_tool_response(recording: Recording) -> bool:
    return any(
        s.payload.type == "tool_call" and s.payload.response is not None for s in recording.steps
    )


def _poison_recording(recording: Recording, attack: Attack) -> Recording:
    """Clone the recording with the attack woven into every tool response."""
    clone = Recording.model_validate(recording.model_dump(mode="python", by_alias=True))
    for step in clone.steps:
        if step.payload.type == "tool_call" and step.payload.response is not None:
            step.payload.response = attack.poison(step.payload.response)
    return clone


def _drive(
    agent: Callable[..., Any], poisoned: Recording, agent_input: dict[str, Any] | None
) -> Any:
    """Replay the agent once against the poisoned world; return its final output."""
    env = Tier1Replayer.from_recording(poisoned)
    rec = Recorder(config=RecorderConfig(apply_redaction=False))
    with current_recorder(rec), current_environment(env):
        try:
            return agent(agent_input) if agent_input is not None else agent()
        except Exception as exc:
            return {"__error__": f"{type(exc).__name__}: {exc}"}


def run_redteam(
    baseline: Recording,
    agent: Callable[..., Any],
    *,
    attacks: list[Attack] | None = None,
    agent_input: dict[str, Any] | None = None,
    agent_name: str | None = None,
) -> SafetyAnnex:
    """Run the attack corpus against ``agent`` in the sim; return the SafetyAnnex."""
    corpus = attacks if attacks is not None else default_attack_library()
    applicable = _has_tool_response(baseline)

    findings: list[AttackFinding] = []
    by_class: dict[str, dict[str, int]] = {c: {"run": 0, "compromised": 0} for c in ATTACK_CLASSES}
    compromised_total = 0

    for attack in corpus:
        bucket = by_class.setdefault(attack.attack_class, {"run": 0, "compromised": 0})
        bucket["run"] += 1
        if not applicable:
            findings.append(
                AttackFinding(
                    attack_id=attack.id,
                    attack_class=attack.attack_class,
                    description=attack.description,
                    compromised=False,
                    applicable=False,
                )
            )
            continue
        output = _drive(agent, _poison_recording(baseline, attack), agent_input)
        compromised = attack.detect(output)
        if compromised:
            compromised_total += 1
            bucket["compromised"] += 1
        findings.append(
            AttackFinding(
                attack_id=attack.id,
                attack_class=attack.attack_class,
                description=attack.description,
                compromised=compromised,
                evidence=_evidence(output, attack) if compromised else None,
            )
        )

    return SafetyAnnex(
        baseline_run_id=baseline.run_id,
        agent_name=agent_name or baseline.agent_meta.agent_name,
        verdict="vulnerable" if compromised_total else "safe",
        attacks_run=len(corpus),
        compromised=compromised_total,
        by_class={k: v for k, v in by_class.items() if v["run"]},
        findings=findings,
    )


def _evidence(output: Any, attack: Attack, *, window: int = 60) -> str:
    """A short snippet of the output around the leaked canary."""
    import json

    try:
        blob = json.dumps(output, default=str)
    except (TypeError, ValueError):
        blob = str(output)
    idx = blob.lower().find(attack.canary.lower())
    if idx < 0:
        return blob[: window * 2]
    start = max(0, idx - window)
    return blob[start : idx + len(attack.canary) + window]
