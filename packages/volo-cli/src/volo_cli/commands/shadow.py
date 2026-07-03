"""`volo shadow` — production shadow: bank traces, adopt incidents, catch drift (M13).

* ``volo shadow pull traces/`` — import sampled OTel traces (redaction always runs first).
* ``volo shadow adopt failure.json`` — turn a production failure into a permanent regression.
* ``volo shadow list`` — what's banked.
* ``volo shadow check --agent module:fn`` — replay the whole corpus against the current build,
  compare the reliability surface to the last snapshot, **exit 3 on drift**. First run
  establishes the baseline. Wire it into a nightly workflow and regressions page you, not
  your users.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

DEFAULT_CORPUS = Path(".volo") / "corpus"
DEFAULT_BASELINE = Path(".volo") / "shadow-baseline.json"
DRIFT_EXIT_CODE = 3

shadow_app = typer.Typer(
    name="shadow",
    help="Bank production traces; replay them nightly; alert on reliability drift.",
    no_args_is_help=True,
)

_CorpusOpt = Annotated[
    Path, typer.Option("--corpus", help="Corpus bank directory.", show_default=True)
]


@shadow_app.command("pull")
def shadow_pull(
    source: Annotated[Path, typer.Argument(help="An OTel trace file, or a directory of them.")],
    corpus: _CorpusOpt = DEFAULT_CORPUS,
    agent_name: Annotated[
        str | None, typer.Option("--agent-name", help="Agent name stored on imported traces.")
    ] = None,
    framework: Annotated[
        str, typer.Option("--framework", help="Framework tag for imported traces.")
    ] = "otel",
    tag: Annotated[str, typer.Option("--tag", help="Corpus source tag.")] = "shadow",
) -> None:
    """Import production OTel traces into the corpus (redacted, deduplicated)."""
    from volo_shadow import CorpusBank, pull

    if not source.exists():
        raise typer.BadParameter(f"Trace source not found: {source}")
    result = pull(source, CorpusBank(corpus), agent_name=agent_name, framework=framework, tag=tag)
    for entry in result.imported:
        typer.echo(f"shadow pull: banked {entry.run_id} ({entry.steps} steps, {entry.source})")
    typer.echo(f"shadow pull: {result.summary()} -> {corpus}")


@shadow_app.command("adopt")
def shadow_adopt(
    recording_path: Annotated[Path, typer.Argument(help="Path to a Recording JSON file.")],
    corpus: _CorpusOpt = DEFAULT_CORPUS,
    tag: Annotated[str, typer.Option("--tag", help="Corpus source tag.")] = "incident",
) -> None:
    """Adopt one recording (e.g. a production failure trace) into the corpus."""
    from volo_shadow import CorpusBank, adopt

    if not recording_path.exists():
        raise typer.BadParameter(f"Recording not found: {recording_path}")
    entry = adopt(recording_path, CorpusBank(corpus), tag=tag)
    if entry is None:
        typer.echo("shadow adopt: already banked (identical content)")
    else:
        typer.echo(f"shadow adopt: banked {entry.run_id} ({entry.steps} steps, {entry.source})")


@shadow_app.command("list")
def shadow_list(corpus: _CorpusOpt = DEFAULT_CORPUS) -> None:
    """Show every banked trace."""
    from volo_shadow import CorpusBank

    entries = CorpusBank(corpus).entries()
    if not entries:
        typer.echo(f"shadow list: corpus at {corpus} is empty")
        return
    for e in entries:
        name = e.agent_name or "-"
        typer.echo(f"shadow list: {e.run_id}  [{e.source}] agent={name} steps={e.steps}")
    typer.echo(f"shadow list: {len(entries)} banked trace(s)")


@shadow_app.command("check")
def shadow_check(
    agent: Annotated[str, typer.Option("--agent", help="Agent under test, as `module:callable`.")],
    corpus: _CorpusOpt = DEFAULT_CORPUS,
    baseline: Annotated[
        Path,
        typer.Option("--baseline", help="Snapshot file to compare against (created if missing)."),
    ] = DEFAULT_BASELINE,
    n_runs: Annotated[int, typer.Option("--n", help="Repetitions per scenario.")] = 2,
    threshold: Annotated[
        float, typer.Option("--threshold", help="Alert when a dimension drops more than this.")
    ] = 0.05,
    update_baseline: Annotated[
        bool,
        typer.Option("--update-baseline", help="Write the current snapshot over the baseline."),
    ] = False,
    report: Annotated[
        Path | None, typer.Option("--report", help="Also write the JSON drift report.")
    ] = None,
) -> None:
    """Replay the corpus against the current agent; exit 3 if the surface drifted."""
    from volo_runner import resolve_agent
    from volo_shadow import CorpusBank, compare, snapshot

    bank = CorpusBank(corpus)
    if not bank.entries():
        typer.echo(f"shadow check: corpus at {corpus} is empty — `volo shadow pull` first")
        raise typer.Exit(2)

    current = snapshot(bank, resolve_agent(agent), n_runs=n_runs)

    if not baseline.exists():
        baseline.parent.mkdir(parents=True, exist_ok=True)
        baseline.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        typer.echo(
            f"shadow check: baseline established over {len(current['entries'])} trace(s) "
            f"-> {baseline}"
        )
        return

    base = json.loads(baseline.read_text(encoding="utf-8"))
    drift = compare(base, current, threshold=threshold)

    for f in drift.findings:
        typer.echo(
            f"shadow check: DRIFT {f.run_id} {f.dimension}: "
            f"{f.baseline:.3f} -> {f.current:.3f} (delta {f.delta:+.3f})"
        )
    if drift.new_runs:
        typer.echo(f"shadow check: {len(drift.new_runs)} new trace(s) not in baseline")
    if report is not None:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(drift.to_dict(), indent=2) + "\n", encoding="utf-8")
        typer.echo(f"shadow check: report -> {report}")
    if update_baseline:
        baseline.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        typer.echo(f"shadow check: baseline updated -> {baseline}")

    if drift.drifted:
        typer.echo(f"shadow check: {len(drift.findings)} drift finding(s) -> ALERT")
        raise typer.Exit(DRIFT_EXIT_CODE)
    typer.echo(f"shadow check: no drift across {len(current['entries'])} trace(s) -> OK")
