# ADR 0030: the PR check is a composite Action + a sticky comment, not a hosted App

- Status: accepted
- Date: 2026-07-06

## Context

M28 (newplan P7) wants a GitHub PR check that posts the reliability report on every pull request.
The charter calls this a "PR-check App," but a GitHub App needs a hosted server to receive
webhooks — which is the paid/one-way-door territory the founder deferred (M26). This milestone
stays OSS-first: no hosting, no secrets, no new dependency.

## Decision

Deliver the PR check as a **composite GitHub Action that runs in the user's own CI**, plus a
plain `volo comment` renderer:

1. **`volo comment`** reads a `ReliabilityReport` (and optionally an `EvidencePack`, M29) and
   renders one Markdown body: the existing reliability summary plus a per-control compliance
   table. It prepends a hidden **sticky marker** (`<!-- volo-pr-check -->`) so the poster can find
   and *update* its prior comment instead of spamming one per push. Pure formatting — no network —
   so it's unit-testable and platform-independent. It emits **UTF-8 bytes** to stdout (the body
   carries emoji; a Windows cp1252 console would otherwise crash on pipe).
2. **A composite Action** (`.github/actions/volo-pr-check/action.yml`) orchestrates: `uv sync` →
   `volo ci` (writes `report.json`, `continue-on-error` so we still comment on a fail) → optional
   `volo compliance build` → `volo comment` → post the sticky comment via **`gh` + the workflow's
   `GITHUB_TOKEN`** → finally re-exit with `volo ci`'s code so the check reflects the verdict.
3. **No third-party action, no configured secrets.** Sticky-comment upsert is a few lines of
   `gh api` (list issue comments, match the marker, PATCH or POST). `gh` and the token are
   already present on GitHub runners.

## Consequences

- Zero hosting and zero marginal cost: the check runs on the user's runners against deterministic
  replay ($0 API). A team adopts it by copying one workflow file.
- The comment is *sticky*: one comment per PR, updated in place — no notification spam across a
  long PR. The marker is the contract; changing it would orphan old comments (documented).
- Because `volo ci` runs with `continue-on-error`, the comment is posted even on a regression, and
  the job still fails via the final re-exit — the reviewer sees *why* it failed, not just that it
  did.
- This is not a hosted App: it can't do cross-repo dashboards or org-level policy — that's the
  cloud plane (M26), intentionally out of scope here.

## Alternatives considered

- **A hosted GitHub App** — deferred: needs a server (webhooks, auth, storage) = the paid
  one-way-door decision M26 is gated on. The Action gets the same PR-comment outcome with none of
  it.
- **A third-party comment action** (e.g. create-or-update-comment) — rejected: adds an external
  dependency for ~6 lines of `gh api`; keeping it first-party means no supply-chain surface.
- **Emit the comment only to the job summary** (`$GITHUB_STEP_SUMMARY`) — kept as well (`volo ci`
  already does), but a PR comment is what reviewers actually see; the Action does both.
