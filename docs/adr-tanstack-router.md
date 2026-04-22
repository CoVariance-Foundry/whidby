# ADR: TanStack Router vs Next.js App Router

**Status:** Decided — stay on Next.js App Router  
**Date:** 2026-04-21  
**Applies to:** `apps/app`, `apps/admin`, `apps/web`

## Context

As part of the TanStack monorepo adoption (Query, Table, Form), we evaluated
whether to also adopt TanStack Router and replace Next.js App Router.

## Decision

**Stay on Next.js App Router.** Do not adopt TanStack Router at this time.

## Rationale

### Against TanStack Router

1. **Next.js is the deployment platform.** Both apps deploy on Vercel as
   Next.js projects. Replacing the routing layer would mean either ejecting from
   Next.js entirely or running TanStack Router as a client-side SPA router
   inside a single Next.js catch-all route — losing SSR, RSC, incremental static
   regeneration, and Vercel's built-in optimizations.

2. **Auth guard depends on server routing.** The `proxy.ts` middleware and
   `(protected)/layout.tsx` server component both use `getUser()` to gate
   access before any client code runs. TanStack Router is client-only; we would
   need to rebuild auth checking as client-side redirects, introducing flash-of-
   unauthorized-content.

3. **SSR data loading is already working.** The reports list (`reports/page.tsx`)
   and dashboard home load data server-side via RSC and pass it as props to
   client components. TanStack Router's `loader` pattern solves the same problem
   but only on the client, which would regress performance for initial page loads.

4. **Migration cost is disproportionate.** Estimated 6–10+ weeks of work for a
   lateral move: restructuring all route files, recreating layout nesting,
   reimplementing middleware, and reworking the build pipeline. The UX benefit
   is marginal — TanStack Query already provides the cross-navigation state
   persistence that motivated the original discussion.

### For TanStack Router (acknowledged but outweighed)

- Type-safe route params and search params.
- Co-located loaders and route-level error boundaries.
- Tighter integration with TanStack Query via route loaders.

These are real benefits, but they don't justify the migration cost given the
current Next.js foundation.

## Re-evaluation Triggers

Revisit this decision if:

- The project moves off Vercel / Next.js for other reasons.
- A significant new app surface is being built from scratch (greenfield).
- TanStack Start (the full-stack framework) reaches production stability and
  offers SSR parity with Next.js.

## Related

- `docs/tanstack-migration-audit.md` — baseline fetch/state audit
- TanStack Query, Table, and Form adoption completed in this same cycle
