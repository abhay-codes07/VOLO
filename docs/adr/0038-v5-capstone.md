# ADR 0038: v5.0 is a capstone — an integration proof, not a new subsystem

- Status: accepted
- Date: 2026-07-08

## Context

M34 closes the v1.1→v5.0 charter. Every pillar (P1–P10) has shipped as its own package across
M1–M33. The risk at the end of a long build is that the pieces work in isolation but don't compose
— that the "platform" is really a pile of packages. The capstone must *prove* coherence, not add
another feature nobody asked for.

## Decision

1. **The capstone is an end-to-end integration test, not code.** `tests/test_full_pipeline_v5.py`
   drives a *single* baseline recording through every gate in sequence — reliability
   (`orchestrate`) → red-team (`run_redteam`) → certification (`certify`, signed) → compliance
   evidence pack (`build_evidence_pack`, signed) → cloud ingest (`volo_cloud.service`) — and
   asserts the whole chain holds. A second test proves the gate has *teeth*: the same pipeline
   *denies* a prompt-injectable agent (red-team `vulnerable`, certification failed). This is the
   real deliverable — executable evidence that the product is one thing.
2. **No new one-way doors.** v5.0 introduces no new dependency, service, or architectural
   commitment; it ties together what exists. The open-core boundary (ADR-0001), the local-first
   rule (§11), and the signing scheme (ADR-0028/0029/0037) are unchanged.
3. **Docs state the whole, honestly.** The README gains a "full pipeline (v5.0)" diagram and an
   accurate package inventory; the license section reflects the open-core split (Apache-2.0 core +
   commercial `cloud/`). No marketing beyond what the tests back.

## Consequences

- There is now a living, CI-run assertion that record → … → certify → evidence → cloud composes;
  if a future change breaks the seam between two pillars, this test fails. That's the capstone's
  lasting value — it converts "the platform is coherent" from a claim into a check.
- v5.0 is a milestone/version marker, not a feature release; the tag records the charter's
  completion. Post-v5.0 work (asymmetric signing, RS256/JWKS SSO, hosted infra, a live computer-use
  driver) is already enumerated in the relevant ADRs as the documented next steps.
- Keeping the capstone to an integration test (plus docs) honors "narrow and deep beats broad and
  shallow" at the very end: the strongest possible closing artifact is proof, not more surface.

## Alternatives considered

- **A grand new "platform" feature** (a unified dashboard tying everything together) — deferred:
  valuable but it's a product surface, not what makes the charter *complete*; the coherence proof
  is the honest capstone and the dashboard can follow.
- **Just tag v5.0 with no new test** — rejected: the version would assert completeness with nothing
  verifying the pieces compose; the integration test is what earns the tag.
