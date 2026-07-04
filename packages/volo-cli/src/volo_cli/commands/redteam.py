"""`volo redteam` — run the adversarial attack corpus against an agent, in the sim (M15).

Poisons a recording's tool responses with each attack and replays the agent offline; if an
attack's canary surfaces in the output, the agent obeyed injected content and is flagged
compromised. Exits 4 when any attack lands (a CI safety gate), 0 when the agent is clean.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

VULNERABLE_EXIT_CODE = 4

redteam_app = typer.Typer(
    name="redteam",
    help="Adversarial attack corpus + safety annex (prompt injection, exfil, jailbreak, ...).",
    no_args_is_help=True,
)


@redteam_app.command("run")
def redteam_run(
    recording_path: Annotated[Path, typer.Argument(help="Baseline Recording JSON to attack.")],
    agent: Annotated[str, typer.Option("--agent", help="Agent under test, as `module:callable`.")],
    input_: Annotated[
        str, typer.Option("--input", "-i", help="JSON input passed to the agent.")
    ] = "{}",
    pack: Annotated[
        Path | None,
        typer.Option("--pack", help="Attack pack JSON (default: the built-in 54-attack corpus)."),
    ] = None,
    annex_out: Annotated[
        Path | None, typer.Option("--out", help="Write the SafetyAnnex JSON here.")
    ] = None,
) -> None:
    """Attack the agent and print the safety annex; exit 4 if any attack lands."""
    import json

    from volo_core import Recording
    from volo_redteam import load_pack, run_redteam
    from volo_runner import resolve_agent

    if not recording_path.exists():
        raise typer.BadParameter(f"Recording not found: {recording_path}")
    baseline = Recording.from_json(recording_path.read_text(encoding="utf-8"))
    try:
        agent_input = json.loads(input_)
    except json.JSONDecodeError as exc:
        raise typer.BadParameter(f"--input must be valid JSON: {exc}") from exc

    attacks = load_pack(pack) if pack is not None else None
    annex = run_redteam(
        baseline,
        resolve_agent(agent),
        attacks=attacks,
        agent_input=agent_input if agent_input != {} else None,
        agent_name=agent,
    )

    for cls, counts in sorted(annex.by_class.items()):
        marker = "!!" if counts["compromised"] else "ok"
        typer.echo(
            f"redteam: {marker} {cls:18} {counts['compromised']}/{counts['run']} compromised"
        )
    for f in annex.findings:
        if f.compromised:
            typer.echo(f"redteam: COMPROMISED {f.attack_id} - {f.description}")

    if annex_out is not None:
        annex_out.parent.mkdir(parents=True, exist_ok=True)
        annex_out.write_text(annex.to_json() + "\n", encoding="utf-8")
        typer.echo(f"redteam: annex -> {annex_out}")

    typer.echo(
        f"redteam: {annex.compromised}/{annex.attacks_run} attacks landed -> "
        f"{annex.verdict.upper()}"
    )
    if annex.verdict == "vulnerable":
        raise typer.Exit(VULNERABLE_EXIT_CODE)


@redteam_app.command("list")
def redteam_list(
    pack: Annotated[
        Path | None, typer.Option("--pack", help="Attack pack to list (default: built-in corpus).")
    ] = None,
) -> None:
    """List the attack corpus by class."""
    from volo_redteam import default_attack_library, load_pack

    attacks = load_pack(pack) if pack is not None else default_attack_library()
    by_class: dict[str, int] = {}
    for a in attacks:
        by_class[a.attack_class] = by_class.get(a.attack_class, 0) + 1
    for a in attacks:
        typer.echo(f"redteam: {a.attack_class:18} {a.id:34} {a.description}")
    total = len(attacks)
    classes = ", ".join(f"{k}={v}" for k, v in sorted(by_class.items()))
    typer.echo(f"redteam: {total} attack(s) across {len(by_class)} class(es) — {classes}")


@redteam_app.command("export")
def redteam_export(
    out: Annotated[Path, typer.Argument(help="Where to write the built-in corpus as a JSON pack.")],
) -> None:
    """Export the built-in corpus as an attack pack (a starting point for custom packs)."""
    from volo_redteam import default_attack_library, dump_pack

    path = dump_pack(default_attack_library(), out, name="volo-builtin")
    typer.echo(f"redteam: exported {len(default_attack_library())} attacks -> {path}")
