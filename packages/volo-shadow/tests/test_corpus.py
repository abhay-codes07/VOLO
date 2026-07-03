"""CorpusBank: banked once, indexed, deduplicated by content."""

from __future__ import annotations

from pathlib import Path

from volo_core import Recording, ToolCallPayload
from volo_shadow import CorpusBank, content_digest


def _recording(answer: str = "one hit") -> Recording:
    rec = Recording()
    rec.add_step(ToolCallPayload(tool="search", request={"q": "x"}, response={"hits": 1}))
    rec.final_output = {"answer": answer}
    return rec


def test_add_entries_load_roundtrip(tmp_path: Path) -> None:
    bank = CorpusBank(tmp_path / "corpus")
    entry = bank.add(_recording(), source="shadow")
    assert entry is not None and entry.steps == 1 and entry.source == "shadow"

    (loaded_entry, loaded) = bank.load_all()[0]
    assert loaded_entry.run_id == entry.run_id
    assert loaded.final_output == {"answer": "one hit"}


def test_same_content_different_run_id_is_deduplicated(tmp_path: Path) -> None:
    bank = CorpusBank(tmp_path / "corpus")
    a, b = _recording(), _recording()
    assert a.run_id != b.run_id
    assert content_digest(a) == content_digest(b)

    assert bank.add(a) is not None
    assert bank.add(b) is None
    assert len(bank.entries()) == 1


def test_different_content_is_banked_separately(tmp_path: Path) -> None:
    bank = CorpusBank(tmp_path / "corpus")
    assert bank.add(_recording("one hit")) is not None
    assert bank.add(_recording("two hits")) is not None
    assert len(bank.entries()) == 2


def test_index_persists_across_bank_instances(tmp_path: Path) -> None:
    root = tmp_path / "corpus"
    CorpusBank(root).add(_recording())
    fresh = CorpusBank(root)
    assert len(fresh.entries()) == 1
    assert fresh.add(_recording()) is None  # dedupe works from the persisted index
