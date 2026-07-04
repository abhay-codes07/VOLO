"""`volo migrate` — model-migration lab (M16).

Compare an agent's reliability + cost across two models. You already recorded your corpus under
the current model (baseline); re-record it once under the candidate, then::

    volo migrate baseline/ candidate/ --from claude-haiku-4-5 --to llama-3.3-70b-versatile

Pairs the corpora trace by trace, scores each pair (tool-path / output / faithfulness / cost),
and prints a migration recommendation. Exits 5 on ``block`` (a regression), 0 otherwise.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

BLOCK_EXIT_CODE = 5


def migrate_command(
    baseline: Annotated[Path, typer.Argument(help="Baseline recording/corpus (model A).")],
    candidate: Annotated[Path, typer.Argument(help="Candidate recording/corpus (model B).")],
    from_model: Annotated[
        str | None, typer.Option("--from", help="Baseline model label (else inferred).")
    ] = None,
    to_model: Annotated[
        str | None, typer.Option("--to", help="Candidate model label (else inferred).")
    ] = None,
    judge: Annotated[
        str, typer.Option("--judge", help="Faithfulness judge: heuristic | ollama | groq.")
    ] = "heuristic",
    out: Annotated[
        Path | None, typer.Option("--out", help="Write the migration report JSON here.")
    ] = None,
) -> None:
    """Score a model migration across a corpus and recommend go / review / block."""
    from volo_cli.commands._judge import resolve_judge
    from volo_migrate import pair_corpora, run_migration

    if not baseline.exists():
        raise typer.BadParameter(f"Baseline not found: {baseline}")
    if not candidate.exists():
        raise typer.BadParameter(f"Candidate not found: {candidate}")

    pairs, unpaired = pair_corpora(baseline, candidate)
    if not pairs:
        typer.echo("migrate: no paired recordings — check the two corpora share file stems")
        raise typer.Exit(2)

    report = run_migration(
        pairs,
        from_model=from_model,
        to_model=to_model,
        judge=resolve_judge(judge),
        unpaired=unpaired,
    )

    typer.echo(
        f"migrate: {report.from_model} -> {report.to_model} over {len(report.pairs)} trace(s)"
    )
    for v in report.pairs:
        marker = {"improved": "up", "regressed": "!!", "changed": "~~", "unchanged": "ok"}[
            v.outcome
        ]
        typer.echo(
            f"migrate: {marker} {v.key:24} {v.outcome:10} "
            f"faith {v.faithfulness_a:.2f}->{v.faithfulness_b:.2f}"
            f"{'  output-changed' if v.output_changed else ''}"
            f"{'  path-changed' if v.tool_path_changed else ''}"
        )
    c = report.counts
    typer.echo(
        f"migrate: {c['improved']} improved, {c['regressed']} regressed, "
        f"{c['changed']} changed, {c['unchanged']} unchanged"
    )
    delta = report.cost_delta_usd
    sign = "+" if delta >= 0 else ""
    typer.echo(
        f"migrate: cost ${report.cost_a_usd:.4f} -> ${report.cost_b_usd:.4f} "
        f"({sign}{delta:.4f} projected)"
    )
    if report.unpaired:
        typer.echo(
            f"migrate: {len(report.unpaired)} unpaired trace(s): {', '.join(report.unpaired)}"
        )

    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report.to_json() + "\n", encoding="utf-8")
        typer.echo(f"migrate: report -> {out}")

    typer.echo(f"migrate: recommendation -> {report.recommendation.upper()}")
    if report.recommendation == "block":
        raise typer.Exit(BLOCK_EXIT_CODE)
