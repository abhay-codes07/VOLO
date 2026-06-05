"""`volo diff` — "git bisect for agents" (ADR-0007)."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from volo_core import Recording
from volo_diff import compute_diff, format_diff


def diff_command(
    run_a: Annotated[Path, typer.Argument(help="Baseline Recording.")],
    run_b: Annotated[Path, typer.Argument(help="Candidate Recording.")],
    out: Annotated[
        Path | None,
        typer.Option("--out", help="Where to write the Diff JSON."),
    ] = None,
) -> None:
    for p in (run_a, run_b):
        if not p.exists():
            raise typer.BadParameter(f"Recording not found: {p}")

    a = Recording.from_json(run_a.read_text(encoding="utf-8"))
    b = Recording.from_json(run_b.read_text(encoding="utf-8"))
    d = compute_diff(a, b)

    typer.echo(format_diff(d))

    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(d.to_json() + "\n", encoding="utf-8")
        typer.echo(f"\ndiff -> {out}")

    raise typer.Exit(0 if d.first_diverging_step is None else 1)
