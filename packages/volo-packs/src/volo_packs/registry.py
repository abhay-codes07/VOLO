"""Pack registry — publish/install packs by name against a git-backed index (newplan M21).

The registry is a single ``index.json`` living in a public git repo (or any URL / local path):
``{packs: {name: {kind, versions: {version: {url, checksum, n_items}}}}}``. There is **no
registry service** — publishing is a commit to that file, installing is an HTTP GET of the index
plus the pack it points at, checksum-verified on the way in. $0 infra (raw git hosting).

``install_from_registry`` resolves a version (latest by semver if unspecified), fetches the pack,
and refuses it unless its content checksum matches the registry's recorded checksum *and* the pack
validates — so a swapped or corrupted pack can't be installed under a trusted name.
"""

from __future__ import annotations

import urllib.request
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from volo_packs.pack import Pack, content_checksum, validate_pack
from volo_packs.store import InstalledPack, PackInstallError, PackStore

REGISTRY_FORMAT_VERSION = "1"


class RegistryVersion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str
    checksum: str
    n_items: int = 0


class RegistryPack(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str
    versions: dict[str, RegistryVersion] = Field(default_factory=dict)


class RegistryIndex(BaseModel):
    model_config = ConfigDict(extra="forbid")

    registry_format: str = REGISTRY_FORMAT_VERSION
    packs: dict[str, RegistryPack] = Field(default_factory=dict)

    def to_json(self, *, indent: int = 2) -> str:
        return self.model_dump_json(indent=indent)


class RegistryError(RuntimeError):
    """Raised when a pack/version is not in the index or fails verification."""


def _semver_key(version: str) -> tuple[int, ...]:
    try:
        return tuple(int(p) for p in version.split("."))
    except ValueError:
        return (0,)


def _read_source_text(source: str | Path) -> str:
    """Read text from an http(s) URL, a ``file://`` URL, or a local path."""
    s = str(source)
    if s.startswith(("http://", "https://", "file://")):
        with urllib.request.urlopen(s, timeout=15) as resp:
            return resp.read().decode("utf-8")  # type: ignore[no-any-return]
    return Path(s).read_text(encoding="utf-8")


def load_index(source: str | Path) -> RegistryIndex:
    """Load a registry index from a URL or path."""
    return RegistryIndex.model_validate_json(_read_source_text(source))


def save_index(index: RegistryIndex, path: Path | str) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(index.to_json() + "\n", encoding="utf-8")
    return target


def register(index: RegistryIndex, pack: Pack, url: str) -> RegistryIndex:
    """Add ``pack`` (hosted at ``url``) to the index. Mutates and returns it."""
    problems = validate_pack(pack)
    if problems:
        raise RegistryError(f"cannot publish invalid pack {pack.ref}: {problems[0]}")
    name, version, kind = pack.manifest.name, pack.manifest.version, pack.manifest.kind
    existing = index.packs.get(name)
    if existing is not None and existing.kind != kind:
        raise RegistryError(f"{name!r} is registered as kind {existing.kind!r}, not {kind!r}")
    entry = index.packs.setdefault(name, RegistryPack(kind=kind))
    entry.versions[version] = RegistryVersion(
        url=url, checksum=pack.manifest.checksum, n_items=pack.manifest.n_items
    )
    return index


def resolve(
    index: RegistryIndex, name: str, version: str | None = None
) -> tuple[str, RegistryVersion]:
    """Return ``(version, RegistryVersion)`` — the latest by semver when ``version`` is None."""
    pack = index.packs.get(name)
    if pack is None or not pack.versions:
        raise RegistryError(f"pack {name!r} is not in the registry")
    if version is None:
        version = max(pack.versions, key=_semver_key)
    entry = pack.versions.get(version)
    if entry is None:
        available = ", ".join(sorted(pack.versions))
        raise RegistryError(f"{name}@{version} not found; available: {available}")
    return version, entry


def fetch_pack(url: str | Path) -> Pack:
    return Pack.model_validate_json(_read_source_text(url))


def install_from_registry(
    name: str,
    source: str | Path,
    store: PackStore,
    *,
    version: str | None = None,
    force: bool = False,
) -> InstalledPack:
    """Resolve → fetch → verify checksum against the index → validate → install."""
    index = load_index(source)
    resolved_version, entry = resolve(index, name, version)
    pack = fetch_pack(entry.url)

    if pack.manifest.name != name or pack.manifest.version != resolved_version:
        raise RegistryError(
            f"fetched pack is {pack.ref}, expected {name}@{resolved_version} (index/url mismatch)"
        )
    actual = content_checksum(pack.items)
    if actual != entry.checksum:
        raise RegistryError(
            f"checksum mismatch for {pack.ref}: registry {entry.checksum[:12]}... != "
            f"fetched {actual[:12]}... (pack was altered after publishing)"
        )
    try:
        return store.install(pack, force=force)
    except PackInstallError as exc:
        raise RegistryError(str(exc)) from exc


def index_summary(index: RegistryIndex) -> list[dict[str, Any]]:
    """Flat listing for display: one row per (name, latest version)."""
    rows: list[dict[str, Any]] = []
    for name, pack in sorted(index.packs.items()):
        if not pack.versions:
            continue
        latest = max(pack.versions, key=_semver_key)
        rows.append(
            {
                "name": name,
                "kind": pack.kind,
                "latest": latest,
                "versions": sorted(pack.versions, key=_semver_key),
                "n_items": pack.versions[latest].n_items,
            }
        )
    return rows
