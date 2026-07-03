# Volo — Roadmap

> Milestones map to SemVer minors. Tick checkboxes as work lands. The detailed living state is
> `docs/STATUS.md`.

## v0.1.0 — M1: Recorder + Replayer MVP ✅
Goal: a developer can `volo record` an example agent, then `volo sim` to deterministically
replay it.

- [x] Repo + memory + docs scaffolding
- [x] `volo-core` Recording schema v1
- [x] `volo-sdk` Recorder + capture proxies (auto-capture every model + tool call)
- [x] `volo-cli` (`record / sim / run / ci / diff`)
- [x] **Tier-1 Replayer** — deterministic cache-replay; `ReplayMiss` on un-recorded inputs
- [x] CLI wired end-to-end (record → JSON → sim → replay)
- [x] `examples/echo_agent` and `examples/calc_agent` exercise the full pipeline

## v0.2.0 — M2: Scenarios + Reliability ✅
Goal: derive adversarial scenarios from a recording, score reliability on multiple dimensions
(per DFAH), surface a single ship/no-ship verdict.

- [x] `volo-scenarios`: `drop_tool_result`, `corrupt_field`, `inject_latency`,
      `ambiguous_user_turn`, `prompt_injection`, `reorder_steps`, `long_horizon_repeat`
- [x] `volo-reliability`: 4 metrics + `ReliabilityReport` + 5th-percentile aggregation
- [x] Single ship/no-ship verdict surfaced via `volo run`

## v0.3.0 — M3: CI runner + GitHub Action ✅
Goal: PR gating works end to end.

- [x] `volo-runner.orchestrate` with seeded determinism
- [x] `volo ci` GitHub-Action-friendly output
- [x] `.github/workflows/ci.yml` — Python + JS jobs
- [x] `.github/workflows/volo-selfcheck.yml` — dogfood every push
- [ ] PR-comment template (deferred to M3.1 once we open the repo publicly)

## v0.4.0 — M4: Diff / root-cause ✅ (step-level)
Goal: "git bisect for agents."

- [x] `volo-diff` step-level bisect via LCS-shape alignment
- [x] `volo diff <a> <b>` CLI with human-readable report + JSON output
- [ ] Git-history bisect (M4.1)

## v0.5.0 — M5: High-fidelity simulator (Tier 2) ✅
Goal: close the MIRAGE fidelity gap (~62% → ~99%) using tool-spec + source-informed simulation.

- [x] `ToolSpec` v2 with OpenAPI / source hints
- [x] Constrained generation via local model for un-recorded inputs (`OllamaConstrainedSynthesizer`)
- [x] Source-informed synthesis + `Tier2Miss` flag-on-unknown invariant
- [x] Fidelity benchmarks vs Tier-1 baseline (100% with (a)+(b); ADR-0010)
- [x] ADR documenting the simulator algorithm (ADR-0009) + benchmark methodology (ADR-0010)

## v0.6.0 — M6: Dashboard 🟨 (screens shipped; demo gif deferred)
Goal: the screenshots that ship the product.

- [x] Landing page (instrument-panel aesthetic)
- [x] Recordings list (fetched from API)
- [x] Single-run trajectory inspector
- [x] Reliability surface panel (verdict + 4 dimensions)
- [x] **Trajectory canvas** — the branching flight-path hero (`TrajectoryCanvas`, wired to API)
- [x] Reliability surface heatmap (`ReliabilityHeatmap`)
- [x] Diff / regression view side-by-side (`/diff`)
- [x] Scenario library browser (`/scenarios`)
- [x] CI dashboard per PR (`/ci`, sparklines + history)
- [ ] 20-second terminal-to-dashboard demo gif (marketing asset — deferred)

## v0.7.0 — M7: Framework integrations ✅
- [x] `integrations/langgraph` (`wrap()` + `import_langgraph_otel`)
- [x] `integrations/openai_agents`
- [x] `integrations/crewai`
- [x] `volo_sdk.import_otel_trace` (JSONL / OTLP-JSON / bare-array) — the shared seam
- [ ] `integrations/raw` (manual instrumentation reference) — optional, not yet written

## v0.8.0 — M8: Cost-routing brain hardening ✅
- [x] `OllamaProvider` (sync HTTP)
- [x] `FrontierProvider` abstraction + `Budget` cap enforcement (the library-level hard cap)
- [x] `CachedProvider` content-addressed cache
- [x] Concrete HTTP client wired — free OpenAI-compatible (`OpenAICompatProvider`, Groq default; ADR-0011)
- [x] Cost / token visible in CLI output (`volo run` / `volo ci` cost summary)
- [x] Local-judge integration for faithfulness scoring (`--judge heuristic|ollama|groq`)

## v1.0.0 — M9: Production hardening + launch 🟨 (security review done)
- [x] Security review (redaction, sandbox, secrets) — `docs/security-review-2026-06-04.md`,
      ADR-0012. 2 CRITICAL + 1 HIGH + MEDIUMs fixed (RCE via source_hint, API path traversal,
      opt-in auth, file-read confinement, redaction patterns, artifact size cap).
- [x] Brand name decided (bible §2.4, ADR-0008) — Volo, locked.
- [ ] Docs site (deferred — deployment/§13)
- [ ] Landing page with the 20-second demo gif (deferred — marketing)
- [ ] Public OSS launch (deferred — §13)

## v1.1.0 — M10: MCP simulation 🟨 (record/replay + CLI + docs shipped)
Goal: deterministic record/replay of Model Context Protocol servers — agents that reach their
tools through MCP get offline, byte-identical integration tests (ADR-0014).

- [x] `volo-mcp` core: ndjson JSON-RPC framing, method→cache-key taxonomy, result/error envelope
- [x] `MCPRecorder` (auto `ToolSpec` harvest from `tools/list`) + `MCPReplayServer`
      (un-recorded input → JSON-RPC `-32042`, never hallucinate)
- [x] stdio transport: transparent recording proxy + replay serve-loop
- [x] `volo mcp record | serve` CLI, `examples/mcp_calc_server.py`, byte-faithful e2e test
- [x] Docs: README quickstart, docs-site guide, CLI reference

## v1.2.0 — M11: MCP fuzz + conformance ✅
Goal: adversarial testing at the MCP boundary — "what does my agent do when the server returns
garbage?" — plus a regression gate for MCP-server authors.

- [x] `volo_mcp.fuzz`: scenario operators applied inside the `{"result": ...}` envelope;
      handshake/meta steps and recorded protocol errors stay byte-intact; seeded/reproducible
- [x] `volo mcp fuzz` — one servable mutated recording per operator (resilience, robustness,
      security, order_sensitivity), `--serve` for a live hostile world, `--report` JSON
- [x] `volo_mcp.conformance` + `volo mcp conformance` — replay recorded requests against the
      LIVE server, diff answers (errors included), exit 1 on behavioral change

## v1.3.0 — M12: pytest plugin ✅
Goal: reliability tests as plain unit tests — Volo's engine behind pytest fixtures.

- [x] `pytest-volo` package, auto-registered via the `pytest11` entry point (ADR-0016)
- [x] `@pytest.mark.volo_recording(path, *, tier=1, fuzz=None, seed=0)` marker +
      `volo_recordings_dir` ini option
- [x] Fixtures: `volo_recording` (baseline), `volo_env` (Tier-1/2 sim, active for the test),
      `volo_scenario` (auto-parametrized over the scenario library; MCP recordings auto-select
      the fuzz library), `volo_run` (full scenarios → replay → score loop)
- [x] `assert_ship` / `assert_no_ship` helpers that attach the reliability surface on failure

## v1.4.0 — M13: production shadow + drift sentinel ✅
Goal: close the record→replay loop in production — every banked trace is a permanent
regression test, replayed nightly; drift pages you before your users notice.

- [x] `volo-shadow`: `CorpusBank` (indexed, content-digest deduplicated, redaction always runs
      before disk) + `pull` (OTel sampling via the M7 import seam) + `adopt` (incident → fixture)
- [x] Drift sentinel: `snapshot` (corpus × full scenario suite → reliability surface) +
      `compare` (dimension drop > threshold, or ship→no_ship flip ⇒ finding)
- [x] `volo shadow pull | adopt | list | check` — check exits 3 on drift (the alert), 2 on an
      empty corpus; `--report` / `--update-baseline` / `--threshold`
- [x] Nightly GitHub Action template (`examples/workflows/volo-nightly.yml`)
- [x] Acceptance: a seeded nondeterminism regression trips the alert (test-proven)
- [ ] M14: drift trends + dashboard screens + webhook/Slack alerting
