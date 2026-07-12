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

## v1.5.0 — M14: drift trends + dashboard + alerting ✅
Goal: the sentinel's memory — reliability over time, visible and loud.

- [x] `SnapshotHistory` (append-only JSONL; every `shadow check` appends snapshot + drift verdict)
      with fleet-average and per-trace trend series (ADR-0018)
- [x] `volo shadow trend` — ASCII sparkline per dimension; `--trace` follows one banked trace
- [x] Webhook alerting on `shadow check` (`--webhook` / `VOLO_SHADOW_WEBHOOK`) — Slack-compatible
      payload, best-effort delivery (never masks the exit-3 alert)
- [x] API: `GET /shadow/history` (+ per-trace) — the trend feed
- [x] Dashboard: `/shadow` screen — fleet-average sparklines per dimension, drifted-night chips,
      banked-corpus table (bible §8.3 aesthetic, reuses the CI sparkline)

## v1.6.0 — M15: red-team corpus + safety annex ✅
Goal: probe agents for injection/exfil/jailbreak vulnerability — safely, in the sim.

- [x] `volo-redteam`: `Attack` model (canary-based poison + detect), 54-attack built-in corpus
      across 6 classes (prompt_injection, tool_poisoning, data_exfil, jailbreak,
      confused_deputy, pii_bait), JSON attack packs (`load_pack`/`dump_pack`) — ADR-0019
- [x] `run_redteam` → `SafetyAnnex` (safe/vulnerable verdict, per-class counts, findings with
      evidence); poison + replay run entirely in the Tier-1 sim (no live calls)
- [x] `volo redteam run|list|export` — run exits 4 when any attack lands (CI safety gate)
- [x] `examples/vulnerable_agent.py` — naive (fails) vs guarded (passes) side-by-side

## v1.7.0 — M16: model-migration lab ✅
Goal: "will my agent survive the next model?" — reliability + cost delta across a model swap.

- [x] `volo-migrate`: pair two corpora by stem (`pair_corpora`), model-agnostic tool-path
      signature, per-pair `evaluate_pair` (tool-path / output / faithfulness / cost) — ADR-0020
- [x] `MigrationReport` → recommendation `recommend` / `review` / `block`; projected cost delta
      from `volo_models.pricing` (promoted to a public module, shared with `FrontierProvider`)
- [x] `volo migrate <baseline> <candidate> --from --to [--judge] [--out]` — exit 5 on block

## v1.8.0 — M17: simulated users & counterparties ✅
Goal: test multi-turn agents deterministically — a seeded persona answers the agent's questions.

- [x] `volo-personas`: `Persona` (facts → script → default resolution, JSON packs),
      `SimulatedUser`, `PersonaEnvironment` (wraps the sim, intercepts ask_user tools) — ADR-0021
- [x] `drive_persona` → `ConversationReport` (transcript + goal_met via `expected` markers)
- [x] `volo persona run|list|export` — `--require-goal` exits 6 on unmet goal
- [x] `examples/clarifying_agent.py` — a runnable multi-turn agent

## v1.9.0 — M18: long-horizon rig ✅
Goal: surface memory drift / context rot / accumulation — the failure class too expensive to
test live, a for-loop in the sim.

- [x] `volo-longhorizon`: `run_long_horizon` replays a task N times threading memory forward,
      re-scoring each episode; deterministic (Tier-1 replay) — ADR-0022
- [x] Longitudinal dimensions on top of DFAH: `stability`, `output_consistency`,
      `faithfulness_slope`, `first_degraded_episode`; verdict `stable` / `degrades`
- [x] `volo horizon <recording> --agent -n N` — faithfulness sparkline; exit 7 on degrade
- [x] `examples/drifting_agent.py` — `stable` (holds) vs `drifting` (context rot at a threshold)

## v2.0.0 — M19: hardening (closes wave 2) ✅
Goal: perf pass, recording-format v2, docs overhaul — tag v2.0.0.

- [x] Perf pass: `benchmarks/replay_throughput.py` + throughput guard test (floor 10k steps/min;
      measured ≫ 5M steps/min — no optimization needed) — ADR-0023
- [x] Recording persistence v2: gzip-aware `save_recording`/`load_recording`, cheap
      `recording_header`, `RecorderConfig.compress`; schema-migration seam (`register_migration`,
      `load_recording` upgrades before validating) — schema stays additive at 1.0.0 (ADR-0023)
- [x] Docs overhaul: ARCHITECTURE.md gains the expansion-packages map (§2a) + persistence note;
      distinct gate exit codes documented
- [x] Tag v2.0.0

**Wave 2 (v1.1 → v2.0) complete.**

## v2.1.0 — M20: pack format + `volo pack` ✅ (wave 3 opens)
Goal: turn adversarial content into versioned, checksummed, shareable bundles — the marketplace
inventory.

- [x] `volo-packs`: `Pack` (manifest + items), semver + content-checksum, per-kind item
      validation (attacks / personas / scenarios) — ADR-0024
- [x] `PackStore` — local install dir + index, dedupe by `name@version`, tamper-safe install
- [x] `volo pack init|validate|install|list` — `init` seeds from built-ins; `validate` exit 1 on
      bad checksum/schema
- [x] M21: git-backed registry index (publish / install-by-name; $0 infra) — ADR-0025

## v2.3.0 — M22: framework adapters v2 ✅
Goal: extend M7's `wrap()` + OTel-import pattern to three more frameworks.

- [x] `integrations/autogen` (`volo-autogen`) — v0.4 `model_client` + legacy `llm`
- [x] `integrations/pydantic_ai` (`volo-pydantic-ai`) — `agent.model` + `run_sync`
- [x] `integrations/semantic_kernel` (`volo-semantic-kernel`) — `kernel.services` + `invoke`
- [x] Each: `wrap()` (proxy swap + decision step) + `import_*_otel()`; fake-based tests (ADR-0026)
- [ ] M23 VS Code (deferred — editor/JS surface)

## v3.0.0 — M25: marketplace GA (closes wave 3) ✅
Goal: verified publishers — pack signing + a curated public seed registry.

- [x] `volo_packs.signing`: HMAC-SHA256 publisher signatures binding `name@version` + checksum;
      `Keyring` verification — ADR-0028 (Ed25519 upgrade documented as next)
- [x] `volo pack sign` / `verify`; `--keyring` + `--require-signed` on install
- [x] Registry `verified` flag + publisher; `install_from_registry` verifies signatures
- [x] Seed public registry `registry/` (built-in attacks/personas/scenarios packs + index)
- [x] Tag v3.0.0

**Wave 3 (v2.1 → v3.0) complete.**

## v3.1.0 — M29: compliance evidence packs ✅ (wave 4, OSS-first)
Goal: turn Volo's reports into signed, deterministic audit evidence mapped to control frameworks.

- [x] `volo-compliance`: control catalog (EU AI Act / ISO 42001 / SOC 2) + `build_evidence_pack`
      evaluating each control against reliability / red-team / drift evidence — ADR-0029
- [x] `EvidencePack` — reproducible content checksum (excludes timestamp) + optional HMAC
      signature (`sign_evidence` / `verify_evidence`); Markdown + self-contained HTML report
- [x] `volo compliance build|verify` — `--require-satisfied` exits 8; `verify` exit 1 on
      checksum/signature failure

## v3.2.0 — M28: PR-check GitHub Action ✅ (wave 4, OSS-first)
Goal: reliability (+ compliance) gate on every PR — entirely in the user's CI, no hosting.

- [x] `volo comment` — sticky PR-comment Markdown (reliability + optional compliance), hidden
      marker for update-not-spam; UTF-8-safe stdout — ADR-0030
- [x] Composite Action `.github/actions/volo-pr-check/action.yml` — runs `volo ci`, optional
      `volo compliance build`, posts/updates the sticky comment via `gh` + `GITHUB_TOKEN`, fails
      the check on regression. No third-party action, no secrets.
- [x] Workflow template `examples/workflows/volo-pr-check.yml`

## v3.3.0 — M26: cloud control plane MVP ✅ (commercial)
Goal: the first paid tier — hosted teams / workspaces / report history over the OSS engine.

- [x] Commercial `cloud/` dir (`volo-cloud`, own LICENSE — NOT Apache-2.0; ADR-0001/0031)
- [x] Teams, workspaces, membership, API keys (sha256-hashed, shown once), workspace report
      history — SQLite locally / Postgres via `VOLO_DB_URL`, no new dependency
- [x] FastAPI: `/cloud/teams`, `/workspaces`, `/keys` (management via `require_principal` seam) +
      `X-Volo-Key`-gated `/workspaces/{id}/reports` scoped to the key's workspace

## v3.4.0 — M23: VS Code extension ✅ (OSS)
Goal: inspect + replay recordings without leaving the editor.

- [x] `apps/vscode` — "Volo: Open Trajectory View" (webview flight-path of a recording) +
      "Volo: Replay Recording" (`volo sim` in a terminal) — ADR-0032
- [x] Pure `trajectory.ts` (parse) + `webview.ts` (render, HTML-escaped) — no `vscode` import,
      8 vitest tests; thin `extension.ts` glue; `tsc` typecheck clean

## v3.5.0 — M27: hosted Tier-2 sim-minutes ✅ (commercial)
Goal: resell simulation compute — a metered, hard-capped job queue over the M26 control plane.

- [x] `SimJob` queue + `SimQuota` (per-workspace hard cap) in `cloud/`; DB-backed (SQLite/Postgres)
- [x] `volo-cloud-worker` — claims a job, runs the reliability suite, meters wall-clock as
      sim-minutes, charges the quota, stores the report into workspace history — ADR-0033
- [x] Enqueue 402 when quota exhausted; agent execution gated by `VOLO_SIM_AGENT_ALLOWLIST`
      (safe-by-default, ADR-0012 posture)
- [x] Endpoints `POST/GET /cloud/workspaces/{id}/sim-jobs`, `/quota`

## v3.6.0 — M30: RBAC / SSO / audit ✅ (commercial)
- [x] Team roles (owner>admin>member) enforced on management mutations; owner-only role grants
- [x] Vendor-neutral SSO — HS256 bearer-JWT verify (stdlib), any provider via `VOLO_JWT_*`;
      RS256/JWKS documented as the crypto-dep upgrade — ADR-0035
- [x] Append-only `AuditEvent` on every mutation; `GET /cloud/teams/{id}/audit`

## v3.7.0 — M31: computer-use record/replay ✅ (OSS, frontier)
Goal: the simulator's next surface after MCP — browser/desktop agents.

- [x] `volo-computeruse`: `ActionEvent` (kind/target/value/**screenshot hash**) keyed on UI state;
      events map onto the Recording as `cu.<kind>` tool calls — ADR-0034
- [x] `ComputerUseRecorder` + `ComputerUseReplayServer` (flag on unseen (action, screen), never
      fabricate UI); `volo cu inspect|replay`

## v3.8.0 — M32: multi-agent system testing ✅ (OSS, frontier)
Goal: test an orchestrator as a system — simulate its sub-agents, verdict the whole interaction.

- [x] `volo-multiagent`: `MultiAgentEnvironment` intercepts delegation tools
      (`delegate`/`call_agent`/`handoff`, `agent.<name>`) → routes to persona counterparties (M17) — ADR-0036
- [x] `run_multiagent` → `SystemReport` (reached / unreached / unknown-agent / message graph +
      healthy/broken verdict); `volo multiagent run` exits 9 on broken
- [x] `examples/orchestrator_agent.py` (delegates to researcher + writer)

## v3.9.0 — M33: Volo Certified ✅ (OSS, frontier)
Goal: a public, signed pass/fail credential — the "UL of agents".

- [x] `volo-certify`: `certify()` composes reliability (M4) + red-team (M15); Volo Score = mean of
      the four reliability dims x100; `CertCriteria` (require_safe + min score, opt-in require_ship) — ADR-0037
- [x] Signed, checksummed `Certificate` (HMAC, same scheme as packs/evidence) + SVG/markdown badge
- [x] `volo certify run|verify|badge` (run exits 10 if not certified)

## v5.0.0 — M34: the capstone ✅ (release)
Goal: prove the whole charter composes — one recording through every gate — and tag v5.0.

- [x] `tests/test_full_pipeline_v5.py` — one baseline flows record → reliability → red-team →
      certify (signed) → evidence pack (signed) → cloud ingest; a second test proves the pipeline
      *denies* a vulnerable agent — ADR-0038
- [x] README refreshed: full-pipeline diagram, accurate package inventory, open-core license note
- [x] **v1.1 → v5.0 charter complete.** All pillars P1–P10, milestones M1–M34 shipped.

## v5.1.0 — post-v5.0 hardening ✅ (deploy release, 2026-07-13)
All shipped and merged to `main` (565 tests, 0 warnings):
- [x] Ed25519 asymmetric signing for packs / evidence / certificates (#5)
- [x] RS256 / JWKS SSO for the cloud plane (#6)
- [x] Hosted-deploy artifacts (Dockerfiles + fly.toml) for the sim-minutes API + worker (#7)
- [x] Live Playwright computer-use driver (#8)
- [x] Fixes: pack-signature content binding — **security** (#16), CLI cp1252 `--help` crash (#18),
      JWT `exp` required (#20), reliability/security test gaps (#19), httpx2 (#21), package-manager
      alignment (#22)
- [x] `docs/DEPLOY.md` deploy runbook
- [ ] **Open (design decision):** #10 — `ambiguous_user_turn` / `inject_latency` operators are
      inert (false verdicts); fixing changes what the reliability suite measures.

## v2.4.0 — M24: public reliability leaderboard ✅
Goal: one **Volo Score** per agent — the credibility/dataset engine, deterministic and static.

- [x] `benchmarks/leaderboard.py`: record each example agent → run the scenario suite → rank by
      Volo Score (50% clean correctness + 50% adversarial robustness) — ADR-0027
- [x] Renders `leaderboard.{json,md,html}` (self-contained static site, $0 infra)
- [x] `examples/flaky_agent.py` (nondeterministic) proves the score discriminates reliable from
      unreliable agents (91/88 stable vs 21 flaky)
- [x] Weekly-rebuild GitHub Action template (`examples/workflows/volo-leaderboard.yml`)

## v2.2.0 — M21: git-backed pack registry ✅
Goal: publish/install packs by name with no registry service — a JSON index in a git repo.

- [x] `volo_packs.registry`: `RegistryIndex` (name → versions → {url, checksum, n_items}),
      `register`/`resolve` (latest by semver), `install_from_registry` (checksum-verified) — ADR-0025
- [x] Sources are http(s) / file:// / local path (stdlib urllib; $0 infra)
- [x] `volo pack publish` (add to index), `volo pack install <name> --registry` (by name),
      `volo pack search` (list a registry)
- [ ] M22 adapters v2 · M23 VS Code · M24 public leaderboard · M25 marketplace GA
