"""The CLI must not crash on non-ASCII output under a legacy codepage (Windows cp1252)."""

from __future__ import annotations

from typer.testing import CliRunner

from volo_cli.main import _force_utf8_io, app

runner = CliRunner()


def test_force_utf8_io_is_safe_and_idempotent() -> None:
    _force_utf8_io()
    _force_utf8_io()  # calling twice must not raise


def test_top_level_help_renders() -> None:
    res = runner.invoke(app, ["--help"])
    assert res.exit_code == 0
    assert "certify" in res.output


def test_command_help_strings_are_cp1252_safe() -> None:
    # every registered command's help text must survive a legacy codepage (the --help crash was a
    # stray non-ASCII char in a help string)
    for group in app.registered_groups:
        help_text = getattr(group.typer_instance.info, "help", "") or ""
        help_text.encode("cp1252")  # raises UnicodeEncodeError if a stray char sneaks back in
