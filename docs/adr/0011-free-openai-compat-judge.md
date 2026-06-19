# ADR 0011: Free OpenAI-compatible judge backend (Groq default) over paid frontier

- **Status:** accepted
- **Date:** 2026-06-02
- **Deciders:** founder
- **Related:** bible §11 (cost-routing brain), ADR-0006 (reliability metrics),
  ADR-0009 (Tier-2 algorithm + flag-on-unknown invariant)

## Context

M8 (cost-routing brain) shipped the provider abstractions — `OllamaProvider`,
`FrontierProvider`, `CachedProvider`, `Budget` — plus the optional LLM-judge layer
(`HeuristicJudge` / `OllamaJudge` / `FrontierJudge`). The remaining gap was that
`FrontierJudge` had **no concrete `_inner` HTTP client**: the abstraction enforced opt-in and
budget but could not actually talk to a model.

The original plan was to wire **Anthropic** as the first concrete frontier client. The founder
redirected: the judge should run against a **free** API so that exercising it (locally and in
demos) costs nothing on anyone's account. Anthropic — and any paid frontier — is explicitly
out of scope for this wiring.

## Decision

Wire one **generic OpenAI-compatible client**, not a vendor-specific one.

1. **`OpenAICompatProvider`** (`volo-models`) — a stdlib-`urllib` wrapper (zero new runtime
   deps, same discipline as `OllamaProvider`) over `POST {base_url}/chat/completions`. Groq,
   Google Gemini, OpenRouter and xAI all expose this surface, so a single client targets any
   of them via a `preset=` selector (`PRESETS` table) or direct `base_url` / `model` /
   `key_env` overrides. **Default preset: Groq** (`llama-3.3-70b-versatile`), whose free tier
   is the intended judge backend. `xai` is in the table for completeness but its API is paid —
   selecting it is a deliberate cost choice.

2. **Gating** (founder decision): even though the configured backends are free, a live call
   still requires an explicit opt-in, `VOLO_OPENAI_COMPAT_OPT_IN=true`, plus a resolvable API
   key (`$GROQ_API_KEY` by default). This keeps CI from ever making a surprise network call.
   Cost is modelled as **`$0.00`**, so — unlike `FrontierProvider` — **no `Budget` is
   required**. The paid `FrontierProvider` gate (`VOLO_FRONTIER_OPT_IN` + `Budget`) is
   untouched and remains the only place that can spend real money.

3. **`OpenAICompatJudge`** (`volo-reliability`) — mirrors `OllamaJudge`: lazily constructs the
   provider, falls back to `HeuristicJudge` on any error or unparseable output, so the judge
   never blocks a run. `default_judge()` gains a `VOLO_OPENAI_COMPAT_JUDGE=true` flag, checked
   ahead of the Ollama flag. Paid frontier judges are still never returned implicitly.

4. **Cost-free tests.** The provider takes a `transport` seam; the suite replays a recorded
   Groq-shaped response fixture (`tests/fixtures/groq_chat_completion.json`) so CI is
   deterministic and offline. A `CachedProvider` round-trip test demonstrates the
   record-once / replay-many story end to end.

## Consequences

- The judge is now usable for real on a free account, with no cost surface and no surprise
  network calls in CI.
- Switching backends (Groq → Gemini → OpenRouter) is config, not code.
- `FrontierJudge`'s missing `_inner` is no longer the blocking M8 debt — though wiring a real
  paid frontier client (Anthropic/OpenAI) is still available behind its existing gate if a
  user opts in.
- The three LLM-backed judges now share a single `_score_from_response` helper, so the
  text→JSON→clamp parse contract lives in one place.
