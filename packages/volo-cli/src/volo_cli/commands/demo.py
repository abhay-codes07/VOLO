"""`volo demo` — seed the data dir with showcase recordings + reports.

Produces five artifacts the dashboard renders out-of-the-box:
1. A v1 calc_agent baseline recording.
2. A v2 calc_agent (with off-by-one bug) recording — same shape, wrong value.
3. A reliability report on v1 against the default scenario library.
4. A reliability report on v2 — should regress vs. v1.
5. A diff of v1 vs v2 — should pinpoint the multiply step as the divergence.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from volo_core import current_recorder
from volo_diff import compute_diff
from volo_runner import OrchestratorConfig, orchestrate
from volo_sdk import Recorder, RecorderConfig


def demo_command(
    data_dir: Annotated[
        Path,
        typer.Option("--data-dir", help="Where to write recordings + reports."),
    ] = Path(".volo"),
    n_runs: Annotated[
        int,
        typer.Option("--n", help="Repetitions per scenario for the reliability passes."),
    ] = 2,
) -> None:
    """Seed the data dir with showcase recordings + reports for the dashboard."""
    import os
    import sys

    cwd = os.getcwd()
    if cwd not in sys.path:
        sys.path.insert(0, cwd)
    from examples.calc_agent import run as calc_v1
    from examples.calc_agent_v2 import run as calc_v2

    rec_dir = data_dir / "recordings"
    rep_dir = data_dir / "reports"
    diff_dir = data_dir / "diffs"
    for d in (rec_dir, rep_dir, diff_dir):
        d.mkdir(parents=True, exist_ok=True)

    input_ = {"a": 2, "b": 3, "c": 4}

    # 1. Record v1 baseline.
    rec_v1 = Recorder(
        agent_name="examples.calc_agent:run",
        framework="raw",
        config=RecorderConfig(data_dir=data_dir, apply_redaction=False),
    )
    with current_recorder(rec_v1):
        rec_v1.set_final_output(calc_v1(input_))
    v1_path = rec_dir / "calc_v1.json"
    v1_path.write_text(rec_v1.recording.to_json() + "\n", encoding="utf-8")
    typer.echo(f"  baseline (v1)  -> {v1_path}")

    # 2. Record v2 (with the off-by-one bug).
    rec_v2 = Recorder(
        agent_name="examples.calc_agent_v2:run",
        framework="raw",
        config=RecorderConfig(data_dir=data_dir, apply_redaction=False),
    )
    with current_recorder(rec_v2):
        rec_v2.set_final_output(calc_v2(input_))
    v2_path = rec_dir / "calc_v2.json"
    v2_path.write_text(rec_v2.recording.to_json() + "\n", encoding="utf-8")
    typer.echo(f"  candidate (v2) -> {v2_path}")

    # 3. Run the reliability suite on v1.
    report_v1 = orchestrate(
        rec_v1.recording,
        "examples.calc_agent:run",
        config=OrchestratorConfig(n_runs=n_runs, agent_input=input_),
    )
    v1_report_path = rep_dir / "calc_v1.json"
    v1_report_path.write_text(report_v1.to_json() + "\n", encoding="utf-8")
    typer.echo(
        f"  report v1       -> {v1_report_path}  verdict={report_v1.verdict}",
    )

    # 4. Same on v2 — should regress.
    report_v2 = orchestrate(
        rec_v2.recording,
        "examples.calc_agent_v2:run",
        config=OrchestratorConfig(n_runs=n_runs, agent_input=input_),
    )
    v2_report_path = rep_dir / "calc_v2.json"
    v2_report_path.write_text(report_v2.to_json() + "\n", encoding="utf-8")
    typer.echo(
        f"  report v2       -> {v2_report_path}  verdict={report_v2.verdict}",
    )

    # 5. Diff v1 vs v2 — should pinpoint the multiply step.
    diff_result = compute_diff(rec_v1.recording, rec_v2.recording)
    diff_path = diff_dir / "v1_vs_v2.json"
    diff_path.write_text(diff_result.to_json() + "\n", encoding="utf-8")
    typer.echo(
        f"  diff v1 vs v2   -> {diff_path}  "
        f"first_diverging_step={diff_result.first_diverging_step}",
    )

    typer.echo("\ndemo data ready. open the dashboard to see it rendered.")
