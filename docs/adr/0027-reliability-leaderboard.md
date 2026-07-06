# ADR 0027: the leaderboard scores correctness × robustness into one deterministic Volo Score

- Status: accepted
- Date: 2026-07-06

## Context

M24 (newplan P9) turns the fidelity benchmark into a public **reliability leaderboard** — the
credibility and dataset engine. The design questions: what single number ranks agents, and how to
keep it honest, deterministic, and $0 to host.

## Decision

1. **One score, two halves.** For each agent Volo records one run and then runs the full
   adversarial scenario suite (`orchestrate`, seeded, N runs/scenario). The **Volo Score** (0-100)
   is `50% × clean-run correctness + 50% × adversarial robustness`, where correctness is the
   baseline recording's faithfulness (is the normal answer grounded in tool evidence?) and
   robustness is the mean of the four DFAH dimensions under the scenario suite. This rewards
   agents that are **both** correct and robust: a correct-but-flaky agent loses the robustness
   half; a stable-but-wrong agent loses the correctness half.
2. **Deterministic, no live models.** Everything is Tier-1 replay + the heuristic judge — seeded,
   reproducible, free. The same agent always scores the same, so the leaderboard is a fact, not a
   sample. (`examples/flaky_agent.py` is deliberately nondeterministic to demonstrate the score
   discriminating — 88 stable vs 21 flaky.)
3. **Static artifact, $0 infra.** `benchmarks/leaderboard.py` emits `leaderboard.json` (data), a
   Markdown table, and a **self-contained HTML page** (inline CSS, no assets) — committed and
   servable via GitHub Pages. A weekly GitHub Actions cron
   (`examples/workflows/volo-leaderboard.yml`) rebuilds and commits it. No leaderboard service.
4. **The corpus is example agents for now.** The `ENTRIES` list scores the bundled examples
   (echo/calc/calc_v2/research/flaky). Framework × model breadth grows by adding entries; the row
   already carries `framework`, `model`, and a per-failure-class breakdown for that expansion.

## Consequences

- The score is a *summary*; the per-dimension and per-failure-class fields on each row keep the
  detail a skeptic needs. Publishing both the number and its components is what makes "Volo Score"
  defensible rather than a black box.
- Toy example agents self-ground (their echo-summarizer makes any answer "faithful"), so among
  them correctness rarely separates — the flaky agent is what proves the mechanism discriminates.
  Real submitted agents will spread on both halves.
- Weighting is fixed at 50/50; a future revision could tune it, but any change is a score-version
  bump (documented, like a schema change) so historical scores stay comparable.
- Determinism means a *regression* in an agent shows up as a score drop across rebuilds — the
  leaderboard doubles as a trend, like the shadow sentinel but public.

## Alternatives considered

- **Rank by a single dimension** (e.g. faithfulness) — rejected: hides the correctness/robustness
  trade-off that's the whole reliability story; one dimension is gameable.
- **A hosted leaderboard with submissions** — rejected for M24: violates $0-infra and adds
  moderation/abuse surface; the git-committed static board is forkable and trustless. Submissions
  layer on later (a PR adds an `ENTRIES` row + a recording).
- **Include live-model runs for a model axis** — rejected: nondeterministic and costs money,
  breaking the "same score every time" property that makes a leaderboard credible.
