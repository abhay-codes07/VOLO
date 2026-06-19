# ADR 0009: Tier-2 simulator algorithm — hybrid synthesis with flag-on-unknown

- **Status:** accepted
- **Date:** 2026-05-31
- **Deciders:** founder
- **Related:** bible §9.2, ADR-0003 (recording format), ADR-0004 (proxy capture),
  ADR-0006 (reliability metrics)

## Context

The bible (§9.2) splits the simulator into two tiers:

- **Tier 1** — deterministic cache-replay from the recording. Shipped in M1 as
  `volo_simulator.Tier1Replayer`. Covers only inputs that appeared in the recording.
- **Tier 2** — high-fidelity synthesis for *un-recorded* inputs. The MIRAGE research line
  showed naive cache-replay hits ~62% fidelity while source-informed synthesis hits ~99%.
  Closing that gap is the central technical wedge for Volo.

We need to ship Tier-2 value early without committing to the most ambitious version on day
one — and without ever letting the simulator silently hallucinate a tool response that the
agent will then treat as ground truth.

## Decision

Tier-2 is a **hybrid** of three strategies, applied in a strict order at synthesis time, with
a hard invariant on the tail:

1. **(a) Constrained local-model generation.** When asked for a tool response on an unseen
   input, call the local Ollama judge with a constrained-decoding prompt that pins the
   response shape to `ToolSpec.output_schema` (JSON Schema). The model is seeded by the runner
   so synthesis is reproducible across runs. If the model produces a value that validates,
   return it. **This ships in M5.**
2. **(b) Source-/spec-informed synthesis.** When the tool has a `ToolSpec.source_hint`
   (a function reference, an OpenAPI URL, or an inline Python signature), Tier-2 tries to
   derive a faithful response by static inspection or evaluating a pure-function shadow
   *before* falling back to (a). This is the path that closes the 62 → 99% fidelity gap.
   **This is a follow-up in M5.1 — the seam is reserved now.**
3. **(c) Flag-on-unknown sentinel.** If neither (a) nor (b) can produce a schema-validated
   response, Tier-2 raises `Tier2Miss(UnknownInput)`. The runner records the miss as a
   `step.payload.synthesis = "flagged"` annotation and continues. **The simulator never
   hallucinates** — this invariant is load-bearing.

### Resolution order at runtime

```
seen in recording?  → cache hit  (Tier-1)
       ↓ no
has source_hint?    → source-informed synth (Tier-2 b — M5.1+)
       ↓ no / can't
local Ollama?       → constrained-generation synth (Tier-2 a — M5)
       ↓ no / can't
                      raise Tier2Miss → step.synthesis = "flagged"
```

### Ship order

Implementation lands in two passes so we shipping Tier-2 value before the harder source-
informed path is ready:

- **M5:** ship (a) + (c). Tier-2 produces synthesized responses for any tool with an
  `output_schema`. Without a schema, the simulator flags. Fidelity target ≥ 75% on the
  `examples/research_agent` benchmark.
- **M5.1:** ship (b) on top. Switch resolution order to try source-informed first. Fidelity
  target ≥ 95%.

### Public surface

```python
class Tier2Synthesizer(Protocol):
    def synthesize(self, kind: Literal["model_call", "tool_call"], *,
                   provider: str, model: str, tool: str, request: dict,
                   spec: ToolSpec | None) -> dict | None:
        """Return a validated response, or None to signal a miss."""

class Tier2Replayer(SimulatedEnvironment):
    """Chains Tier-1 cache → Tier-2 synth → Tier2Miss."""
```

`Tier2Miss` subclasses `LookupError` (same parent as `ReplayMiss`) so existing runner code
that catches misses keeps working.

### Fidelity target

- **Lower floor (the bible §9.2 benchmark to beat):** 62% (naive cache-replay).
- **M5 target (Tier-2 a only):** ≥ 75% on `examples/research_agent`.
- **M5.1 target (Tier-2 a + b):** ≥ 95%.
- **Stretch / parity with research:** 99%, gated on tool-spec completeness.

Fidelity is measured as the fraction of un-recorded tool calls for which the synthesized
response, fed back into the agent, produces a final output within ε of the live-mode result.
The benchmark methodology gets its own follow-up ADR once we have numbers.

## Consequences

- **Easy:** (a) is cheap to ship — `volo-models.OllamaProvider` already exists; we only need
  a constrained-JSON wrapper + schema validation.
- **Easy:** the flag-on-unknown invariant is enforced at one point (`Tier2Replayer.call`) and
  is independently testable.
- **Hard:** without source hints, the (a)-only path will miss on truly novel structures. The
  honest answer is "flag it" rather than fake confidence.
- **Hard:** Tier-2 needs Ollama running locally. CI workflows that don't have Ollama fall back
  to Tier-1 (current behavior); the `volo-selfcheck.yml` workflow stays Tier-1 until we add
  Ollama provisioning to the runner. Tier-2 tests run on the dev box only at first.
- **Locked in:** the *never hallucinate* invariant. Any future "be permissive" mode requires a
  new ADR that supersedes this one.

## Cost-control alignment

Tier-2 (a) uses local Ollama by default → $0 marginal. Frontier APIs are an opt-in fallback
**only** under the per-project `VOLO_FRONTIER_OPT_IN=true` + `Budget` cap defined in
`volo-models.Budget`. The headline "$0 in CI" promise survives.

## Alternatives considered

- **(a) only, never source-informed.** Cheaper, ships faster, but caps fidelity around
  ~75–85%. We commit to (b) as a follow-up rather than dropping it.
- **(b) only, never local-model.** Faithful but brittle: every tool needs a complete spec,
  and tools without OpenAPI or pure-Python shadows would always flag. Less product value early.
- **Permissive fallback (free-form text synthesis).** Hallucinates. Rejected at the invariant
  layer.
- **A frontier-model judge for synthesis.** Possible later behind opt-in + cap, but Tier-2
  default has to be free. Not in M5 scope.
