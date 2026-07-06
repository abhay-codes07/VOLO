"""Pack format — a versioned, checksummed bundle of items (newplan M20 / ADR-0024).

One JSON file: a ``manifest`` (name, semver, kind, checksum, …) plus ``items`` (the kind-specific
payload). The checksum is sha256 over the canonicalized items, so tampering or corruption is
caught by ``validate_pack``. Packs are the shareable unit the registry (M21) and marketplace (P6)
trade in.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from volo_core import canonical_json
from volo_packs.kinds import PACK_KINDS, validate_items

PACK_FORMAT_VERSION = "1"
_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def content_checksum(items: list[dict[str, Any]]) -> str:
    """sha256 over the canonicalized items — stable across key order and whitespace."""
    return hashlib.sha256(canonical_json(items).encode("utf-8")).hexdigest()


class PackManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    version: str  # semver MAJOR.MINOR.PATCH
    kind: str
    checksum: str  # content_checksum(items)
    description: str = ""
    author: str = ""
    pack_format: str = PACK_FORMAT_VERSION
    volo_min_version: str = "2.0.0"
    n_items: int = 0


class Pack(BaseModel):
    model_config = ConfigDict(extra="forbid")

    manifest: PackManifest
    items: list[dict[str, Any]] = Field(default_factory=list)

    @property
    def ref(self) -> str:
        return f"{self.manifest.name}@{self.manifest.version}"

    def to_json(self, *, indent: int = 2) -> str:
        return self.model_dump_json(indent=indent)


def build_pack(
    *,
    name: str,
    version: str,
    kind: str,
    items: list[dict[str, Any]],
    description: str = "",
    author: str = "",
) -> Pack:
    """Assemble a ``Pack``, computing its checksum. Raises on a bad name/semver/kind/items."""
    if not name or not re.match(r"^[a-z0-9][a-z0-9._-]*$", name):
        raise ValueError(f"invalid pack name {name!r} (use lowercase, digits, . _ -)")
    if not _SEMVER.match(version):
        raise ValueError(f"invalid version {version!r} (expected semver MAJOR.MINOR.PATCH)")
    if kind not in PACK_KINDS:
        raise ValueError(f"unknown pack kind {kind!r}; known: {list(PACK_KINDS)}")
    problems = validate_items(kind, items)
    if problems:
        raise ValueError(f"pack has {len(problems)} invalid item(s): {problems[0]}")
    manifest = PackManifest(
        name=name,
        version=version,
        kind=kind,
        checksum=content_checksum(items),
        description=description,
        author=author,
        n_items=len(items),
    )
    return Pack(manifest=manifest, items=items)


def validate_pack(pack: Pack) -> list[str]:
    """Return a list of problems (empty ⇒ valid): semver, checksum, item schema."""
    problems: list[str] = []
    m = pack.manifest
    if not _SEMVER.match(m.version):
        problems.append(f"version {m.version!r} is not semver")
    if m.kind not in PACK_KINDS:
        problems.append(f"unknown kind {m.kind!r}")
    expected = content_checksum(pack.items)
    if m.checksum != expected:
        problems.append(
            f"checksum mismatch: manifest {m.checksum[:12]}... != actual {expected[:12]}..."
        )
    if m.n_items != len(pack.items):
        problems.append(f"n_items {m.n_items} != actual {len(pack.items)}")
    problems.extend(validate_items(m.kind, pack.items))
    return problems


def read_pack(path: Path | str) -> Pack:
    return Pack.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_pack(pack: Pack, path: Path | str) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(pack.to_json() + "\n", encoding="utf-8")
    return target
