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

## App-Specific Guidance

See `apps/web/CLAUDE.md` for marketing site details.
