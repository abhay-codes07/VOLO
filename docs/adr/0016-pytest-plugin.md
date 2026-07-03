# ADR 0016: pytest-volo — the engine behind one marker and four fixtures

- Status: accepted
- Date: 2026-07-03

## Context

M12 (dev-surface pillar): developers should not need `volo run` and a separate report format to
gate reliability — checks should live in the test suite they already have. The question is the
public API shape of a pytest plugin, which is hard to change once released.

## Decision

A new package `packages/pytest-volo` (module `pytest_volo`), auto-registered via the standard
`pytest11` entry point. The whole surface is **one marker + four fixtures + two helpers**:

- **Marker** `@pytest.mark.volo_recording(path, *, tier=1, fuzz=None, seed=0)` is the single
  configuration point. Paths resolve: absolute → `volo_recordings_dir` ini (relative to
  rootdir) → the test file's directory → rootdir.
- **`volo_recording`** — the loaded baseline `Recording`.
- **`volo_env`** — a `SimulatedEnvironment` (Tier-1 default, `tier=2` opt-in) installed as the
  active environment (ContextVar) for the test's duration, so agents using volo proxies hit the
  sim with zero test-side plumbing.
- **`volo_scenario`** — implemented via `pytest_generate_tests`: requesting the fixture
  parametrizes the test over the scenario library, one test item per operator (ids = operator
  names, so `-k corrupt_field` works). Library selection: explicit `fuzz="mcp"|"default"` wins;
  otherwise recordings with `agent_meta.framework == "mcp"` auto-select the MCP fuzz library
  (ADR-0015), everything else gets the seven default operators (ADR-0005). Each param is a
  `VoloScenario` (scenario metadata + mutated recording + active env).
- **`volo_run`** — a thin callable over `volo_runner.orchestrate` returning the
  `ReliabilityReport`; `assert_ship` / `assert_no_ship` (in `pytest_volo`) raise with the
  aggregate + per-scenario metrics attached, so a red CI run names the failure class.

Tested with `pytester` (real inner test suites). Because pytest forbids `pytest_plugins` in
non-root conftests, the monorepo enables pytester via `-p pytester` in the root `addopts`.

## Consequences

- The plugin is installed monorepo-wide, so the marker/fixtures are registered for all our own
  suites — additive only; `pytest_generate_tests` acts solely on tests that request
  `volo_scenario`.
- Scenario generation happens at collection time (the recording is loaded then), so hostile
  worlds appear in `--collect-only` and shard cleanly under xdist-style splitting.
- `tier=2` uses the default synthesizer chain; offline it degrades to flag-on-unknown
  (`Tier2Miss`), which is exactly the asserted behavior.
- The marker is the only config surface; if per-test overrides beyond
  `tier`/`fuzz`/`seed` are needed later, they extend the marker kwargs without breaking the API.

## Alternatives considered

- **A `volo_scenarios(...)` decorator** instead of fixture-triggered parametrization —
  rejected: two ways to spell parametrization (decorator + marker) for no added power;
  fixtures compose with pytest's own `parametrize` already.
- **Config via CLI flags / ini only** (no marker) — rejected: recordings are per-test facts,
  not per-run config; a marker keeps the binding next to the test.
- **Folding the plugin into `volo-sdk`** — rejected: pulls pytest into the SDK's dependency
  tree; the plugin composes the other packages and belongs at the edge (hexagonal rule).
