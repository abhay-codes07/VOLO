"""`volo pack` — build, validate, and install content packs (M20).

* ``volo pack init <kind> out.json`` — a starter pack seeded from the built-in library.
* ``volo pack validate <pack.json>`` — check manifest, checksum, and item schema (exit 1 on fail).
* ``volo pack install <pack.json>`` — validate + copy into the local pack store.
* ``volo pack list`` — what's installed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

DEFAULT_PACK_DIR = Path(".volo") / "packs"
INVALID_EXIT_CODE = 1

pack_app = typer.Typer(
    name="pack",
    help="Versioned, checksummed packs of attacks / personas / scenarios.",
    no_args_is_help=True,
)

_DirOpt = Annotated[Path, typer.Option("--dir", help="Local pack store directory.")]


@pack_app.command("init")
def pack_init(
    kind: Annotated[str, typer.Argument(help="Pack kind: attacks | personas | scenarios.")],
    out: Annotated[Path, typer.Argument(help="Where to write the starter pack JSON.")],
    name: Annotated[str, typer.Option("--name", help="Pack name.")] = "",
    version: Annotated[str, typer.Option("--version", help="Semver.")] = "0.1.0",
    author: Annotated[str, typer.Option("--author", help="Author.")] = "",
) -> None:
    """Create a starter pack seeded from Volo's built-in library for the kind."""
    from volo_packs import PACK_KINDS, build_pack, starter_items, write_pack

    if kind not in PACK_KINDS:
        raise typer.BadParameter(f"kind must be one of {list(PACK_KINDS)}, got {kind!r}")
    pack = build_pack(
        name=name or f"my-{kind}",
        version=version,
        kind=kind,
        items=starter_items(kind),
        description=f"Starter {kind} pack (edit me).",
        author=author,
    )
    path = write_pack(pack, out)
    typer.echo(f"pack init: {pack.ref} ({pack.manifest.n_items} {kind} item(s)) -> {path}")


@pack_app.command("validate")
def pack_validate(
    pack_path: Annotated[Path, typer.Argument(help="Pack JSON to validate.")],
) -> None:
    """Validate a pack's manifest, checksum, and item schema."""
    from volo_packs import read_pack, validate_pack

    if not pack_path.exists():
        raise typer.BadParameter(f"Pack not found: {pack_path}")
    pack = read_pack(pack_path)
    problems = validate_pack(pack)
    if problems:
        for p in problems:
            typer.echo(f"pack validate: !! {p}")
        typer.echo(f"pack validate: {pack.ref} -> INVALID ({len(problems)} problem(s))")
        raise typer.Exit(INVALID_EXIT_CODE)
    typer.echo(
        f"pack validate: {pack.ref} [{pack.manifest.kind}] {pack.manifest.n_items} item(s) -> VALID"
    )


@pack_app.command("install")
def pack_install(
    pack_path: Annotated[Path, typer.Argument(help="Pack JSON to install.")],
    directory: _DirOpt = DEFAULT_PACK_DIR,
    force: Annotated[bool, typer.Option("--force", help="Overwrite an installed version.")] = False,
) -> None:
    """Validate a pack and install it into the local pack store."""
    from volo_packs import PackInstallError, PackStore, read_pack

    if not pack_path.exists():
        raise typer.BadParameter(f"Pack not found: {pack_path}")
    pack = read_pack(pack_path)
    try:
        entry = PackStore(directory).install(pack, force=force)
    except PackInstallError as exc:
        typer.echo(f"pack install: {exc}")
        raise typer.Exit(INVALID_EXIT_CODE) from exc
    typer.echo(
        f"pack install: {entry.name}@{entry.version} [{entry.kind}] "
        f"{entry.n_items} item(s) -> {directory}"
    )


@pack_app.command("list")
def pack_list(directory: _DirOpt = DEFAULT_PACK_DIR) -> None:
    """List installed packs."""
    from volo_packs import PackStore

    entries = PackStore(directory).entries()
    if not entries:
        typer.echo(f"pack list: no packs installed at {directory}")
        return
    for e in entries:
        typer.echo(f"pack list: {e.name}@{e.version:8} [{e.kind:10}] {e.n_items} item(s)")
    typer.echo(f"pack list: {len(entries)} pack(s)")
