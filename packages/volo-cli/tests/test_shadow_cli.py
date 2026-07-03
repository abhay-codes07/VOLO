"""`volo shadow pull|adopt|list|check` — the nightly drift sentinel, end to end."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from volo_cli.main import app

runner = CliRunner()


def _write_trace(path: Path) -> Path:
    spans = [
        {
            "name": "tool.search",
            "spanId": "s1",
            "startTimeUnixNano": 1,
            "attributes": {
                "tool.name": "search",
                "tool.input": json.dumps({"q": "volo"}),
                "tool.output": json.dumps({"hits": 1}),
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
                "gen_ai.response": json.dumps({"text": "one hit"}),
            },
        },
    ]
    path.write_text("\n".join(json.dumps(s) for s in spans) + "\n", encoding="utf-8")
    return path


def _write_agents(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "shadow_agent_stable.py").write_text(
        "def run():\n    return {'answer': 'one hit'}\n", encoding="utf-8"
    )
    (tmp_path / "shadow_agent_regressed.py").write_text(
        "import itertools\n_c = itertools.count()\n"
        "def run():\n    return {'answer': f'draft-{next(_c)}'}\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))


def test_pull_then_list(tmp_path: Path) -> None:
    trace = _write_trace(tmp_path / "trace.jsonl")
    corpus = tmp_path / "corpus"

    res = runner.invoke(app, ["shadow", "pull", str(trace), "--corpus", str(corpus)])
    assert res.exit_code == 0, res.output
    assert "1 banked" in res.output

    res = runner.invoke(app, ["shadow", "list", "--corpus", str(corpus)])
    assert res.exit_code == 0
    assert "1 banked trace(s)" in res.output


def test_check_baseline_then_ok_then_alert(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The full sentinel loop: establish baseline → quiet night → regression pages you."""
    _write_agents(tmp_path, monkeypatch)
    corpus = tmp_path / "corpus"
    baseline = tmp_path / "baseline.json"
    runner.invoke(
        app, ["shadow", "pull", str(_write_trace(tmp_path / "t.jsonl")), "--corpus", str(corpus)]
    )

    def check(agent: str, *extra: str) -> Any:
        return runner.invoke(
            app,
            [
                "shadow",
                "check",
                "--agent",
                agent,
                "--corpus",
                str(corpus),
                "--baseline",
                str(baseline),
                *extra,
            ],
        )

    first = check("shadow_agent_stable:run")
    assert first.exit_code == 0, first.output
    assert "baseline established" in first.output

    quiet = check("shadow_agent_stable:run")
    assert quiet.exit_code == 0, quiet.output
    assert "no drift" in quiet.output

    report = tmp_path / "drift.json"
    alert = check("shadow_agent_regressed:run", "--report", str(report))
    assert alert.exit_code == 3, alert.output
    assert "ALERT" in alert.output
    blob = json.loads(report.read_text(encoding="utf-8"))
    assert blob["drifted"] is True and blob["findings"]


def test_check_empty_corpus_exits_2(tmp_path: Path) -> None:
    res = runner.invoke(
        app,
        ["shadow", "check", "--agent", "x:y", "--corpus", str(tmp_path / "nope")],
    )
    assert res.exit_code == 2
    assert "empty" in res.output


def test_adopt_recording(tmp_path: Path) -> None:
    from volo_core import Recording, ToolCallPayload

    rec = Recording()
    rec.add_step(ToolCallPayload(tool="t", request={}, response={"ok": True}))
    path = tmp_path / "incident.json"
    path.write_text(rec.to_json(), encoding="utf-8")

    res = runner.invoke(app, ["shadow", "adopt", str(path), "--corpus", str(tmp_path / "corpus")])
    assert res.exit_code == 0, res.output
    assert "banked" in res.output
