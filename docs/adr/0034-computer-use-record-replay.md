# ADR 0034: computer-use actions key on the screenshot hash and map onto the Recording as tool calls

- Status: accepted
- Date: 2026-07-08

## Context

M31 (newplan P8, the simulator's frontier after MCP) records and replays computer-use agents —
ones that click, type, and navigate a UI. Unlike a tool call, a UI action's outcome depends on the
*screen it ran in*; replaying "click #buy" must reproduce the recorded result only when the screen
matches, and must not invent a UI state it never saw.

## Decision

1. **An action's identity includes the UI state.** An `ActionEvent` is
   `(kind, target, value, screen)` where `screen` is a `screenshot_hash` (sha256 of the
   screenshot/DOM). The cache identity is `("cu.<kind>", {target, value, screen})`, so the same
   click on a different screen is a *different* event that replays differently (or flags).
2. **Events are ordinary `tool_call` steps.** `ComputerUseRecorder` writes each action as a
   `cu.<kind>` tool call onto the standard Recording (framework `computer_use`), so the entire
   simulator/scenario/reliability/diff stack applies unchanged — the same reuse MCP got in
   ADR-0014. No new step type, no schema churn.
3. **Flag on unseen, never fabricate.** `ComputerUseReplayServer` is backed by any
   `SimulatedEnvironment` (Tier-1 by default); a seen (action, screen) replays its recorded
   `{result, screen_after}`, and an unseen one returns `{"__flagged__": …}` — the ADR-0009
   invariant, now for pixels. A future Tier-2 could synthesize UI responses under the same
   validate-or-abstain contract.
4. **Transport-free core now; a driver later.** The package ships the recorder + replay + schema
   and a `volo cu inspect|replay` CLI (replay serves outcomes for action events read from stdin).
   A real driver (Playwright / pyautogui) that *feeds* the recorder from a live browser/desktop is
   the follow-up, mirroring how MCP shipped its cores before the stdio transport.

## Consequences

- Because actions are keyed on the screenshot hash, replay fidelity is exactly as good as the
  screen fingerprint: an identical DOM/screenshot → a hit; any pixel/DOM difference → a flag. That
  is deliberately strict (no silent drift), and the hash function can be swapped (e.g. perceptual
  hashing) without touching the schema.
- Reusing `tool_call` means computer-use recordings are diffable, fuzzable, and scorable like any
  other — a computer-use agent gets the whole platform for free.
- The `screen` is the pre-action state and `screen_after` the outcome, so a chain of actions
  threads screen → screen_after → next screen; a recorded session replays step-for-step when the
  agent revisits the same screens.

## Alternatives considered

- **A dedicated `action` step type** in the Recording schema — rejected: schema-version churn and
  every downstream tool would need to learn it; the `(tool, request)` mapping loses nothing
  (same reasoning as ADR-0014).
- **Key only on (kind, target)**, ignoring the screen — rejected: replays the wrong outcome when
  the same control does different things on different screens; UI state is the whole point.
- **Store raw screenshots in the recording** — rejected for the core: huge and non-diffable; a
  hash is enough for replay identity, and a driver can keep artifacts out-of-band.
