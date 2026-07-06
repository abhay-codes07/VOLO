"""Registry: publish to an index, resolve versions, install-by-name with checksum verification."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import pytest

from volo_packs import (
    PackStore,
    RegistryError,
    RegistryIndex,
    build_pack,
    install_from_registry,
    load_index,
    register,
    resolve,
    save_index,
    starter_items,
    write_pack,
)


def _pack(name: str = "acme", version: str = "1.0.0", kind: str = "attacks"):
    return build_pack(name=name, version=version, kind=kind, items=starter_items(kind))


def test_register_and_resolve_latest(tmp_path: Path) -> None:
    idx = RegistryIndex()
    p10 = _pack(version="1.0.0")
    p12 = _pack(version="1.2.0")
    p11 = _pack(version="1.11.0")  # numeric, not lexical, ordering
    register(idx, p10, "file://x/1.0.0.json")
    register(idx, p12, "file://x/1.2.0.json")
    register(idx, p11, "file://x/1.11.0.json")

    version, entry = resolve(idx, "acme")  # latest by semver
    assert version == "1.11.0"
    assert entry.checksum == p11.manifest.checksum

    v, _ = resolve(idx, "acme", "1.0.0")
    assert v == "1.0.0"


def test_resolve_unknown_raises() -> None:
    with pytest.raises(RegistryError, match="not in the registry"):
        resolve(RegistryIndex(), "nope")


def test_register_rejects_kind_conflict() -> None:
    idx = RegistryIndex()
    register(idx, _pack(kind="attacks"), "u1")
    with pytest.raises(RegistryError, match="registered as kind"):
        register(idx, _pack(kind="personas"), "u2")


def test_install_from_registry_via_local_files(tmp_path: Path) -> None:
    pack = _pack(version="2.0.0")
    pack_file = write_pack(pack, tmp_path / "acme.json")
    idx = RegistryIndex()
    register(idx, pack, str(pack_file))  # url is a local path
    index_file = save_index(idx, tmp_path / "index.json")

    store = PackStore(tmp_path / "store")
    entry = install_from_registry("acme", index_file, store)
    assert entry.name == "acme" and entry.version == "2.0.0"
    assert len(store.entries()) == 1


def test_install_rejects_tampered_pack(tmp_path: Path) -> None:
    pack = _pack(version="1.0.0")
    pack_file = tmp_path / "acme.json"
    idx = RegistryIndex()
    register(idx, pack, str(pack_file))  # records the *good* checksum
    index_file = save_index(idx, tmp_path / "index.json")

    # now host a tampered pack at that url
    blob = json.loads(pack.to_json())
    blob["items"].append(
        {
            "id": "x",
            "attack_class": "jailbreak",
            "description": "d",
            "payload": "p CANARY_X",
            "canary": "CANARY_X",
        }
    )
    pack_file.write_text(json.dumps(blob), encoding="utf-8")

    with pytest.raises(RegistryError, match="checksum mismatch"):
        install_from_registry("acme", index_file, PackStore(tmp_path / "store"))


def test_verified_flag_and_signed_install(tmp_path: Path) -> None:
    from volo_packs import sign_pack

    pack = sign_pack(_pack(version="1.0.0"), publisher="acme", secret="s3cret")
    pack_file = write_pack(pack, tmp_path / "acme.json")
    idx = RegistryIndex()
    register(idx, pack, str(pack_file))
    index_file = save_index(idx, tmp_path / "index.json")

    # the registry marks the version verified + records the publisher
    _, entry = resolve(load_index(index_file), "acme")
    assert entry.verified is True and entry.publisher == "acme"

    # install with a matching keyring succeeds
    store = PackStore(tmp_path / "store")
    installed = install_from_registry(
        "acme", index_file, store, keyring={"acme": "s3cret"}, require_signed=True
    )
    assert installed.name == "acme"


def test_verified_install_without_keyring_is_refused(tmp_path: Path) -> None:
    from volo_packs import sign_pack

    pack = sign_pack(_pack(version="1.0.0"), publisher="acme", secret="s3cret")
    pack_file = write_pack(pack, tmp_path / "acme.json")
    idx = RegistryIndex()
    register(idx, pack, str(pack_file))
    index_file = save_index(idx, tmp_path / "index.json")

    # verified entry + no/ wrong keyring → refuse (entry.verified forces the check)
    with pytest.raises(RegistryError, match="signature verification failed"):
        install_from_registry("acme", index_file, PackStore(tmp_path / "store"), keyring={})


def test_require_signed_refuses_unsigned_pack(tmp_path: Path) -> None:
    pack = _pack(version="1.0.0")  # unsigned
    pack_file = write_pack(pack, tmp_path / "acme.json")
    idx = RegistryIndex()
    register(idx, pack, str(pack_file))
    index_file = save_index(idx, tmp_path / "index.json")

    with pytest.raises(RegistryError, match="signature verification failed"):
        install_from_registry(
            "acme", index_file, PackStore(tmp_path / "store"), require_signed=True
        )


def test_install_over_http(tmp_path: Path) -> None:
    pack = _pack(version="1.0.0", kind="personas")
    server = HTTPServer(("127.0.0.1", 0), _make_handler(pack))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        idx = RegistryIndex()
        register(idx, pack, f"{base}/pack.json")
        index_file = save_index(idx, tmp_path / "index.json")
        # index itself is local; the pack is fetched over http
        store = PackStore(tmp_path / "store")
        entry = install_from_registry("acme", index_file, store)
        assert entry.name == "acme" and entry.kind == "personas"

        # and the index can be loaded over http too
        remote = load_index(f"{base}/index.json")
        assert "acme" in remote.packs
    finally:
        server.shutdown()


def _make_handler(pack: Any) -> type[BaseHTTPRequestHandler]:
    pack_body = pack.to_json().encode("utf-8")
    index = RegistryIndex()
    register(index, pack, "unused")

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            body = pack_body if self.path.endswith("pack.json") else index.to_json().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args: Any) -> None:
            del args

    return Handler
