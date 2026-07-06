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
    ref: Annotated[
        str,
        typer.Argument(help="A pack JSON file, or a pack NAME when --registry is given."),
    ],
    registry: Annotated[
        str | None,
        typer.Option("--registry", help="Registry index URL/path; installs REF by name."),
    ] = None,
    version: Annotated[
        str | None, typer.Option("--version", help="Registry version (default: latest).")
    ] = None,
    directory: _DirOpt = DEFAULT_PACK_DIR,
    force: Annotated[bool, typer.Option("--force", help="Overwrite an installed version.")] = False,
    keyring: Annotated[
        Path | None, typer.Option("--keyring", help="Keyring JSON of trusted publishers.")
    ] = None,
    require_signed: Annotated[
        bool, typer.Option("--require-signed", help="Refuse packs without a valid signature.")
    ] = False,
) -> None:
    """Install a pack from a local file, or by name from a registry (--registry)."""
    from volo_packs import (
        PackInstallError,
        PackStore,
        RegistryError,
        install_from_registry,
        load_keyring,
        read_pack,
    )

    store = PackStore(directory)
    if registry is not None:
        keys = load_keyring(keyring) if keyring is not None else None
        try:
            entry = install_from_registry(
                ref,
                registry,
                store,
                version=version,
                force=force,
                keyring=keys,
                require_signed=require_signed,
            )
        except RegistryError as exc:
            typer.echo(f"pack install: {exc}")
            raise typer.Exit(INVALID_EXIT_CODE) from exc
        typer.echo(
            f"pack install: {entry.name}@{entry.version} [{entry.kind}] "
            f"{entry.n_items} item(s) from registry -> {directory}"
        )
        return

    pack_path = Path(ref)
    if not pack_path.exists():
        raise typer.BadParameter(f"Pack not found: {pack_path} (use --registry to install by name)")
    try:
        entry = store.install(read_pack(pack_path), force=force)
    except PackInstallError as exc:
        typer.echo(f"pack install: {exc}")
        raise typer.Exit(INVALID_EXIT_CODE) from exc
    typer.echo(
        f"pack install: {entry.name}@{entry.version} [{entry.kind}] "
        f"{entry.n_items} item(s) -> {directory}"
    )


@pack_app.command("sign")
def pack_sign(
    pack_path: Annotated[Path, typer.Argument(help="Pack JSON to sign (updated in place).")],
    publisher: Annotated[str, typer.Option("--publisher", help="Publisher name.")],
    secret_env: Annotated[
        str, typer.Option("--secret-env", help="Env var holding the signing secret.")
    ] = "VOLO_PACK_SECRET",
) -> None:
    """Sign a pack with a publisher secret (HMAC-SHA256) so installers can verify it."""
    import os

    from volo_packs import read_pack, sign_pack, write_pack

    if not pack_path.exists():
        raise typer.BadParameter(f"Pack not found: {pack_path}")
    secret = os.environ.get(secret_env)
    if not secret:
        raise typer.BadParameter(f"no signing secret in ${secret_env}")
    pack = sign_pack(read_pack(pack_path), publisher=publisher, secret=secret)
    write_pack(pack, pack_path)
    typer.echo(f"pack sign: {pack.ref} signed by {publisher!r} (hmac-sha256) -> {pack_path}")


@pack_app.command("verify")
def pack_verify(
    pack_path: Annotated[Path, typer.Argument(help="Pack JSON to verify.")],
    keyring: Annotated[Path, typer.Option("--keyring", help="Keyring JSON of trusted publishers.")],
) -> None:
    """Verify a pack's publisher signature against a keyring (exit 1 on failure)."""
    from volo_packs import load_keyring, read_pack, verify_pack_signature

    if not pack_path.exists():
        raise typer.BadParameter(f"Pack not found: {pack_path}")
    pack = read_pack(pack_path)
    sig = pack.manifest.signature
    if sig is None:
        typer.echo(f"pack verify: {pack.ref} is UNSIGNED")
        raise typer.Exit(INVALID_EXIT_CODE)
    if verify_pack_signature(pack, load_keyring(keyring)):
        typer.echo(f"pack verify: {pack.ref} signed by {sig.publisher!r} -> VALID")
        return
    typer.echo(f"pack verify: {pack.ref} signature from {sig.publisher!r} -> INVALID")
    raise typer.Exit(INVALID_EXIT_CODE)


@pack_app.command("publish")
def pack_publish(
    pack_path: Annotated[Path, typer.Argument(help="Pack JSON to publish.")],
    url: Annotated[str, typer.Option("--url", help="Where the pack will be hosted (raw URL).")],
    index: Annotated[
        Path, typer.Option("--index", help="Registry index file to update (created if missing).")
    ] = Path("index.json"),
) -> None:
    """Add a pack to a git-backed registry index (then commit the index to the registry repo)."""
    from volo_packs import RegistryError, RegistryIndex, load_index, read_pack, register, save_index

    if not pack_path.exists():
        raise typer.BadParameter(f"Pack not found: {pack_path}")
    pack = read_pack(pack_path)
    idx = load_index(index) if index.exists() else RegistryIndex()
    try:
        register(idx, pack, url)
    except RegistryError as exc:
        typer.echo(f"pack publish: {exc}")
        raise typer.Exit(INVALID_EXIT_CODE) from exc
    save_index(idx, index)
    typer.echo(f"pack publish: {pack.ref} [{pack.manifest.kind}] -> {index}")
    typer.echo("pack publish: commit the index to your registry repo to make it installable.")


@pack_app.command("search")
def pack_search(
    registry: Annotated[str, typer.Option("--registry", help="Registry index URL/path.")],
    query: Annotated[
        str | None, typer.Argument(help="Optional name substring to filter by.")
    ] = None,
) -> None:
    """List packs available in a registry index."""
    from volo_packs import index_summary, load_index

    rows = index_summary(load_index(registry))
    if query:
        rows = [r for r in rows if query.lower() in r["name"].lower()]
    if not rows:
        typer.echo("pack search: no matching packs")
        return
    for r in rows:
        typer.echo(
            f"pack search: {r['name']}@{r['latest']:8} [{r['kind']:10}] "
            f"{r['n_items']} item(s)  versions={','.join(r['versions'])}"
        )
    typer.echo(f"pack search: {len(rows)} pack(s)")


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
