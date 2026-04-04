# CLAUDE.md

## Monorepo Structure

This is a Turborepo monorepo for the NicheFinder/Widby project.

```
apps/
  web/     — Marketing landing page (Next.js 16, deployed as "whidby" on Vercel)
  app/     — Product app (coming soon)
packages/
  (none yet)
```

## Commands

```bash
npm run dev          # Dev all apps
npm run build        # Build all apps
npm run dev:web      # Dev marketing site only (port 3000)
npm run dev:app      # Dev product app only (port 3001)
```

## Python Scoring Engine

The niche scoring and outreach engine lives in `src/` (Python 3.11+). See `.cursor/agents.md` for full module specs, build order, and TDD workflow.

```bash
pytest tests/unit/ -v              # Unit tests (no network)
pytest tests/integration/ -v -m integration  # Integration tests (requires API keys)
```

## App-Specific Guidance

See `apps/web/CLAUDE.md` for marketing site details.
