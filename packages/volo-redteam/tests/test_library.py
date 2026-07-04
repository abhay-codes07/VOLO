"""The built-in corpus: size, class coverage, uniqueness, and pack round-trip."""

from __future__ import annotations

from pathlib import Path

from volo_redteam import ATTACK_CLASSES, default_attack_library, dump_pack, load_pack


def test_corpus_is_large_and_covers_all_six_classes() -> None:
    corpus = default_attack_library()
    assert len(corpus) >= 50
    classes = {a.attack_class for a in corpus}
    assert classes == set(ATTACK_CLASSES)
    # every class carries real weight, not a token single entry
    for cls in ATTACK_CLASSES:
        assert sum(1 for a in corpus if a.attack_class == cls) >= 6


def test_ids_and_canaries_are_unique() -> None:
    corpus = default_attack_library()
    assert len({a.id for a in corpus}) == len(corpus)
    assert len({a.canary for a in corpus}) == len(corpus)


def test_every_payload_contains_its_canary() -> None:
    for a in default_attack_library():
        assert a.canary in a.payload  # enforced by Attack.__post_init__, asserted here too


def test_pack_roundtrip(tmp_path: Path) -> None:
    corpus = default_attack_library()
    path = dump_pack(corpus, tmp_path / "pack.json", name="test")
    loaded = load_pack(path)
    assert loaded == corpus


def test_load_pack_accepts_bare_list(tmp_path: Path) -> None:
    import json

    corpus = default_attack_library()[:3]
    p = tmp_path / "bare.json"
    p.write_text(json.dumps([a.to_dict() for a in corpus]), encoding="utf-8")
    assert load_pack(p) == corpus
