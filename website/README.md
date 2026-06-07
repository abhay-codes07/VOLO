# Volo docs site

[Mintlify](https://mintlify.com) docs. Content is MDX; `docs.json` is the config.

## Preview locally

```bash
npm i -g mint        # the Mintlify CLI
cd website
mint dev             # http://localhost:3000
```

## Deploy (free for open source)

1. Install the [Mintlify GitHub App](https://mintlify.com) on the `VOLO` repo.
2. Set the docs directory to `website/`.
3. Pushes to `main` auto-deploy. Point a custom domain (e.g. `docs.volo.dev`) when ready.

## Structure

| File | Page |
|---|---|
| `index.mdx` | Introduction |
| `quickstart.mdx` | Quickstart |
| `concepts.mdx` | Core concepts |
| `ci.mdx` | Gate PRs in CI |
| `fidelity.mdx` | Fidelity benchmark |
| `cli.mdx` | CLI reference |

Add a `favicon.svg` and a `/logo` (light/dark) to `website/` before launch.
