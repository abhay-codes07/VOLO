"""Ingest: OTel traces come in, redacted deduplicated corpus entries come out."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from volo_core import Recording
from volo_shadow import CorpusBank, adopt, pull


def _spans(answer: str) -> list[dict[str, Any]]:
    return [
        {
            "name": "tool.search",
            "spanId": "s1",
            "startTimeUnixNano": 1,
            "attributes": {
                "tool.name": "search",
                "tool.input": json.dumps({"q": "volo"}),
                "tool.output": json.dumps({"hits": 1, "owner": "alice@example.com"}),
            },
        },
        {
            "name": "gen_ai.chat",
            "spanId": "s2",
            "startTimeUnixNano": 2,
            "attributes": {
                "gen_ai.system": "ollama",
                "gen_ai.request.model": "llama3.2:3b",
                "gen_ai.request": json.dumps({"prompt": "summarize"}),
                "gen_ai.response": json.dumps({"text": answer}),
            },
        },
    ]


def _write_jsonl(path: Path, spans: list[dict[str, Any]]) -> Path:
    path.write_text("\n".join(json.dumps(s) for s in spans) + "\n", encoding="utf-8")
    return path


def test_pull_banks_redacted_traces(tmp_path: Path) -> None:
    trace = _write_jsonl(tmp_path / "trace.jsonl", _spans("one hit"))
    bank = CorpusBank(tmp_path / "corpus")

    result = pull(trace, bank, agent_name="prod-agent")
    assert result.summary().startswith("1 banked")

    entry, recording = bank.load_all()[0]
    assert entry.agent_name == "prod-agent" and entry.framework == "otel"
    assert recording.redaction_applied is True
    assert len(recording.steps) == 2
    banked_text = (bank.root / entry.file).read_text(encoding="utf-8")
    assert "alice@example.com" not in banked_text  # PII never touches disk


def test_pull_directory_dedupes_and_counts_empty(tmp_path: Path) -> None:
    traces = tmp_path / "traces"
    traces.mkdir()
    _write_jsonl(traces / "a.jsonl", _spans("one hit"))
    _write_jsonl(traces / "b.jsonl", _spans("one hit"))  # identical content → duplicate
    (traces / "c.jsonl").write_text("", encoding="utf-8")  # empty → skipped

    result = pull(traces, CorpusBank(tmp_path / "corpus"))
    assert len(result.imported) == 1
    assert result.duplicates == 1
    assert result.empty == 1


def test_adopt_redacts_unredacted_recordings(tmp_path: Path) -> None:
    from volo_core import ToolCallPayload

    rec = Recording()
    rec.add_step(
        ToolCallPayload(tool="fetch", request={"url": "x"}, response={"who": "bob@example.com"})
    )
    path = tmp_path / "incident.json"
    path.write_text(rec.to_json(), encoding="utf-8")

    bank = CorpusBank(tmp_path / "corpus")
    entry = adopt(path, bank)
    assert entry is not None and entry.source == "incident"
    _, banked = bank.load_all()[0]
    assert banked.redaction_applied is True
    assert "bob@example.com" not in banked.to_json()

    assert adopt(path, bank) is None  # adopting the same incident twice is a no-op
