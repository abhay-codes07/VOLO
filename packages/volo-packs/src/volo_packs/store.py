"""PackStore — a local install directory of validated packs, with an index (newplan M20).

Mirrors ``CorpusBank`` (M13): a directory of pack JSON files plus ``index.json``. Install
validates the pack (checksum + schema) and refuses a duplicate ``name@version`` unless forced.
The registry (M21) will publish/fetch against this same on-disk shape.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from volo_packs.pack import Pack, read_pack, validate_pack, write_pack

INDEX_NAME = "index.json"


@dataclass(frozen=True)
class InstalledPack:
    name: str
    version: str
    kind: str
    n_items: int
    checksum: str
    file: str


class PackInstallError(RuntimeError):
    """Raised when a pack fails validation or collides with an installed version."""


class PackStore:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)

    def install(self, pack: Pack, *, force: bool = False) -> InstalledPack:
        problems = validate_pack(pack)
        if problems:
            raise PackInstallError(f"pack {pack.ref} is invalid: {problems[0]}")
        entries = self.entries()
        if not force and any(
            e.name == pack.manifest.name and e.version == pack.manifest.version for e in entries
        ):
            raise PackInstallError(f"{pack.ref} is already installed (use force to overwrite)")
        entries = [
            e
            for e in entries
            if not (e.name == pack.manifest.name and e.version == pack.manifest.version)
        ]
        file_name = f"{pack.manifest.name}@{pack.manifest.version}.json"
        write_pack(pack, self.root / file_name)
        entry = InstalledPack(
            name=pack.manifest.name,
            version=pack.manifest.version,
            kind=pack.manifest.kind,
            n_items=pack.manifest.n_items,
            checksum=pack.manifest.checksum,
            file=file_name,
        )
        entries.append(entry)
        self._write_index(entries)
        return entry

    def entries(self) -> list[InstalledPack]:
        index = self.root / INDEX_NAME
        if not index.exists():
            return []
        raw = json.loads(index.read_text(encoding="utf-8"))
        return [InstalledPack(**e) for e in raw.get("packs", [])]

    def load(self, entry: InstalledPack) -> Pack:
        return read_pack(self.root / entry.file)

    def _write_index(self, entries: list[InstalledPack]) -> None:
        blob = {"packs": [asdict(e) for e in sorted(entries, key=lambda e: (e.name, e.version))]}
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / INDEX_NAME).write_text(
            json.dumps(blob, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
