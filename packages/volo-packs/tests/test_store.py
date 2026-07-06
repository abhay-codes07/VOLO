"""PackStore: install validates + dedupes by name@version; index persists."""

from __future__ import annotations

from pathlib import Path

import pytest

from volo_packs import PackInstallError, PackStore, build_pack, starter_items


def _pack(name: str = "p", version: str = "1.0.0", kind: str = "attacks"):
    return build_pack(name=name, version=version, kind=kind, items=starter_items(kind))


def test_install_and_list(tmp_path: Path) -> None:
    store = PackStore(tmp_path / "packs")
    entry = store.install(_pack())
    assert entry.name == "p" and entry.version == "1.0.0"
    assert [e.ref if hasattr(e, "ref") else (e.name, e.version) for e in store.entries()]
    loaded = store.load(store.entries()[0])
    assert loaded.manifest.kind == "attacks"


def test_duplicate_version_rejected_unless_forced(tmp_path: Path) -> None:
    store = PackStore(tmp_path / "packs")
    store.install(_pack())
    with pytest.raises(PackInstallError, match="already installed"):
        store.install(_pack())
    # force overwrites in place (still one entry)
    store.install(_pack(), force=True)
    assert len(store.entries()) == 1


def test_different_versions_coexist(tmp_path: Path) -> None:
    store = PackStore(tmp_path / "packs")
    store.install(_pack(version="1.0.0"))
    store.install(_pack(version="1.1.0"))
    assert {e.version for e in store.entries()} == {"1.0.0", "1.1.0"}


def test_install_rejects_tampered_pack(tmp_path: Path) -> None:
    store = PackStore(tmp_path / "packs")
    pack = _pack(kind="personas")
    pack.items.append({"name": "sneaky"})  # invalidates the checksum
    with pytest.raises(PackInstallError, match="invalid"):
        store.install(pack)


def test_index_persists_across_instances(tmp_path: Path) -> None:
    root = tmp_path / "packs"
    PackStore(root).install(_pack())
    assert len(PackStore(root).entries()) == 1
