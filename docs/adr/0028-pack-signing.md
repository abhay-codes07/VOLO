# ADR 0028: pack signing is HMAC-SHA256 v1 over identity+checksum; asymmetric is the next step

- Status: accepted
- Date: 2026-07-06

## Context

M25 (marketplace GA, closes wave 3) adds **verified publishers** to the pack registry
(ADR-0024/0025). The registry's checksum already stops post-publish tampering of a pack's
*content*; signing adds *provenance* — proof a pack came from the publisher the registry names. No
asymmetric-crypto library is installed, and the bible (§0) requires founder sign-off before adding
a dependency; hand-rolling asymmetric crypto is not acceptable.

## Decision

1. **v1 signatures are HMAC-SHA256, stdlib only.** `sign_pack` computes
   `HMAC(secret, "name@version:checksum")` — binding the pack's **identity and content** — and
   stores a `{publisher, algorithm, value}` signature on the manifest. `verify_pack_signature`
   recomputes it against a `Keyring` (`publisher → secret`) using a constant-time compare. The
   signature lives in the manifest and does *not* affect the content checksum (which is over
   `items`), so signing an existing pack is non-destructive.
2. **The algorithm is tagged, so the format survives an upgrade.** The signature envelope carries
   `algorithm: "hmac-sha256"`. Adding Ed25519 later is a new algorithm value + verify branch — no
   manifest/registry format change. This is written down now so v1 isn't a dead end.
3. **The registry records verification.** `RegistryVersion` gains `verified` + `publisher`, set at
   publish time from the pack's signature. `install_from_registry` verifies the signature when the
   caller passes `require_signed` **or** the registry marks the version `verified`; a missing/bad
   signature (or absent keyring entry) refuses the install.
4. **The seed registry ships unsigned.** The official built-in packs (`registry/`) are trivially
   reproducible (`volo pack init <kind>` → byte-identical items → same checksum), so their
   integrity is self-evident from the checksum; signing them would require committing a shared
   secret, which HMAC's model makes pointless. Signing is proven by tests + CLI + private-registry
   use.

## Consequences

- **HMAC is symmetric:** the verifier holds the same secret the signer used, so it authenticates
  within a trust group (a company, a team, a private registry) but is *not* public-key provenance
  — anyone with the keyring can forge. This is honest and adequate for private/team marketplaces;
  it is explicitly **not** sufficient for an open public marketplace where verifiers shouldn't hold
  publisher secrets. That gap is closed by the Ed25519 upgrade (§2), gated on adding a vetted
  crypto dependency with founder approval.
- Because the signature binds `name@version:checksum`, changing the version or the content
  invalidates it (tested) — a signature can't be lifted onto a different or altered pack.
- `verified` in the registry is only as trustworthy as the index's write access + the keyring;
  it's a convenience flag, not a cryptographic guarantee on its own until asymmetric lands.

## Alternatives considered

- **Add `cryptography`/PyNaCl now for Ed25519** — deferred: needs founder sign-off for a new
  dependency; HMAC ships value today and the tagged envelope makes the upgrade clean.
- **Hand-roll Ed25519** — rejected outright: never hand-roll asymmetric crypto.
- **Sign the whole pack JSON** — rejected: the checksum already covers content; signing
  `name@version:checksum` is smaller, stable, and binds exactly identity+content.
- **Sign the built-in seed packs** — rejected: would commit a forgeable shared secret for no gain
  given the packs are reproducible.
