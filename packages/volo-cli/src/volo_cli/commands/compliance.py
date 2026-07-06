"""`volo compliance` — generate/verify signed compliance evidence packs (M29).

* ``volo compliance build`` — bundle a reliability report, red-team safety annex, and/or drift
  report into a signed evidence pack mapped to control frameworks (EU AI Act / ISO 42001 / SOC2).
* ``volo compliance verify`` — check an evidence pack's checksum (and signature, with a keyring).

The evidence is a mapping aid, not legal advice — its value is being deterministic, checksummed,
and replayable. ``build --require-satisfied`` exits 8 if any control is unmet (a CI gate).
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

UNMET_EXIT_CODE = 8
INVALID_EXIT_CODE = 1

compliance_app = typer.Typer(
    name="compliance",
    help="Signed, deterministic compliance evidence packs (EU AI Act / ISO 42001 / SOC2).",
    no_args_is_help=True,
)


@compliance_app.command("build")
def compliance_build(
    agent: Annotated[str, typer.Option("--agent", help="Agent name for the evidence pack.")],
    reliability: Annotated[
        Path | None, typer.Option("--reliability", help="ReliabilityReport JSON (from volo run).")
    ] = None,
    safety: Annotated[
        Path | None, typer.Option("--safety", help="SafetyAnnex JSON (from volo redteam --out).")
    ] = None,
    drift: Annotated[
        Path | None, typer.Option("--drift", help="Drift report JSON (from volo shadow check).")
    ] = None,
    framework: Annotated[
        str, typer.Option("--framework", help="eu_ai_act | iso_42001 | soc2 | all.")
    ] = "all",
    out: Annotated[Path, typer.Option("--out", help="Evidence pack JSON output.")] = Path(
        "evidence.json"
    ),
    md: Annotated[
        Path | None, typer.Option("--md", help="Also write a human-readable Markdown report.")
    ] = None,
    sign_publisher: Annotated[
        str | None, typer.Option("--sign", help="Sign the pack as this publisher.")
    ] = None,
    secret_env: Annotated[
        str, typer.Option("--secret-env", help="Env var holding the signing secret.")
    ] = "VOLO_PACK_SECRET",
    require_satisfied: Annotated[
        bool, typer.Option("--require-satisfied", help="Exit 8 if any control is unmet.")
    ] = False,
) -> None:
    """Build a signed evidence pack from Volo artifacts, mapped to control frameworks."""
    import json
    import os
    from datetime import UTC, datetime

    from volo_compliance import FRAMEWORKS, build_evidence_pack, render_markdown, sign_evidence
    from volo_redteam import SafetyAnnex
    from volo_reliability import ReliabilityReport

    frameworks = list(FRAMEWORKS) if framework == "all" else [framework]
    for fw in frameworks:
        if fw not in FRAMEWORKS:
            raise typer.BadParameter(f"--framework must be one of {list(FRAMEWORKS)} or 'all'")

    rel = (
        ReliabilityReport.model_validate_json(reliability.read_text("utf-8"))
        if reliability
        else None
    )
    saf = SafetyAnnex.model_validate_json(safety.read_text("utf-8")) if safety else None
    dft = json.loads(drift.read_text("utf-8")) if drift else None
    if rel is None and saf is None and dft is None:
        raise typer.BadParameter("provide at least one of --reliability / --safety / --drift")

    pack = build_evidence_pack(
        agent_name=agent,
        frameworks=frameworks,
        reliability=rel,
        safety=saf,
        drift=dft,
        generated_at=datetime.now(UTC).isoformat(timespec="seconds"),
    )
    if sign_publisher is not None:
        secret = os.environ.get(secret_env)
        if not secret:
            raise typer.BadParameter(f"no signing secret in ${secret_env}")
        pack = sign_evidence(pack, publisher=sign_publisher, secret=secret)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(pack.to_json() + "\n", encoding="utf-8")
    if md is not None:
        md.parent.mkdir(parents=True, exist_ok=True)
        md.write_text(render_markdown(pack), encoding="utf-8")

    counts = pack.counts()
    for c in pack.controls:
        marker = {"satisfied": "ok", "partial": "~~", "unmet": "!!"}[c.state]
        typer.echo(f"compliance: {marker} {c.framework}/{c.control_id} {c.state} - {c.title}")
    typer.echo(
        f"compliance: {counts['satisfied']} satisfied, {counts['partial']} partial, "
        f"{counts['unmet']} unmet -> {out}"
        + (f" (signed by {sign_publisher!r})" if sign_publisher else "")
    )
    if require_satisfied and counts["unmet"]:
        raise typer.Exit(UNMET_EXIT_CODE)


@compliance_app.command("verify")
def compliance_verify(
    evidence_path: Annotated[Path, typer.Argument(help="Evidence pack JSON to verify.")],
    keyring: Annotated[
        Path | None, typer.Option("--keyring", help="Keyring JSON to verify the signature.")
    ] = None,
) -> None:
    """Verify an evidence pack's checksum (and signature, if a keyring is given)."""
    import json

    from volo_compliance import EvidencePack, verify_evidence

    if not evidence_path.exists():
        raise typer.BadParameter(f"Evidence pack not found: {evidence_path}")
    pack = EvidencePack.model_validate_json(evidence_path.read_text("utf-8"))

    if pack.checksum != pack.content_checksum():
        typer.echo(f"compliance verify: {pack.agent_name} -> CHECKSUM MISMATCH (tampered)")
        raise typer.Exit(INVALID_EXIT_CODE)
    typer.echo(f"compliance verify: {pack.agent_name} checksum OK")

    if keyring is not None:
        keys = json.loads(keyring.read_text("utf-8"))
        if pack.signature is None:
            typer.echo("compliance verify: pack is UNSIGNED")
            raise typer.Exit(INVALID_EXIT_CODE)
        if verify_evidence(pack, keys):
            typer.echo(f"compliance verify: signature by {pack.signature.publisher!r} -> VALID")
        else:
            typer.echo(f"compliance verify: signature by {pack.signature.publisher!r} -> INVALID")
            raise typer.Exit(INVALID_EXIT_CODE)
