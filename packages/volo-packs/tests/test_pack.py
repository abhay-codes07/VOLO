"""Pack format: build/validate/checksum, semver, kind item validation, round-trip."""

from __future__ import annotations

from pathlib import Path

import pytest

from volo_packs import (
    build_pack,
    content_checksum,
    read_pack,
    starter_items,
    validate_pack,
    write_pack,
)


def _attack_items() -> list[dict]:
    return starter_items("attacks")


def test_build_pack_computes_checksum_and_count() -> None:
    items = _attack_items()
    pack = build_pack(name="my-attacks", version="1.0.0", kind="attacks", items=items)
    assert pack.manifest.checksum == content_checksum(items)
    assert pack.manifest.n_items == len(items)
    assert pack.ref == "my-attacks@1.0.0"
    assert validate_pack(pack) == []


def test_build_rejects_bad_semver() -> None:
    with pytest.raises(ValueError, match="semver"):
        build_pack(name="x", version="1.0", kind="attacks", items=_attack_items())


def test_build_rejects_bad_name() -> None:
    with pytest.raises(ValueError, match="invalid pack name"):
        build_pack(
            name="Bad Name", version="1.0.0", kind="personas", items=starter_items("personas")
        )


def test_build_rejects_invalid_items() -> None:
    with pytest.raises(ValueError, match="invalid item"):
        build_pack(
            name="x",
            version="1.0.0",
            kind="attacks",
            items=[
                {
                    "id": "bad",
                    "attack_class": "prompt_injection",
                    "description": "d",
                    "payload": "no canary here",
                    "canary": "MISSING",
                }
            ],
        )


def test_validate_detects_checksum_tampering() -> None:
    pack = build_pack(name="p", version="1.0.0", kind="scenarios", items=starter_items("scenarios"))
    pack.items.append({"op": "corrupt_field", "seed": 99})  # mutate after checksum
    problems = validate_pack(pack)
    assert any("checksum mismatch" in p for p in problems)
    assert any("n_items" in p for p in problems)


def test_scenario_kind_validates_op_names() -> None:
    pack = build_pack(name="s", version="2.1.0", kind="scenarios", items=starter_items("scenarios"))
    assert validate_pack(pack) == []


def test_all_three_starter_kinds_build_clean() -> None:
    for kind in ("attacks", "personas", "scenarios"):
        pack = build_pack(name=f"k-{kind}", version="1.0.0", kind=kind, items=starter_items(kind))
        assert validate_pack(pack) == [] and pack.manifest.n_items > 0


def test_roundtrip_file(tmp_path: Path) -> None:
    pack = build_pack(name="p", version="1.2.3", kind="personas", items=starter_items("personas"))
    path = write_pack(pack, tmp_path / "p.json")
    loaded = read_pack(path)
    assert loaded.manifest == pack.manifest and loaded.items == pack.items
