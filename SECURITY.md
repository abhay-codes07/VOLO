# Security Policy

Volo records and replays AI-agent runs, which can include captured tool I/O and model traffic.
We take the safety of that data seriously and welcome responsible disclosure.

## Supported versions

Volo is pre-1.0. Security fixes land on the latest `0.1.x` line and `main`.

| Version | Supported |
|---|---|
| `0.1.x` (latest) | ✅ |
| older pre-releases | ❌ |

## Reporting a vulnerability

**Please do not open a public GitHub issue for security problems.**

Report privately via GitHub's
[**private vulnerability reporting**](https://github.com/abhay-codes07/VOLO/security/advisories/new)
("Report a vulnerability" on the repo's Security tab). Include:

- a description of the issue and its impact,
- steps to reproduce (a minimal PoC if possible),
- affected version / commit, and any suggested remediation.

We aim to acknowledge a report within **72 hours** and to agree on a disclosure timeline once the
issue is confirmed. Please give us a reasonable window to ship a fix before any public disclosure.

## Scope & hardening posture

Volo's trust boundaries and the defaults that keep it safe are documented in
[ADR-0012](docs/adr/0012-security-trust-boundaries.md). Highlights worth knowing before you
deploy:

- **Source-informed Tier-2 synthesis is OFF by default.** Executing a recording's `source_hint`
  is gated behind `VOLO_TRUST_SOURCE_HINTS=true` — only enable it for recordings you trust.
- **API auth is opt-in but required off-localhost.** Set `VOLO_REQUIRE_AUTH=true` (and swap in a
  real `get_principal`) for any non-local deployment; mutating routes then reject anonymous
  callers. `/healthz` is intentionally unauthenticated for liveness probes and returns no
  sensitive data.
- **Path traversal is contained** on all filesystem-backed routes (`_safe_data_path`).
- **Secrets are redacted** from recordings (API keys, tokens, JWTs, provider-specific patterns)
  with a size cap on stored artifacts.

If you find a gap in any of the above, that's exactly the kind of report we want.

## Operational hygiene

- Keep API keys in a gitignored `.env` (auto-loaded), never in source or recordings.
- Treat recordings as potentially sensitive: they can contain captured request/response bodies.
