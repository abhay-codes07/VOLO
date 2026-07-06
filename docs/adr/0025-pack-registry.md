# ADR 0025: the pack registry is a git-hosted JSON index — no service, checksum-verified installs

- Status: accepted
- Date: 2026-07-06

## Context

M21 (newplan P6, wave 3) makes packs (ADR-0024) installable by name across teams. The bible's
cost discipline (§11) rules out standing up a registry service; the marketplace must start at
$0 infra.

## Decision

1. **The registry is a single `index.json`, hosted anywhere.** Shape:
   `{registry_format, packs: {name: {kind, versions: {version: {url, checksum, n_items}}}}}`.
   It lives in a public git repo (raw file URL), on any web host, or a local path. There is **no
   registry service and no database** — publishing is a commit to that file; installing is an
   HTTP GET of the index plus the pack it points at. This is the same "git-backed index" pattern
   the shadow corpus and pack store already use, extended across the network.
2. **Sources are URL-or-path, via stdlib.** `_read_source_text` handles `http(s)://`, `file://`,
   and local paths through `urllib` — no HTTP dependency. So a private registry can be a plain
   directory, and CI can point at a raw git URL; the same code path serves both.
3. **Installs are checksum-verified against the index.** `install_from_registry` resolves the
   version (latest by **numeric** semver when unspecified), fetches the pack from its `url`, and
   refuses it unless (a) its `name@version` matches what was requested and (b) its recomputed
   content checksum equals the checksum the registry recorded at publish time — *and* the pack
   validates (ADR-0024). So a pack swapped or corrupted at its hosting URL after publishing cannot
   be installed under a trusted name; the index entry is the trust anchor.
4. **`register` is the publish primitive; the git commit is the publish act.** `volo pack publish`
   validates the pack and writes/updates the local `index.json`; the author commits it to the
   registry repo. Kind is pinned per name (a name can't switch from `attacks` to `personas`).

## Consequences

- $0 infra, fully forkable: anyone can host a registry by committing a JSON file; a private
  registry is a directory. No accounts, no server to run or secure.
- Trust rests on the index's integrity (git history + review) plus the per-pack checksum. This
  stops accidental corruption and post-publish tampering of the *pack*, but a writer with commit
  access to the index could still point a name at malicious content — publisher **signing** (a
  verified-marketplace feature, M25) is the answer and layers on without changing the format.
- Latest-version resolution is numeric semver only (no ranges, no pre-release/build metadata);
  adequate for M21, extendable later.
- The index grows with every published version (versions are never removed here); pruning/yank is
  a future registry operation.

## Alternatives considered

- **A hosted registry API** (like PyPI/npm) — rejected: violates the $0-infra start and adds an
  operational surface; the git-index pattern gets install-by-name with none of it.
- **Fetch packs by convention** (derive the URL from name+version) — rejected: couples the
  registry to one host's URL scheme; an explicit `url` per version lets packs live anywhere.
- **Trust the fetched pack's own checksum** — rejected: a tampered pack would carry a matching
  self-checksum; the *registry's* recorded checksum is the independent anchor that makes
  verification meaningful.
