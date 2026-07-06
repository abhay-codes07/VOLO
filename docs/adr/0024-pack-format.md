# ADR 0024: content packs are one JSON file — manifest + items + content checksum

- Status: accepted
- Date: 2026-07-06

## Context

M20 (newplan P6, wave 3) makes Volo's adversarial content shareable: attack corpora (M15),
personas (M17), and scenario selections. Each already serializes to JSON on its own; a *pack*
needs to add identity (name + version), integrity (tamper detection), and a uniform lifecycle so
the registry (M21) and marketplace trade in one artifact type.

## Decision

1. **A pack is a single JSON file: `{manifest, items}`.** The manifest carries `name`, `version`
   (semver), `kind`, a `checksum`, `n_items`, and provenance (`author`, `pack_format`,
   `volo_min_version`). `items` is the kind-specific payload — the same dicts the underlying
   type already round-trips (`Attack.to_dict`, `Persona.to_dict`, scenario configs). No new
   per-kind file format; a pack is generic transport.
2. **Integrity via a content checksum.** `checksum = sha256(canonical_json(items))` — stable
   across key order and whitespace (reuses `volo_core.canonical_json`). `validate_pack`
   recomputes it, so any post-build edit to items is caught, along with `n_items` drift. This is
   what makes a downloaded pack trustworthy without a signature (signing is a later, additive
   layer for *verified* publishers).
3. **Kinds are a one-entry extension point.** `volo_packs.kinds` maps each kind to an item
   validator (delegating to the real type's constructor, so validation can't drift from
   behavior) and a `starter_items` builder (the built-in library). Adding a kind is one
   validator + one starter.
4. **`PackStore` mirrors `CorpusBank`** (ADR-0017): a directory of `name@version.json` files plus
   `index.json`, dedupe by `name@version`, install validates before writing. The registry (M21)
   publishes/fetches against this exact on-disk shape — no second format.
5. **CLI lifecycle:** `volo pack init|validate|install|list`; `validate` exits 1 on a bad
   checksum/semver/schema (a CI gate for pack authors).

## Consequences

- A pack is human-diffable JSON, consistent with recordings (bible §9.1) — reviewers can read a
  pack in a PR. The checksum means a reviewer/CI can also *prove* it wasn't altered after build.
- Because item validation calls the real constructor, a pack can never install content the engine
  can't load — a persona pack with a nameless persona or an attack whose payload lacks its canary
  fails at `validate`, not at run time.
- Semver is validated but not yet *resolved* (no ranges / "latest"); that arrives with the
  registry. Multiple versions of the same pack coexist in the store.
- Checksum ≠ signature: it detects accidental/careless tampering, not a determined forger.
  Publisher signing is deferred to the verified-marketplace milestone (M25) and layers on without
  changing the format.

## Alternatives considered

- **A pack as a directory / tarball** — rejected for v1: a single JSON file is trivial to diff,
  fetch, and check into git; a corpus of packs is a directory (the store), which is enough.
- **Per-kind bespoke formats** (an "attack pack" schema separate from a "persona pack" schema) —
  rejected: duplicates the manifest/checksum/lifecycle three times; the generic envelope with a
  `kind` discriminator is one code path.
- **No checksum, trust the file** — rejected: the whole point of shareable inventory is
  provenance; silent corruption or edits would erode trust in the marketplace.
