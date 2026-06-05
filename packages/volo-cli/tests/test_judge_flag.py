"""Tests for the `--judge` resolution helper (bible §11, ADR-0011)."""

from __future__ import annotations

import pytest
import typer

from volo_cli.commands._judge import JUDGE_CHOICES, resolve_judge


def test_heuristic_resolves_to_none() -> None:
    # None means "use the zero-cost heuristic default" downstream.
    assert resolve_judge("heuristic") is None


def test_ollama_resolves_to_ollama_judge() -> None:
    from volo_reliability import OllamaJudge

    assert isinstance(resolve_judge("ollama"), OllamaJudge)


def test_groq_resolves_to_openai_compat_judge() -> None:
    from volo_reliability import OpenAICompatJudge

    assert isinstance(resolve_judge("groq"), OpenAICompatJudge)


def test_case_insensitive() -> None:
    from volo_reliability import OllamaJudge

    assert isinstance(resolve_judge("OLLAMA"), OllamaJudge)


def test_unknown_judge_raises_bad_parameter() -> None:
    with pytest.raises(typer.BadParameter):
        resolve_judge("gpt5")


def test_choices_are_exposed() -> None:
    assert JUDGE_CHOICES == ("heuristic", "ollama", "groq")
