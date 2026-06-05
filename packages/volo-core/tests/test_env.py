"""Tests for optional ``.env`` loading (``volo_core.env.load_env``)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

import volo_core.env as env

_VAR = "VOLO_TEST_DOTENV_VAR"


def _reset(monkeypatch: pytest.MonkeyPatch, cwd: Path) -> None:
    monkeypatch.chdir(cwd)
    monkeypatch.setattr(env, "_loaded", False)


def test_load_env_reads_dotenv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / ".env").write_text(f"{_VAR}=from_dotenv\n", encoding="utf-8")
    monkeypatch.delenv(_VAR, raising=False)
    _reset(monkeypatch, tmp_path)
    try:
        env.load_env()
        assert os.environ.get(_VAR) == "from_dotenv"
    finally:
        os.environ.pop(_VAR, None)


def test_explicit_env_wins_over_dotenv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / ".env").write_text(f"{_VAR}=from_dotenv\n", encoding="utf-8")
    monkeypatch.setenv(_VAR, "from_shell")  # already-exported var must win (override=False)
    _reset(monkeypatch, tmp_path)
    env.load_env()
    assert os.environ.get(_VAR) == "from_shell"


def test_load_env_is_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _reset(monkeypatch, tmp_path)
    env.load_env()
    env.load_env()  # second call is a no-op, must not raise
    assert env._loaded is True
