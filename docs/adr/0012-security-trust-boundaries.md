# ADR 0012: Security trust boundaries — untrusted recordings, path containment, opt-in auth

- **Status:** accepted
- **Date:** 2026-06-04
- **Deciders:** founder
- **Related:** bible §7.5 (security & safety), ADR-0003 (recording format),
  ADR-0009/0010 (Tier-2 source-informed synthesis), ADR-0004 (proxy capture)

## Context

The M9 security review audited Volo against the bible §7.5 mandate ("redaction in the SDK,
sandbox tool execution, never log API keys/secrets") plus general appsec. Two findings were
**CRITICAL** and share a root cause: **a Recording is untrusted input.** The whole product
premise is "record once, *share/download*, replay" — so a recording (and the `tool_specs` /
`source_hint` it carries) can be attacker-authored, and so can the path/id parameters hitting
the dashboard API.

The review found:

1. **RCE via `source_hint` (CRITICAL).** Tier-2's `SourceInformedSynthesizer` resolved a
   `python:module.path:attr` hint by `importlib.import_module` + **calling** the attr — and it
   was wired into the default Tier-2 chain. Opening an untrusted recording under a Tier-2
   environment executed attacker-named code. The §7.5 "sandbox tool execution" mandate was not
   met.
2. **Arbitrary file read via `fixture:` / `openapi:` hints (MEDIUM→part of the same surface).**
   Those resolvers read any path (`fixture:/etc/passwd`, `openapi:../../secrets.json`).
3. **Path traversal in the API (CRITICAL, verified exploitable).** `/diffs/{stem}`,
   `_recording_path`, `_report_path` joined the raw id into a filesystem path; on Windows
   `..%5C..%5C` escaped the data dir and returned any `.json` on the host.
4. **No auth enforcement (HIGH).** Every route resolved an anonymous principal and never
   checked it; the DB-writing POSTs were open.

## Decision

Establish explicit trust boundaries rather than trusting recording-derived data:

1. **`source_hint` is untrusted by default.** `SourceInformedSynthesizer` gains
   `trust_source_hints: bool = False` and an optional `base_dir`.
   - `python:` resolution runs **only** when `trust_source_hints=True` (recordings you
     authored locally). Otherwise it abstains (`miss_python_untrusted`) — never imports/calls.
   - `fixture:` / `openapi:` file reads run when trusted (any path) or, when untrusted, only
     if confined within `base_dir` (relative paths, resolved, `..`/symlink escapes refused).
     With no `base_dir` and no trust, file hints abstain entirely.
   - `Tier2Replayer` defaults the flag from `VOLO_TRUST_SOURCE_HINTS` (false), so the
     parameterless `from_recording` path is safe. Trusted local workflows (e.g. the fidelity
     benchmark on our own `research_agent`) opt in explicitly.

2. **Path containment in the API.** `_safe_data_path(subdir, name)` rejects separators, `..`,
   colon/drive markers, null bytes, and absolute paths, then verifies the *resolved* path is
   contained in the subdir. Applied to recording/report/diff lookups.

3. **Opt-in auth enforcement.** `require_principal` denies anonymous callers with 401 when
   `VOLO_REQUIRE_AUTH=true`; state-mutating POSTs depend on it. OSS local default stays open
   (no setup); any non-localhost deployment sets the flag and swaps `get_principal`.

4. **Defence in depth.** Redaction default-deny posture reinforced: `RecordingRow.redaction_
   applied` defaults to `False` (claim redaction only when a writer sets it); the redaction
   denylist gains Google/Slack/Stripe/JWT patterns; the API caps per-artifact reads
   (`VOLO_MAX_ARTIFACT_BYTES`, default 32 MiB) to blunt memory-exhaustion via SSE/diff.

## Consequences

- Opening an untrusted recording can no longer execute code or read arbitrary files; the
  §7.5 "sandbox" mandate is met by *refusing* the dangerous resolvers unless trusted.
- **Behaviour change:** Tier-2 source-informed synthesis is OFF by default. Local users who
  rely on `python:` shadows set `VOLO_TRUST_SOURCE_HINTS=true` (or pass `trust_source_hints=
  True`). The fidelity benchmark sets it, so the 100% number is unchanged for the trusted case.
- The API is safe to expose with `VOLO_REQUIRE_AUTH=true` + a real `get_principal`; OSS local
  use is unchanged.
- Residual / follow-ups (documented in the review): redaction remains a denylist (prose
  secrets can slip), `resolve_agent` still prepends CWD to `sys.path` (operator-trust), and
  `simulated_cost_usd` plumbing is unrelated. These are tracked, not fixed here.
