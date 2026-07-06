# Volo pack registry (seed)

A git-backed pack registry is just an `index.json` plus the packs it points at (ADR-0025). This
is the official seed registry — the built-in [red-team](../website/redteam.mdx),
[persona](../website/personas.mdx), and scenario packs, installable by name.

```bash
# discover
uv run volo pack search --registry registry/index.json

# install by name (resolves the latest version, checksum-verified)
uv run volo pack install volo-redteam-builtin --registry registry/index.json
```

For a hosted registry, point `--registry` at the raw index URL, e.g.
`https://raw.githubusercontent.com/abhay-codes07/VOLO/main/registry/index.json`.

## Integrity

Every install verifies the fetched pack's content checksum against the checksum recorded in the
index — a pack altered after publishing won't install. These built-in packs are unsigned and
trivially reproducible (`volo pack init <kind>` yields byte-identical items, hence the same
checksum), so their integrity is self-evident.

**Verified publishers.** Packs can additionally carry an HMAC-SHA256 publisher signature
(`volo pack sign` / `verify`; install with `--require-signed --keyring`), which the registry marks
as `verified` (ADR-0028). The signature binds a pack's `name@version` to its checksum under a
publisher's secret. HMAC is a shared-secret scheme suited to private/team registries; an
asymmetric (Ed25519) upgrade for a fully public marketplace is the documented next step.
