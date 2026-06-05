# Volo Dashboard

Next.js (App Router) + Tailwind, dark-first instrument-panel aesthetic (bible §8 /
[`docs/DESIGN_SYSTEM.md`](../../docs/DESIGN_SYSTEM.md)).

## Local dev

```bash
# from repo root
corepack enable pnpm    # one-time
pnpm install
pnpm --filter web dev
# → http://localhost:3000
```

## Status

Pre-alpha scaffold. The landing page renders the design tokens for visual review; the
**trajectory canvas** hero (bible §8.3) ships in milestone M6. See
[`docs/STATUS.md`](../../docs/STATUS.md) for the live ledger.
