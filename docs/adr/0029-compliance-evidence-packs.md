# ADR 0029: compliance evidence is derived from existing reports, checksum-sealed, framework-mapped

- Status: accepted
- Date: 2026-07-06

## Context

M29 (newplan P10, wave 4 — OSS-first, no hosting) gives regulated buyers *evidence* that an agent
was tested. Volo already emits the raw material (reliability reports, red-team safety annexes,
shadow drift reports); the milestone is packaging it as a verifiable, auditor-facing artifact
mapped to control frameworks — without becoming a legal-advice product.

## Decision

1. **Evidence is derived, never re-run.** `build_evidence_pack` consumes artifacts Volo already
   produced (a `ReliabilityReport`, a `SafetyAnnex`, a drift-report dict) and turns each into an
   `EvidenceItem` with a `passed` signal (`ship`/`safe`/`not drifted`). No new testing happens at
   compliance time — the evidence *is* the prior deterministic run, so the pack is reproducible.
2. **Controls are a small, honest catalog.** `controls.py` maps ~10 controls across three
   frameworks (EU AI Act, ISO/IEC 42001, SOC 2) to the evidence kinds that satisfy them. Each
   control's state is the **weakest** of its required kinds: `unmet` (evidence absent) <
   `partial` (present but not passing) < `satisfied`. Shipped with an explicit "mapping aid, not
   legal advice" disclaimer in every rendering.
3. **The pack is checksum-sealed and optionally signed.** `content_checksum` is a sha256 over the
   agent name + frameworks + evidence + controls, **excluding the `generated_at` timestamp**, so
   regenerating from the same evidence is byte-reproducible and any later edit is detectable.
   `sign_evidence`/`verify_evidence` add an HMAC-SHA256 publisher signature over
   `agent_name:checksum` (the same shared-secret scheme as pack signing, ADR-0028; verify also
   re-checks the checksum, so a tampered pack fails signature too).
4. **CLI is a gate.** `volo compliance build --require-satisfied` exits **8** if any control is
   unmet; `volo compliance verify` exits **1** on a checksum or signature failure. Renders JSON +
   Markdown + a self-contained HTML report. Pure OSS, no hosting, no new dependency (stdlib
   `hashlib`/`hmac`).

## Consequences

- The pack's trustworthiness inherits the underlying runs' determinism: an auditor can re-run the
  Volo suite and get the same reports, hence the same checksum — evidence you can independently
  reproduce, not just read.
- `passed` maps a `no_ship`/`vulnerable`/`drifted` result to `partial`, not `unmet` — "we tested
  and it failed" is different from "we didn't test." That distinction is the point of an evidence
  pack and is surfaced per control.
- The catalog is deliberately small and version-pinned to this ADR; expanding or re-mapping
  controls is a catalog change (reviewable), and a future revision that alters mappings should note
  it so historical packs remain interpretable.
- HMAC signing carries the same symmetric limitation as ADR-0028 (fine for a company/auditor trust
  pair; asymmetric is the public-marketplace upgrade).

## Alternatives considered

- **Re-run tests at compliance time** — rejected: non-reproducible and slow; the evidence should be
  the exact runs that were reviewed, not a fresh sample.
- **A single pass/fail compliance verdict** — rejected: hides which controls lack evidence vs. have
  failing evidence; per-control tri-state is what an auditor needs.
- **Encode a full legal control library** — rejected: scope and liability; a focused, disclaimed
  mapping over the three most-requested frameworks is honest and useful, and the catalog is
  extensible.
