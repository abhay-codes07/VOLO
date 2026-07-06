"""Leaderboard harness (M24): ranks agents by reliability; renders JSON/MD/HTML."""

from __future__ import annotations

from benchmarks.leaderboard import (
    ENTRIES,
    build_leaderboard,
    render_html,
    render_markdown,
    score_entry,
)


def test_build_leaderboard_ranks_and_scores() -> None:
    rows = build_leaderboard()
    assert len(rows) == len(ENTRIES)
    # ranks are contiguous 1..N and scores are a valid 0-100, sorted descending
    assert [r["rank"] for r in rows] == list(range(1, len(rows) + 1))
    scores = [r["volo_score"] for r in rows]
    assert scores == sorted(scores, reverse=True)
    assert all(0 <= s <= 100 for s in scores)


def test_flaky_agent_ranks_below_stable_agents() -> None:
    rows = build_leaderboard()
    by_name = {r["name"]: r for r in rows}
    flaky = next(r for r in rows if "flaky" in r["name"])
    stable = [r for r in rows if "flaky" not in r["name"]]
    # the nondeterministic agent scores below every stable one and lands last
    assert flaky["rank"] == len(rows)
    assert all(flaky["volo_score"] < r["volo_score"] for r in stable)
    # flaky's determinism/consistency actually collapsed
    assert flaky["dimensions"]["decision_determinism"] < 1.0
    assert by_name["research_agent"]["volo_score"] >= 80


def test_score_entry_is_deterministic_for_stable_agents() -> None:
    entry = next(e for e in ENTRIES if e["name"] == "echo_agent")
    a = score_entry(entry)
    b = score_entry(entry)
    assert a["volo_score"] == b["volo_score"]
    assert a["dimensions"] == b["dimensions"]


def test_renderers_include_every_agent() -> None:
    rows = build_leaderboard()
    md = render_markdown(rows)
    html = render_html(rows)
    assert md.startswith("# Volo Reliability Leaderboard")
    assert html.lstrip().startswith("<!doctype html>")
    for r in rows:
        assert r["name"] in md
        assert r["name"] in html


def test_row_carries_failure_class_breakdown() -> None:
    rows = build_leaderboard()
    calc = next(r for r in rows if r["name"] == "calc_agent")
    assert calc["by_failure_class"]  # non-empty per-class scores
    assert "security" in calc["by_failure_class"]  # prompt_injection class
    assert 0.0 <= calc["baseline_faithfulness"] <= 1.0
