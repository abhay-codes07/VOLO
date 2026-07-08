# ADR 0037: certification composes existing gates into one signed, reproducible certificate

- Status: accepted
- Date: 2026-07-08

## Context

M33 (newplan P10) is the "Volo Certified" program — the brand endgame: a public, credible pass/fail
credential for an agent, the "UL of agents". The temptation is to invent a new scoring rig; the
right move is to *compose* the gates Volo already has so a certificate means exactly what the rest
of the product measures.

## Decision

1. **Certification = reliability + safety, nothing new.** `certify(recording, agent)` runs the
   existing reliability suite (`orchestrate`, M4) *and* the red-team corpus (`run_redteam`, M15)
   against the agent, then applies `CertCriteria` to the results. The **Volo Score** is the mean of
   the four reliability dimensions × 100 (under adversity) — the same signals the leaderboard (M24)
   ranks on, not a parallel metric.
2. **Public, legible criteria.** Default bar: `require_safe` (no red-team attack may land) and
   `min_volo_score = 60`; `require_ship` (a ship verdict under adversity) is opt-in because the
   suite is deliberately adversarial. Every failure is recorded as a human-readable `reason`, so a
   "not certified" is explainable, not a black box. In practice safety is the sharp discriminator:
   a guarded agent certifies; a prompt-injectable one fails on `54/54 attacks landed` at the same
   Volo Score.
3. **Signed, checksummed, reproducible.** A `Certificate` carries a content checksum (sha256 over
   the canonical result, excluding `issued_at`) and an optional HMAC publisher signature — the
   *same* scheme as pack/evidence signing (ADR-0028/0029), so there's one signing story across the
   product. Because the underlying runs are seeded and offline, a certifier reproduces the same
   certificate; a keyring verifies who issued it and that it wasn't edited.
4. **A badge is a view.** `render_badge_svg`/`_markdown` turn a certificate into a self-contained
   SVG / README snippet. `volo certify run|verify|badge` is the lifecycle; `run` exits **10**
   (the next gate code after multi-agent's 9) when not certified.

## Consequences

- A certificate is only ever as strong as the recording it was issued against — it certifies
  behavior on *that* baseline. Stated plainly: certification is per-recording evidence, not a
  universal guarantee; a registry (future) would track cert ↔ recording ↔ agent version.
- Reusing the reliability + red-team engines means certification improves for free as those do, and
  a certified agent's number is directly comparable to its leaderboard rank.
- HMAC signing is symmetric (shared secret), same limitation as ADR-0028; an asymmetric
  (Ed25519/RS256) publisher key is the same documented upgrade, gated on a crypto dependency.
- The score/criteria are intentionally simple and transparent; a heavier rubric (weighting
  dimensions, domain-specific gates) is additive on top of `evaluate`.

## Alternatives considered

- **A bespoke certification score** — rejected: a second metric that could disagree with the
  leaderboard erodes trust; composing the existing signals is more credible and less to maintain.
- **Require a ship verdict by default** — rejected: the suite is adversarial by design, so most
  honest agents are `no_ship` under it; safety + a score floor is the meaningful default bar, with
  `require_ship` available for stricter programs.
- **Unsigned certificates** — rejected: a credential that can't be verified or attributed is
  worthless; the checksum + HMAC signature (reused from packs) makes it tamper-evident and
  attributable with no new machinery.
