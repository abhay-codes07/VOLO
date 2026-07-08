"""`volo certify` — the Volo Certified program (M33).

* ``volo certify run <recording> --agent m:fn`` — run reliability + red-team, apply the criteria,
  and emit a signed certificate (exit 10 if not certified).
* ``volo certify verify <cert.json> --keyring k.json`` — check the checksum + signature.
* ``volo certify badge <cert.json>`` — render the SVG badge.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

NOT_CERTIFIED_EXIT_CODE = 10
INVALID_EXIT_CODE = 1

certify_app = typer.Typer(
    name="certify",
    help="Volo Certified — reliability + safety → a signed agent certificate + badge.",
    no_args_is_help=True,
)


@certify_app.command("run")
def certify_run(
    recording_path: Annotated[Path, typer.Argument(help="Baseline Recording JSON.")],
    agent: Annotated[str, typer.Option("--agent", help="Agent under test, as `module:callable`.")],
    input_: Annotated[str, typer.Option("--input", "-i", help="JSON input for the agent.")] = "{}",
    min_score: Annotated[int, typer.Option("--min-score", help="Minimum Volo Score.")] = 60,
    require_ship: Annotated[
        bool, typer.Option("--require-ship", help="Also require a ship verdict under adversity.")
    ] = False,
    out: Annotated[Path | None, typer.Option("--out", help="Write the certificate JSON.")] = None,
    badge: Annotated[Path | None, typer.Option("--badge", help="Write the SVG badge.")] = None,
    sign_publisher: Annotated[
        str | None, typer.Option("--sign", help="Sign the certificate as this publisher.")
    ] = None,
    secret_env: Annotated[
        str, typer.Option("--secret-env", help="Env var holding the signing secret.")
    ] = "VOLO_PACK_SECRET",
) -> None:
    """Certify an agent and print PASS/FAIL; exit 10 if not certified."""
    import json
    import os
    from datetime import UTC, datetime

    from volo_certify import CertCriteria, certify, render_badge_svg, sign_certificate
    from volo_core import Recording
    from volo_runner import resolve_agent

    if not recording_path.exists():
        raise typer.BadParameter(f"Recording not found: {recording_path}")
    baseline = Recording.from_json(recording_path.read_text(encoding="utf-8"))
    try:
        agent_input = json.loads(input_)
    except json.JSONDecodeError as exc:
        raise typer.BadParameter(f"--input must be valid JSON: {exc}") from exc

    cert = certify(
        baseline,
        resolve_agent(agent),
        agent_name=agent,
        agent_input=agent_input if agent_input != {} else None,
        criteria=CertCriteria(min_volo_score=min_score, require_ship=require_ship),
        issued_at=datetime.now(UTC).isoformat(timespec="seconds"),
    )
    if sign_publisher is not None:
        secret = os.environ.get(secret_env)
        if not secret:
            raise typer.BadParameter(f"no signing secret in ${secret_env}")
        cert = sign_certificate(cert, publisher=sign_publisher, secret=secret)

    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(cert.to_json() + "\n", encoding="utf-8")
    if badge is not None:
        badge.parent.mkdir(parents=True, exist_ok=True)
        badge.write_text(render_badge_svg(cert), encoding="utf-8")

    typer.echo(
        f"certify: {cert.agent_name} - score {cert.volo_score}, "
        f"reliability={cert.reliability_verdict}, safety={cert.safety_verdict}"
    )
    for r in cert.reasons:
        typer.echo(f"certify: !! {r}")
    verdict = "CERTIFIED" if cert.passed else "NOT CERTIFIED"
    signed = f" (signed by {sign_publisher!r})" if sign_publisher else ""
    typer.echo(f"certify: -> {verdict}{signed}")
    if not cert.passed:
        raise typer.Exit(NOT_CERTIFIED_EXIT_CODE)


@certify_app.command("verify")
def certify_verify(
    cert_path: Annotated[Path, typer.Argument(help="Certificate JSON.")],
    keyring: Annotated[
        Path | None, typer.Option("--keyring", help="Keyring JSON to verify the signature.")
    ] = None,
) -> None:
    """Verify a certificate's checksum (and signature, with a keyring)."""
    import json

    from volo_certify import Certificate, verify_certificate

    if not cert_path.exists():
        raise typer.BadParameter(f"Certificate not found: {cert_path}")
    cert = Certificate.model_validate_json(cert_path.read_text(encoding="utf-8"))
    if cert.checksum != cert.content_checksum():
        typer.echo(f"certify verify: {cert.agent_name} -> CHECKSUM MISMATCH (tampered)")
        raise typer.Exit(INVALID_EXIT_CODE)
    typer.echo(f"certify verify: {cert.agent_name} checksum OK (passed={cert.passed})")
    if keyring is not None:
        if cert.signature is None:
            typer.echo("certify verify: certificate is UNSIGNED")
            raise typer.Exit(INVALID_EXIT_CODE)
        if verify_certificate(cert, json.loads(keyring.read_text(encoding="utf-8"))):
            typer.echo(f"certify verify: signature by {cert.signature.publisher!r} -> VALID")
        else:
            typer.echo(f"certify verify: signature by {cert.signature.publisher!r} -> INVALID")
            raise typer.Exit(INVALID_EXIT_CODE)


@certify_app.command("badge")
def certify_badge(
    cert_path: Annotated[Path, typer.Argument(help="Certificate JSON.")],
    out: Annotated[Path, typer.Argument(help="Where to write the SVG badge.")],
) -> None:
    """Render the Volo Certified SVG badge for a certificate."""
    from volo_certify import Certificate, render_badge_svg

    if not cert_path.exists():
        raise typer.BadParameter(f"Certificate not found: {cert_path}")
    cert = Certificate.model_validate_json(cert_path.read_text(encoding="utf-8"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_badge_svg(cert), encoding="utf-8")
    typer.echo(f"certify badge: {'PASS' if cert.passed else 'FAIL'} badge -> {out}")
