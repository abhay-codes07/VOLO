"""`volo scenarios` — list the default scenario operator library."""

from __future__ import annotations

import typer

from volo_scenarios import default_library


def scenarios_command(
    seed: int = typer.Option(0, "--seed", help="Base seed for the library."),
) -> None:
    """List the default scenario operators and their failure classes (ADR-0005)."""
    typer.echo(f"{'op':<24} {'failure class':<22} seed")
    typer.echo("-" * 56)
    for op in default_library(seed=seed):
        typer.echo(f"{op.name:<24} {op.failure_class:<22} {op.seed}")
