# Implementation Plan: Magic-Link Callback Lands on Dashboard, Not Marketing Site

**Date**: 2026-04-17 | **Owner**: antwoine@covariance.studio

## Problem

Signing in via magic link from the Dev Suite login ([apps/app/src/app/login/page.tsx](../../apps/app/src/app/login/page.tsx)) redirects the user to the marketing site (`apps/web`, production URL `https://whidby-covariance-projects.vercel.app/`) instead of the dashboard `/auth/callback` route at `apps/app`. The session never reaches the dashboard, so the user appears unauthenticated on `http://localhost:3001`.

## Root Cause

The dashboard login passes the correct `emailRedirectTo` (falls back to `window.location.origin` when `NEXT_PUBLIC_APP_FRONTEND_URL` is unset — locally that's `http://localhost:3001/auth/callback?next=/`).

Supabase drops that redirect and falls back to Site URL because the current allowlist only matches the marketing app's Vercel URL. Values fetched via `GET /v1/projects/eoajvifhbmqmoluiokcj/config/auth`:

```
site_url:        https://whidby-covariance-projects.vercel.app/
uri_allow_list:  https://whidby-covariance-projects.vercel.app/,
                 https://whidby-covariance-projects.vercel.app/**,
                 https://whidby-*-covariance-projects.vercel.app,
                 https://whidby-*-covariance-projects.vercel.app/**
```

Neither the local dashboard origin (`http://localhost:3001`) nor the prod dashboard host (`https://app.thewidby.com`) is allowlisted, so Supabase always resolves to the marketing Site URL.

## Change

`PATCH https://api.supabase.com/v1/projects/eoajvifhbmqmoluiokcj/config/auth`

- `site_url` → `https://app.thewidby.com` (prod dashboard is the correct default)
- `uri_allow_list` → append the dashboard patterns:
  - `http://localhost:3001/**` (local dev)
  - `https://app.thewidby.com/**` (prod dashboard)
  - `https://nichefinder-app-*-covariance-projects.vercel.app/**` (dashboard preview deploys)
  - keep existing marketing entries for any legacy flows that still rely on them

## Verification

1. Confirm config via `GET /config/auth` — site_url and uri_allow_list updated
2. From `http://localhost:3001/login`, submit magic link for `antwoine@covariance.studio`
3. Click the link → land on `http://localhost:3001/auth/callback?code=…` → exchange → redirected to `/`
4. Dashboard renders an authenticated session (no redirect back to `/login`)

## Rollback

`PATCH /config/auth` with previous values captured above.

## Out of Scope

- No code changes; env var `NEXT_PUBLIC_APP_FRONTEND_URL` is already optional and does not need to be set locally (window.location.origin suffices).
- Marketing site `/auth/callback` route is not added; marketing stays unauthenticated.
