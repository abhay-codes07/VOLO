"""Evidence pack — a signed, deterministic bundle of compliance evidence (M29 / ADR-0029).

An ``EvidencePack`` gathers the Volo artifacts produced for an agent (reliability report, red-team
safety annex, drift-monitoring report), evaluates each catalogued control against them, and seals
the result with a content checksum (and optional HMAC signature). The checksum excludes the
volatile ``generated_at`` stamp, so re-generating from the same evidence yields the same
checksum — the pack is reproducible, and any later edit is detectable.
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from volo_core import canonical_json

HMAC_SHA256 = "hmac-sha256"
ControlState = Literal["satisfied", "partial", "unmet"]
_ORDER: dict[str, int] = {"unmet": 0, "partial": 1, "satisfied": 2}


class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str  # reliability | redteam_safety | drift_monitoring
    passed: bool
    summary: str
    detail: dict[str, Any] = Field(default_factory=dict)


class ControlStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    framework: str
    control_id: str
    title: str
    state: ControlState
    evidence_kinds: list[str] = Field(default_factory=list)
    note: str = ""


class EvidenceSignature(BaseModel):
    model_config = ConfigDict(extra="forbid")

    publisher: str
    algorithm: str
    value: str


class EvidencePack(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_name: str
    frameworks: list[str]
    generated_at: str | None = None  # metadata; NOT part of the checksum
    evidence: list[EvidenceItem] = Field(default_factory=list)
    controls: list[ControlStatus] = Field(default_factory=list)
    checksum: str = ""
    signature: EvidenceSignature | None = None

    def sealed(self) -> EvidencePack:
        """Return a copy with the content checksum filled in."""
        return self.model_copy(update={"checksum": self.content_checksum()})

    def content_checksum(self) -> str:
        material = {
            "agent_name": self.agent_name,
            "frameworks": sorted(self.frameworks),
            "evidence": [e.model_dump() for e in self.evidence],
            "controls": [c.model_dump() for c in self.controls],
        }
        return hashlib.sha256(canonical_json(material).encode("utf-8")).hexdigest()

    def counts(self) -> dict[str, int]:
        out = {"satisfied": 0, "partial": 0, "unmet": 0}
        for c in self.controls:
            out[c.state] += 1
        return out

    @property
    def all_satisfied(self) -> bool:
        return all(c.state == "satisfied" for c in self.controls)

    def to_json(self, *, indent: int = 2) -> str:
        return self.model_dump_json(indent=indent)


def worst(states: list[ControlState]) -> ControlState:
    """The weakest state wins — a control is only as strong as its weakest required evidence."""
    if not states:
        return "unmet"
    return min(states, key=lambda s: _ORDER[s])


# ── signing (shared-secret; mirrors volo-packs M25 / ADR-0028) ───────────────


def _message(pack: EvidencePack) -> bytes:
    return f"{pack.agent_name}:{pack.checksum}".encode()


def sign_evidence(pack: EvidencePack, *, publisher: str, secret: str) -> EvidencePack:
    """Sign a sealed pack; returns a copy carrying the signature."""
    if not pack.checksum:
        pack = pack.sealed()
    value = hmac.new(secret.encode("utf-8"), _message(pack), hashlib.sha256).hexdigest()
    return pack.model_copy(
        update={
            "signature": EvidenceSignature(publisher=publisher, algorithm=HMAC_SHA256, value=value)
        }
    )


def verify_evidence(pack: EvidencePack, keyring: dict[str, str]) -> bool:
    sig = pack.signature
    if sig is None or sig.algorithm != HMAC_SHA256:
        return False
    if pack.checksum != pack.content_checksum():  # content tampered
        return False
    secret = keyring.get(sig.publisher)
    if secret is None:
        return False
    expected = hmac.new(secret.encode("utf-8"), _message(pack), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig.value)
