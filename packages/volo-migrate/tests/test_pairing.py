"""Pairing: files pair directly, directories pair by stem, extras are reported."""

from __future__ import annotations

from pathlib import Path

from volo_core import Recording, ToolCallPayload
from volo_migrate import pair_corpora


def _write(path: Path, answer: str) -> None:
    rec = Recording()
    rec.add_step(ToolCallPayload(tool="t", request={}, response={"ok": True}))
    rec.final_output = {"answer": answer}
    path.write_text(rec.to_json(), encoding="utf-8")


def test_two_files_pair_directly(tmp_path: Path) -> None:
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    _write(a, "one")
    _write(b, "two")
    pairs, unpaired = pair_corpora(a, b)
    assert len(pairs) == 1 and unpaired == []
    assert pairs[0][1].final_output == {"answer": "one"}
    assert pairs[0][2].final_output == {"answer": "two"}


def test_directories_pair_by_stem(tmp_path: Path) -> None:
    base, cand = tmp_path / "a", tmp_path / "b"
    base.mkdir()
    cand.mkdir()
    for name in ("login", "checkout", "search"):
        _write(base / f"{name}.json", "a")
        _write(cand / f"{name}.json", "b")
    _write(base / "only_in_a.json", "a")
    _write(cand / "only_in_b.json", "b")

    pairs, unpaired = pair_corpora(base, cand)
    assert [k for k, _, _ in pairs] == ["checkout", "login", "search"]
    assert unpaired == ["only_in_a", "only_in_b"]


def test_index_json_ignored(tmp_path: Path) -> None:
    base, cand = tmp_path / "a", tmp_path / "b"
    base.mkdir()
    cand.mkdir()
    _write(base / "t.json", "a")
    _write(cand / "t.json", "b")
    (base / "index.json").write_text('{"entries": []}', encoding="utf-8")
    (cand / "index.json").write_text('{"entries": []}', encoding="utf-8")

    pairs, unpaired = pair_corpora(base, cand)
    assert [k for k, _, _ in pairs] == ["t"] and unpaired == []
