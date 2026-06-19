# ADR 0008: Project name — Volo

- **Status:** accepted
- **Date:** 2026-05-31
- **Deciders:** founder
- **Related:** bible §2.4, ADR-0001
- **Supersedes:** the "AgentSim codename" used throughout sessions 01–04.

## Context

The product had been carried under the find-and-replaceable codename **AgentSim** while we
finished M1–M4. Bible §0 explicitly told us the codename would be retired before any commit
history, public surface, or trademark exposure. Three constraints needed to be resolved at
once:

1. The **product metaphor** is a flight simulator (bible §2.2, §8) — the name has to fit.
2. The candidate had to be **available**: no conflicting trademark in the AI-tools space, an
   acquirable domain (`.dev` or `.ai` preferred), and a free GitHub-org handle.
3. The candidate had to be **short and pronounceable** in English so it stands up at conference
   shorthand and on the CLI (`volo run …` reads cleaner than the alternatives).

The six bible-listed alternates failed at least one of these. From a founder availability check:

- **Crucible** — taken by a recognizable AI tooling brand. Rejected.
- **Wind Tunnel** — taken (and not a single token). Rejected.
- **Proving Ground** — long, generic, weak in CLI form. Rejected.
- **Hangar** — strong metaphor but the org/domain are taken in adjacent spaces. Rejected.
- **Understudy** — clever, but the metaphor steers toward "B-team" rather than rigour. Rejected.
- **Dryrun** — already a common CLI flag name and a brand in observability. Rejected.

## Decision

The product name is **Volo** — from the Latin *volō*, "I fly". It maps directly to the
flight-test metaphor without metaphor-stretching, is one syllable, and is unique in the
AI-evaluation tooling space.

Concretely:

- Python packages: `volo-core`, `volo-sdk`, `volo-simulator`, `volo-scenarios`,
  `volo-reliability`, `volo-runner`, `volo-diff`, `volo-models`, `volo-cli`, `volo-api`.
- Python module names: `volo_*`.
- CLI binary: `volo`. Verbs: `record / sim / scenarios / run / ci / diff / demo`.
- Environment variables: `VOLO_DATA_DIR`, `VOLO_FRONTIER_OPT_IN`, `VOLO_FRONTIER_MAX_USD`,
  `VOLO_LOG_LEVEL`, `VOLO_API_HOST`, `VOLO_API_PORT`, `NEXT_PUBLIC_VOLO_API`.
- Data dir default: `./.volo/` (replaces `./.agentsim/`).
- Constitution: `VOLO_BUILD_BIBLE.md` at repo root.

## Consequences

- **Easy:** every cross-reference in code already uses `volo_*` and the Bible/STATUS/CHANGELOG
  are consistent. CI workflows renamed (`volo-selfcheck.yml`). Frontend brand is synced.
- **Easy:** the metaphor extends naturally into the brand voice ("flight test", "mission
  control", "telemetry").
- **Hard:** any existing recordings on disk under `./.agentsim/` are not migrated by the SDK —
  the bulk rename includes a `mv` for the founder's local data dir. Anyone else running an
  earlier checkout needs to `mv .agentsim .volo` themselves before they sync.
- **Locked-in:** trademark / domain registration (`volo.dev`, `volo.ai`) and GitHub-org claim
  (`volo-sim` or `volo`) need to be filed before any public artifact ships. These are open
  follow-ups, not blockers for internal work.

## Alternatives considered

See above for the bible-listed six. No other candidates were seriously considered after the
founder verified Volo was clear in our space.
