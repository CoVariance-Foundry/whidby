# AI Review and Visual QA CI/CD Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a CI/CD review system that combines Greptile code review, deterministic Playwright checks, and an agent-driven visual QA pass that reviews preview flows like a user and frontend designer.

**Architecture:** Keep the existing `dev -> main` release model and add PR-level review automation around it. Greptile remains the code-review specialist through the GitHub App and MCP integrations; Playwright produces reproducible screenshots, traces, and HTML reports; a local or CI agent consumes those artifacts and posts design/product feedback back to the PR.

**Tech Stack:** GitHub Actions, Greptile GitHub App + MCP, Playwright, Vercel preview deployments, Supabase branching, Render staging/prod services, Cursor MCP, Codex MCP, Claude Code MCP, Node scripts, existing Next.js apps in `apps/app` and `apps/admin`.

---

## Research Notes

- Greptile should be installed as a GitHub App, repository indexing must be enabled, and review triggers can be filtered by labels, branches, authors, and keywords. Greptile can also be triggered manually by tagging `@greptileai` on a PR.
- Greptile MCP supports Cursor, Claude Code, VS Code, and Codex CLI. For this repo, use env-var based project config so API keys stay outside git.
- Playwright visual comparison uses `expect(page).toHaveScreenshot()`. Baselines must be generated and compared in the same OS/browser environment to avoid noise.
- Playwright CI should upload HTML reports, traces, videos, screenshots, and any agent comments as artifacts. Traces should stay `on-first-retry` for normal E2E; the visual QA job should retain artifacts every run.
- Vercel creates preview deployments for non-production branches. Branch-specific Preview variables override broad Preview variables.
- Vercel custom environments can map persistent branches like `dev` or `staging` to a named environment on supported plans.
- Supabase branches are separate Supabase instances with their own API credentials. Preview branches are ephemeral and data-less unless seeded; persistent branches are appropriate for staging/QA/dev.
- Supabase's Vercel branching integration syncs the matching Supabase branch credentials into the Vercel preview deployment when a PR opens, and can redeploy to handle timing races.
- GitHub environments provide environment-scoped secrets, variables, deployment branch rules, and reviewer gates. Jobs only receive environment secrets after protection rules pass.
- GitHub OIDC requires `permissions: id-token: write`; it allows short-lived cloud tokens but does not itself grant access to other resources.

Sources:

- Greptile quickstart: https://www.greptile.com/docs/quickstart
- Greptile MCP setup: https://www.greptile.com/docs/mcp-v2/setup
- Playwright visual comparisons: https://playwright.dev/docs/test-snapshots
- Vercel Git deployments: https://vercel.com/docs/git
- Vercel environment variables: https://vercel.com/docs/environment-variables
- Supabase branching: https://supabase.com/docs/guides/deployment/branching
- Supabase branching + Vercel: https://supabase.com/docs/guides/deployment/branching/integrations
- GitHub environments: https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments
- GitHub OIDC: https://docs.github.com/en/actions/reference/security/oidc
- Cursor MCP docs: https://docs.cursor.com/advanced/model-context-protocol
- Claude Code MCP docs: https://docs.claude.com/en/docs/claude-code/mcp

---

## Target Branching and Environment Strategy

### Branch Classes

| Branch class | Base/target | Database | Frontend | API | Purpose |
| --- | --- | --- | --- | --- | --- |
| `main` | protected production | production Supabase project | Vercel Production | Render `whidby-1` | Customer-facing production |
| `dev` | protected integration | persistent staging Supabase project or persistent Supabase branch | Vercel custom `staging` environment or branch-scoped Preview | Render `whidby-staging` | Integration and release candidate |
| `codex/*`, `feature/*`, `fix/*` | PR to `dev` by default | ephemeral Supabase preview branch when schema changes; staging Supabase for UI-only PRs | Vercel Preview | Render staging API unless branch-specific API exists | Feature review |
| `hotfix/*` | PR to `main` | production migration preview, then production on merge | Vercel Preview, then Production | Render production only after merge | Urgent production fixes |

### Merge Rules

- Feature branches PR into `dev`.
- `dev` PRs into `main` after GitHub quality gates, Greptile review, visual QA, and staging smoke pass.
- Hotfix branches PR into `main` only when user explicitly chooses a production bypass.
- Branch names used by Codex should keep the repo convention: `codex/<short-feature>`.
- Do not commit directly to `main` unless the user explicitly requests it for docs-only or emergency work.

### Database Rules

- Use the existing staging Supabase project for broad preview unless the PR changes `supabase/migrations/**`.
- For schema-changing PRs, create or rely on Supabase preview branches and seed minimal deterministic data.
- Keep preview branches data-light: seeded auth/test accounts, reference rows, cached reports needed for `/explore`, `/reports`, `/niche-finder`, onboarding, and strategy discovery smoke paths.
- Never point feature previews at production service-role credentials.
- Store branch metadata in PR comments and GitHub deployment statuses, not in committed env files.

### Vercel Rules

- `main` maps to Vercel Production.
- `dev` should map to a Vercel custom `staging` environment if the plan supports it; otherwise use branch-specific Preview variables for `dev`.
- Feature branches receive normal Vercel Preview deployments.
- Enable Vercel system environment variables so Playwright and app code can read `VERCEL_ENV`, `VERCEL_BRANCH_URL`, `VERCEL_GIT_COMMIT_REF`, `VERCEL_GIT_PULL_REQUEST_ID`, and deployment IDs when needed.

---

## File Structure

### MCP and Agent Configuration

- Modify `.mcp.json` to add a shared Greptile HTTP MCP server with `Authorization: Bearer ${GREPTILE_API_KEY}`.
- Modify `.codex/config.toml` to add `mcp_servers.greptile` with `bearer_token_env_var = "GREPTILE_API_KEY"`.
- Create `.cursor/mcp.json` with Greptile, GitHub, and optional Supabase MCP entries using environment variables only.
- Create `.cursor/rules/visual-qa.mdc` to describe how Cursor agents should interpret visual QA artifacts and avoid making unapproved production changes.

### CI/CD Workflows

- Modify `.github/workflows/quality-gates.yml` to keep existing checks and add job dependencies consumed by later workflows.
- Create `.github/workflows/ai-review.yml` for Greptile status tracking, MCP-assisted comment collection instructions, and PR summary links.
- Create `.github/workflows/visual-qa.yml` for Playwright smoke, visual artifact capture, optional agent critique, and PR feedback.
- Create `.github/workflows/env-audit.yml` for environment matrix drift checks across GitHub, Vercel, Render, and Supabase.

### Automation Scripts

- Create `scripts/ci/find_vercel_deployment.mjs` to resolve the Vercel preview URL for a PR commit.
- Create `scripts/ci/wait_for_github_check.mjs` to wait for Vercel and Supabase Preview checks before running remote preview QA.
- Create `scripts/ci/env_manifest_check.mjs` to validate that required variable names exist in the expected platforms without printing secret values.
- Create `scripts/ci/sync_vercel_env.mjs` to push non-secret and secret values from a local operator-provided env source to Vercel environments.
- Create `scripts/ci/sync_github_env.mjs` to configure GitHub environment variables and secrets through the GitHub REST API.
- Create `scripts/ci/sync_supabase_branch_secrets.mjs` to set branch secrets for Supabase preview/persistent branches through Supabase API or CLI.

### Visual QA

- Create `scripts/qa/flows/consumer.json` to declare consumer flows, routes, auth state, and design-review expectations.
- Create `scripts/qa/flows/admin.json` to declare admin flows.
- Create `scripts/qa/run_visual_qa.mjs` to run Playwright against local or preview URLs and emit artifacts.
- Create `scripts/qa/agent_review.mjs` to call `codex` or `claude` in non-interactive mode when configured.
- Create `scripts/qa/post_pr_feedback.mjs` to post a single PR comment with artifact links, findings, and suggested improvements.
- Create `scripts/qa/prompts/visual-designer-review.md` as the reusable prompt for the local/CI agent.
- Modify `apps/app/playwright.config.ts` to add visual QA artifact retention and optional `baseURL` override via `PLAYWRIGHT_BASE_URL`.
- Modify `apps/admin/playwright.config.ts` the same way.
- Create `apps/app/e2e/visual-qa.spec.ts` for the consumer flow screenshots.
- Create `apps/admin/e2e/visual-qa.spec.ts` for the admin flow screenshots.

### Environment Source of Truth

- Create `config/environments/manifest.json` to define required variables by platform, app, and environment.
- Create `config/environments/README.md` only if implementation discovers that `docs-canonical/ENVIRONMENT.md` becomes too large; otherwise update `docs-canonical/ENVIRONMENT.md` and do not create this README.
- Modify `docs-canonical/ENVIRONMENT.md` with the final branching/env matrix and secret ownership rules.
- Modify `.Codex/ACTIVE_WORK.md` when implementation starts.
- Modify `.Codex/project_context.md` after implementation completes.

---

## Task 1: Document and Lock the Release Topology

**Files:**
- Modify: `docs-canonical/ENVIRONMENT.md`
- Modify: `.codex/ACTIVE_WORK.md`
- Test: `npx docguard-cli guard`

- [x] **Step 1: Add the environment topology section to `docs-canonical/ENVIRONMENT.md`**

Add this section after the existing "Staging Environment" section:

```markdown
## AI Review, Preview, and Visual QA Environments

| Stage | Git branch | Frontend | API | Database | Review gates |
|-------|------------|----------|-----|----------|--------------|
| Feature Preview | `codex/*`, `feature/*`, `fix/*` PRs into `dev` | Vercel Preview | Render staging API by default | Supabase preview branch for schema-changing PRs, otherwise staging Supabase | Quality Gates, Greptile, Playwright smoke, optional visual QA |
| Integration | `dev` | Vercel staging custom environment or branch-scoped Preview | `whidby-staging` Render service | persistent staging Supabase project or persistent Supabase branch | Full Quality Gates, visual QA, staging smoke |
| Production | `main` | Vercel Production | `whidby-1` Render service | production Supabase project | protected merge from `dev`, production migration approval |

Feature branches must not receive production service-role credentials. Schema-changing PRs should use Supabase preview branches seeded with deterministic test data. UI-only PRs may use staging Supabase with E2E test accounts.
```

- [x] **Step 2: Update `.codex/ACTIVE_WORK.md`**

Set the active work pointer to:

```markdown
## Active Work

- CI/CD AI review and visual QA workflow implementation.
- Plan: `docs/superpowers/plans/2026-05-17-ai-review-visual-qa-cicd.md`
- Next: implement MCP config, env manifest, visual QA scripts, and GitHub workflows in separate reviewed commits.
```

- [x] **Step 3: Run DocGuard**

Run:

```bash
npx docguard-cli guard
```

Expected: either a clean pass or the repo's existing warning-only DocGuard baseline. If the command fails because the package is unavailable or network-restricted, record the exact failure in the implementation closeout and do not call it a pass.

Task 1 verification result:

- `git diff --check`: passed.
- `npx docguard-cli guard`: attempted; failed with `ENOTFOUND registry.npmjs.org`. DocGuard is not a pass.

- [x] **Step 4: Commit**

```bash
git add docs-canonical/ENVIRONMENT.md .codex/ACTIVE_WORK.md
git commit -m "docs: define ai review preview qa topology"
```

---

## Task 2: Add Shared MCP Configuration for Greptile and Agents

**Files:**
- Modify: `.mcp.json`
- Modify: `.codex/config.toml`
- Create: `.cursor/mcp.json`
- Create: `.cursor/rules/visual-qa.mdc`
- Test: `GREPTILE_API_KEY=redacted codex mcp list`

- [x] **Step 1: Extend `.mcp.json`**

Add `greptile` under `mcpServers`:

```json
"greptile": {
  "type": "http",
  "url": "https://api.greptile.com/mcp",
  "headers": {
    "Authorization": "Bearer ${GREPTILE_API_KEY}"
  }
}
```

Keep the existing `activecampaign` and `render` entries unchanged.

- [x] **Step 2: Extend `.codex/config.toml`**

Append:

```toml
[mcp_servers.greptile]
url = "https://api.greptile.com/mcp"
bearer_token_env_var = "GREPTILE_API_KEY"
```

- [x] **Step 3: Create `.cursor/mcp.json`**

Create with Cursor-specific environment interpolation in headers:

```json
{
  "mcpServers": {
    "greptile": {
      "type": "http",
      "url": "https://api.greptile.com/mcp",
      "headers": {
        "Authorization": "Bearer ${env:GREPTILE_API_KEY}"
      }
    },
    "render": {
      "type": "http",
      "url": "https://mcp.render.com/mcp",
      "headers": {
        "Authorization": "Bearer ${env:RENDER_API_TOKEN}"
      }
    }
  }
}
```

Quality-review fix: `.cursor/mcp.json` uses Cursor's `${env:NAME}` syntax for MCP header environment interpolation. Do not change `.mcp.json` or `.codex/config.toml` for this finding; those files use their own supported environment-variable syntax.

- [x] **Step 4: Create `.cursor/rules/visual-qa.mdc`**

Create:

```markdown
---
description: Visual QA review workflow for Whidby previews
globs:
  - "scripts/qa/**"
  - "apps/**/e2e/**"
  - "apps/**/src/**/*.{tsx,ts,css}"
---

When reviewing visual QA artifacts, separate functional defects from design suggestions. Do not change production credentials, Vercel settings, Supabase projects, or Render services from Cursor. For UI suggestions, cite the screenshot file, viewport, route, and visible symptom.
```

- [x] **Step 5: Verify config shape**

Run:

```bash
node -e 'JSON.parse(require("fs").readFileSync(".mcp.json","utf8")); JSON.parse(require("fs").readFileSync(".cursor/mcp.json","utf8")); console.log("mcp json ok")'
```

Expected:

```text
mcp json ok
```

- [x] **Step 6: Commit**

```bash
git add .mcp.json .codex/config.toml .cursor/mcp.json .cursor/rules/visual-qa.mdc
git commit -m "chore: configure ai review mcp clients"
```

Task 2 verification result:

- `node -e 'JSON.parse(require("fs").readFileSync(".mcp.json","utf8")); JSON.parse(require("fs").readFileSync(".cursor/mcp.json","utf8")); console.log("mcp json ok")'`: passed with `mcp json ok`.
- `git diff --check`: passed.
- Quality-review fix verification: Cursor MCP headers now use `Bearer ${env:GREPTILE_API_KEY}` and `Bearer ${env:RENDER_API_TOKEN}`; `.mcp.json` and `.codex/config.toml` were intentionally left unchanged.

---

## Task 3: Add Environment Manifest and Drift Checks

**Files:**
- Create: `config/environments/manifest.json`
- Create: `scripts/ci/env_manifest_check.mjs`
- Create: `.github/workflows/env-audit.yml`
- Modify: `package.json`
- Test: `npm run env:check -- --offline`

- [x] **Step 1: Create `config/environments/manifest.json`**

```json
{
  "environments": {
    "preview": {
      "githubEnvironment": "preview",
      "vercelTarget": "preview",
      "renderService": "whidby-staging",
      "supabaseMode": "preview-branch"
    },
    "staging": {
      "githubEnvironment": "staging",
      "vercelTarget": "staging",
      "renderService": "whidby-staging",
      "supabaseMode": "persistent-staging"
    },
    "production": {
      "githubEnvironment": "production",
      "vercelTarget": "production",
      "renderService": "whidby-1",
      "supabaseMode": "production"
    }
  },
  "variables": [
    { "name": "NEXT_PUBLIC_SUPABASE_URL", "kind": "public", "platforms": ["vercel"], "environments": ["preview", "staging", "production"] },
    { "name": "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY", "kind": "public", "platforms": ["vercel"], "environments": ["preview", "staging", "production"] },
    { "name": "SUPABASE_SERVICE_ROLE_KEY", "kind": "secret", "platforms": ["github", "render"], "environments": ["preview", "staging", "production"] },
    { "name": "NEXT_PUBLIC_API_URL", "kind": "public", "platforms": ["vercel"], "environments": ["preview", "staging", "production"] },
    { "name": "STRATEGY_DISCOVERY_INTERNAL_TOKEN", "kind": "secret", "platforms": ["vercel", "render", "github"], "environments": ["preview", "staging", "production"] },
    { "name": "GREPTILE_API_KEY", "kind": "secret", "platforms": ["github"], "environments": ["preview", "staging"] },
    { "name": "VERCEL_TOKEN", "kind": "secret", "platforms": ["github"], "environments": ["preview", "staging", "production"] },
    { "name": "VERCEL_ORG_ID", "kind": "secret", "platforms": ["github"], "environments": ["preview", "staging", "production"] },
    { "name": "VERCEL_PROJECT_ID_APP", "kind": "secret", "platforms": ["github"], "environments": ["preview", "staging", "production"] },
    { "name": "VERCEL_PROJECT_ID_ADMIN", "kind": "secret", "platforms": ["github"], "environments": ["preview", "staging", "production"] },
    { "name": "SUPABASE_ACCESS_TOKEN", "kind": "secret", "platforms": ["github"], "environments": ["preview", "staging", "production"] },
    { "name": "SUPABASE_PROJECT_ID", "kind": "secret", "platforms": ["github"], "environments": ["preview", "staging", "production"] },
    { "name": "RENDER_API_TOKEN", "kind": "secret", "platforms": ["github"], "environments": ["staging", "production"] },
    { "name": "E2E_AUTH_EMAIL", "kind": "secret", "platforms": ["github", "vercel"], "environments": ["preview", "staging"] },
    { "name": "E2E_AUTH_PASSWORD", "kind": "secret", "platforms": ["github", "vercel"], "environments": ["preview", "staging"] },
    { "name": "AI_QA_PROVIDER", "kind": "public", "platforms": ["github"], "environments": ["preview", "staging"] },
    { "name": "ANTHROPIC_API_KEY", "kind": "secret", "platforms": ["github"], "environments": ["preview", "staging"] },
    { "name": "OPENAI_API_KEY", "kind": "secret", "platforms": ["github"], "environments": ["preview", "staging"] }
  ]
}
```

- [x] **Step 2: Create `scripts/ci/env_manifest_check.mjs`**

Implement a read-only checker that:

1. Parses `config/environments/manifest.json`.
2. Fails if any variable object is missing `name`, `kind`, `platforms`, or `environments`.
3. Fails if a secret name starts with `NEXT_PUBLIC_`.
4. Supports `--offline` and prints the required matrix without contacting external services.
5. Supports `--github`, `--vercel`, `--render`, and `--supabase` modes for future live checks.
6. Never prints secret values.

Core implementation:

```js
#!/usr/bin/env node
import fs from "node:fs";

const args = new Set(process.argv.slice(2));
const manifest = JSON.parse(fs.readFileSync("config/environments/manifest.json", "utf8"));
const errors = [];

for (const variable of manifest.variables) {
  for (const key of ["name", "kind", "platforms", "environments"]) {
    if (!(key in variable)) errors.push(`${variable.name || "<unnamed>"} missing ${key}`);
  }
  if (variable.kind === "secret" && variable.name.startsWith("NEXT_PUBLIC_")) {
    errors.push(`${variable.name} is marked secret but is public by naming convention`);
  }
}

if (errors.length > 0) {
  console.error(errors.join("\n"));
  process.exit(1);
}

if (args.has("--offline")) {
  for (const variable of manifest.variables) {
    console.log(`${variable.name}: ${variable.kind} -> ${variable.platforms.join(",")} / ${variable.environments.join(",")}`);
  }
  process.exit(0);
}

console.log("live platform checks are enabled by provider flags; no provider flag was selected");
```

- [x] **Step 3: Add root package script**

Modify `package.json`:

```json
"env:check": "node scripts/ci/env_manifest_check.mjs"
```

- [x] **Step 4: Create `.github/workflows/env-audit.yml`**

```yaml
name: Environment Audit

on:
  pull_request:
    branches: [dev, main]
    paths:
      - "config/environments/**"
      - "scripts/ci/**"
      - ".github/workflows/env-audit.yml"
      - "docs-canonical/ENVIRONMENT.md"
  workflow_dispatch:

permissions:
  contents: read

jobs:
  manifest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: npm
      - run: npm ci
      - run: npm run env:check -- --offline
```

- [x] **Step 5: Verify**

Run:

```bash
npm run env:check -- --offline
```

Expected: prints variable names and platforms only; no secret values.

Verification results:

- `npm run env:check -- --offline` passed; output listed required variable names, kinds, platforms, and environments only.
- `git diff --check` passed.

- [x] **Step 6: Commit**

```bash
git add config/environments/manifest.json scripts/ci/env_manifest_check.mjs .github/workflows/env-audit.yml package.json
git commit -m "chore: add environment manifest audit"
```

---

## Task 4: Add Programmatic Environment Sync Scripts

**Files:**
- Create: `scripts/ci/sync_vercel_env.mjs`
- Create: `scripts/ci/sync_github_env.mjs`
- Create: `scripts/ci/sync_supabase_branch_secrets.mjs`
- Modify: `package.json`
- Test: `npm run env:sync:dry-run -- --environment preview`

- [x] **Step 1: Create `scripts/ci/sync_vercel_env.mjs`**

Behavior:

- Read `config/environments/manifest.json`.
- Accept `--environment preview|staging|production`.
- Accept `--dry-run`.
- Read values from the current process environment.
- For `--dry-run`, print only variable names and target environments.
- For live mode, call Vercel CLI or REST API to upsert env vars.
- Never print raw values.

The initial implementation should support dry-run first:

```js
#!/usr/bin/env node
import fs from "node:fs";

const args = process.argv.slice(2);
const dryRun = args.includes("--dry-run");
const envName = args[args.indexOf("--environment") + 1];
if (!envName) throw new Error("Missing --environment preview|staging|production");

const manifest = JSON.parse(fs.readFileSync("config/environments/manifest.json", "utf8"));
const vercelVars = manifest.variables.filter((v) => v.platforms.includes("vercel") && v.environments.includes(envName));

for (const variable of vercelVars) {
  const present = Boolean(process.env[variable.name]);
  console.log(`${dryRun ? "would sync" : "sync"} ${variable.name} to Vercel ${envName}: ${present ? "present" : "missing"}`);
  if (!dryRun && !present) throw new Error(`${variable.name} missing from process environment`);
}
```

- [x] **Step 2: Create `scripts/ci/sync_github_env.mjs`**

Behavior:

- Accept `--environment preview|staging|production`.
- Accept `--repo owner/name`.
- Use `GH_TOKEN` or `GITHUB_TOKEN`.
- Use GitHub REST endpoints for environment variables and secrets.
- Encrypt secrets with the repository public key before upload.
- Dry-run by default unless `--apply` is present.
- Never print raw values.

- [x] **Step 3: Create `scripts/ci/sync_supabase_branch_secrets.mjs`**

Behavior:

- Accept `--branch <name>`.
- Accept `--environment preview|staging`.
- Use `SUPABASE_ACCESS_TOKEN` and `SUPABASE_PROJECT_ID`.
- Set branch secrets for Supabase preview/persistent branches.
- Dry-run by default unless `--apply` is present.
- Refuse `--environment production`; production Supabase secrets must be updated through the approved production path.

- [x] **Step 4: Add package scripts**

Modify `package.json`:

```json
"env:sync:vercel": "node scripts/ci/sync_vercel_env.mjs",
"env:sync:github": "node scripts/ci/sync_github_env.mjs",
"env:sync:supabase": "node scripts/ci/sync_supabase_branch_secrets.mjs",
"env:sync:dry-run": "npm run env:sync:vercel -- --dry-run"
```

- [x] **Step 5: Verify dry-run**

Run:

```bash
npm run env:sync:dry-run -- --environment preview
```

Expected: prints only variable names and `present`/`missing`.

Verification results:

- `npm run env:sync:dry-run -- --environment preview` passed; output listed Vercel preview variable names with `present`/`missing` status only.
- Code-quality hardening: `--environment`, `--repo`, and `--branch` now fail during argument parsing when the value is omitted or the next token is another flag.
- Code-quality hardening: Vercel and GitHub dry-run paths now print `No <platform> variables configured for <environment>` instead of silently succeeding when a selected manifest/platform/environment combination has no matching variables; live/apply paths fail instead of claiming an empty sync.
- `node scripts/ci/sync_vercel_env.mjs --dry-run --environment` failed non-zero with `Missing value for --environment`.
- `node scripts/ci/sync_github_env.mjs --environment preview --repo` failed non-zero with `Missing value for --repo`.
- `node scripts/ci/sync_supabase_branch_secrets.mjs --environment preview --branch` failed non-zero with `Missing value for --branch`.
- `node --check scripts/ci/sync_vercel_env.mjs` passed.
- `node --check scripts/ci/sync_github_env.mjs` passed.
- `node --check scripts/ci/sync_supabase_branch_secrets.mjs` passed.
- `git diff --check` passed.

- [x] **Step 6: Commit**

```bash
git add scripts/ci/sync_vercel_env.mjs scripts/ci/sync_github_env.mjs scripts/ci/sync_supabase_branch_secrets.mjs package.json docs/superpowers/plans/2026-05-17-ai-review-visual-qa-cicd.md
git commit -m "chore: add environment sync dry runs"
```

---

## Task 5: Add Preview URL Resolution and Check Waiting

**Files:**
- Create: `scripts/ci/find_vercel_deployment.mjs`
- Create: `scripts/ci/wait_for_github_check.mjs`
- Modify: `package.json`
- Test: `node scripts/ci/find_vercel_deployment.mjs --dry-run --sha abc123`

- [x] **Step 1: Create `scripts/ci/wait_for_github_check.mjs`**

Behavior:

- Accept `--check-name "Vercel"` or `--check-name "Supabase Preview"`.
- Accept `--repo owner/name` and `--sha <commit-sha>`.
- Poll GitHub Checks API until success, failure, cancelled, or timeout.
- Exit non-zero on failure or timeout.

- [x] **Step 2: Create `scripts/ci/find_vercel_deployment.mjs`**

Behavior:

- Accept `--sha <commit-sha>`, `--project-id <project-id>`, `--team-id <team-id>`.
- Use `VERCEL_TOKEN`.
- Query Vercel deployments filtered by project and git SHA.
- Print a single HTTPS preview URL.
- In `--dry-run`, print `https://example-preview.vercel.app`.

- [x] **Step 3: Add package scripts**

Modify `package.json`:

```json
"ci:wait-check": "node scripts/ci/wait_for_github_check.mjs",
"ci:find-preview": "node scripts/ci/find_vercel_deployment.mjs"
```

- [x] **Step 4: Verify dry-run**

Run:

```bash
node scripts/ci/find_vercel_deployment.mjs --dry-run --sha abc123
```

Expected:

```text
https://example-preview.vercel.app
```

Verification results:

- `node scripts/ci/find_vercel_deployment.mjs --dry-run --sha abc123` passed and printed exactly `https://example-preview.vercel.app`.
- `node scripts/ci/wait_for_github_check.mjs --dry-run --repo owner/name --sha abc123 --check-name Vercel` passed and printed a dry-run wait message.
- `node --check scripts/ci/find_vercel_deployment.mjs` passed.
- `node --check scripts/ci/wait_for_github_check.mjs` passed.
- `git diff --check` passed.

Spec review fix:

- `find_vercel_deployment.mjs` now only selects deployments whose `meta.githubCommitSha` exactly equals the requested `--sha`; deployments missing SHA metadata are skipped and do not print unrelated URLs.
- Mocked no-network verification passed: a deployment with missing `githubCommitSha` was skipped in favor of a matching SHA deployment, and a payload containing only a no-SHA deployment exited non-zero with `No Vercel deployment found for commit abc123`.
- Re-ran `node scripts/ci/find_vercel_deployment.mjs --dry-run --sha abc123`, `node --check scripts/ci/find_vercel_deployment.mjs`, mocked deployment checks, and `git diff --check`.

Code quality hardening:

- `find_vercel_deployment.mjs` now requires explicit `--mock` before reading `VERCEL_DEPLOYMENTS_MOCK_JSON`; a mock env var without `--mock` exits non-zero with a clear message. Dry-run still prints exactly `https://example-preview.vercel.app`.
- `find_vercel_deployment.mjs` selects only deployments with exact SHA match, `READY` state, and explicit preview target/environment metadata; missing target metadata, `ERROR`, `CANCELED`, `BUILDING`, `QUEUED`, missing-state, and non-preview payloads fail without printing a URL.
- `find_vercel_deployment.mjs` and `wait_for_github_check.mjs` both accept `--request-timeout-ms <positive integer>` and use `AbortController` to fail bounded fetches clearly.
- Re-ran dry-run, mocked ready preview with explicit metadata, mocked missing target metadata, mocked production/non-preview, GitHub dry-run with request timeout, `node --check` for both scripts, and `git diff --check`.

- [x] **Step 5: Commit**

```bash
git add scripts/ci/find_vercel_deployment.mjs scripts/ci/wait_for_github_check.mjs package.json
git commit -m "chore: resolve preview deployments for qa"
```

---

## Task 6: Add Deterministic Playwright Visual QA Flows

**Files:**
- Create: `scripts/qa/flows/consumer.json`
- Create: `scripts/qa/flows/admin.json`
- Create: `apps/app/e2e/visual-qa.spec.ts`
- Create: `apps/admin/e2e/visual-qa.spec.ts`
- Modify: `apps/app/playwright.config.ts`
- Modify: `apps/admin/playwright.config.ts`
- Modify: `package.json`
- Test: `npm run qa:visual:app`

- [x] **Step 1: Create `scripts/qa/flows/consumer.json`**

```json
{
  "app": "consumer",
  "baseUrlEnv": "PLAYWRIGHT_BASE_URL",
  "viewports": [
    { "name": "desktop", "width": 1440, "height": 1000 },
    { "name": "mobile", "width": 390, "height": 844 }
  ],
  "routes": [
    { "name": "login", "path": "/login", "requiresAuth": false },
    { "name": "explore", "path": "/explore", "requiresAuth": true },
    { "name": "reports", "path": "/reports", "requiresAuth": true },
    { "name": "niche-finder", "path": "/niche-finder", "requiresAuth": true }
  ]
}
```

- [x] **Step 2: Create `scripts/qa/flows/admin.json`**

```json
{
  "app": "admin",
  "baseUrlEnv": "PLAYWRIGHT_BASE_URL",
  "viewports": [
    { "name": "desktop", "width": 1440, "height": 1000 },
    { "name": "mobile", "width": 390, "height": 844 }
  ],
  "routes": [
    { "name": "login", "path": "/login", "requiresAuth": false },
    { "name": "home", "path": "/", "requiresAuth": true },
    { "name": "exploration", "path": "/exploration", "requiresAuth": true }
  ]
}
```

- [x] **Step 3: Modify Playwright configs**

In both `apps/app/playwright.config.ts` and `apps/admin/playwright.config.ts`, change:

```ts
baseURL: "http://localhost:3002",
```

to:

```ts
baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3002",
```

Use `3001` for admin.

Add under `use`:

```ts
screenshot: "only-on-failure",
video: "retain-on-failure",
```

- [x] **Step 4: Create `apps/app/e2e/visual-qa.spec.ts`**

Implement:

```ts
import { expect, test } from "@playwright/test";
import flow from "../../../scripts/qa/flows/consumer.json";

for (const viewport of flow.viewports) {
  test.describe(`consumer visual qa ${viewport.name}`, () => {
    test.use({ viewport: { width: viewport.width, height: viewport.height } });

    for (const route of flow.routes) {
      test(`${route.name} renders without visual shell regressions`, async ({ page }) => {
        await page.goto(route.path);
        await expect(page.locator("body")).toBeVisible();
        await expect(page).toHaveScreenshot(`${route.name}-${viewport.name}.png`, {
          fullPage: true,
          maxDiffPixelRatio: 0.02
        });
      });
    }
  });
}
```

- [x] **Step 5: Create `apps/admin/e2e/visual-qa.spec.ts`**

Use the same implementation with:

```ts
import flow from "../../../scripts/qa/flows/admin.json";
```

and screenshot names based on admin routes.

- [x] **Step 6: Add package scripts**

Modify `package.json`:

```json
"qa:visual:app": "playwright test --config=apps/app/playwright.config.ts apps/app/e2e/visual-qa.spec.ts --project=chromium",
"qa:visual:admin": "playwright test --config=apps/admin/playwright.config.ts apps/admin/e2e/visual-qa.spec.ts --project=chromium"
```

- [x] **Step 7: Record baseline snapshot decision**

Run on a stable local environment:

```bash
npm run qa:visual:app -- --update-snapshots
npm run qa:visual:admin -- --update-snapshots
```

Expected: snapshot files are created under each app's Playwright snapshot directory. Review every image before committing.

Task 6 implementation note: snapshot baselines were intentionally not generated
or committed in this pass because local rendering/browser state was not proven
stable. The specs keep `expect(page).toHaveScreenshot(..., { fullPage: true,
maxDiffPixelRatio: 0.02 })` so baselines can be generated later with
`--update-snapshots` on a stable runner.

- [x] **Step 8: Verify discovery without launching browsers**

Run:

```bash
npm run qa:visual:app
npm run qa:visual:admin
```

Expected: visual QA tests pass on the same machine/OS where baselines were generated.

Verification run:

- `npm run qa:visual:app -- --list` passed and listed 8 tests in 1 file.
- `npm run qa:visual:admin -- --list` passed and listed 6 tests in 1 file.
- `git diff --check` passed.

Code quality review fix:

- `apps/app/playwright.config.ts` and `apps/admin/playwright.config.ts` now skip
  `webServer` when `PLAYWRIGHT_BASE_URL` is set, preserving local server startup
  only for local runs without a hosted base URL.
- `apps/app/e2e/visual-qa.spec.ts` and `apps/admin/e2e/visual-qa.spec.ts` now
  save explicit full-page pass-review screenshots through
  `testInfo.outputPath(...)` before the `toHaveScreenshot(..., { fullPage:
  true, maxDiffPixelRatio: 0.02 })` assertion. Artifact filenames include app,
  route, and viewport with route separators sanitized.
- Verification passed: `npm run qa:visual:app -- --list`,
  `npm run qa:visual:admin -- --list`,
  `PLAYWRIGHT_BASE_URL=https://example.com npm run qa:visual:app -- --list`,
  `PLAYWRIGHT_BASE_URL=https://example.com npm run qa:visual:admin -- --list`,
  and `git diff --check`.

Concern: admin has auth guard coverage but no shared admin auth helper. Admin
visual QA therefore captures `/login` and unauthenticated redirect-stable
versions of `/` and `/exploration`; the protected routes remain represented in
`scripts/qa/flows/admin.json` with `requiresAuth: true`.

- [x] **Step 9: Commit**

```bash
git add scripts/qa/flows apps/app/e2e/visual-qa.spec.ts apps/admin/e2e/visual-qa.spec.ts apps/app/playwright.config.ts apps/admin/playwright.config.ts package.json
git commit -m "test: add visual qa playwright flows"
```

---

## Task 7: Add Agent-Driven Visual Review

**Files:**
- Create: `scripts/qa/prompts/visual-designer-review.md`
- Create: `scripts/qa/run_visual_qa.mjs`
- Create: `scripts/qa/agent_review.mjs`
- Create: `scripts/qa/post_pr_feedback.mjs`
- Modify: `package.json`
- Test: `npm run qa:agent -- --dry-run --artifacts apps/app/playwright-report`

- [x] **Step 1: Create `scripts/qa/prompts/visual-designer-review.md`**

```markdown
You are reviewing Whidby as a product-minded frontend designer and QA observer.

Inputs:
- Route name, viewport, screenshot path, trace path, console errors, network errors, and accessibility snapshot when available.

Review rules:
- Separate blockers, functional defects, visual polish issues, and product copy suggestions.
- Do not invent hidden failures. Only cite evidence visible in artifacts.
- Prefer concise, actionable comments.
- Include route, viewport, artifact path, and suggested owner.
- Do not recommend changes to pricing, entitlement, database policy, or production credentials.

Return JSON:
{
  "summary": "one paragraph",
  "findings": [
    {
      "severity": "blocker|major|minor|polish",
      "route": "/path",
      "viewport": "desktop|mobile",
      "artifact": "path",
      "title": "short finding",
      "recommendation": "specific improvement"
    }
  ]
}
```

- [x] **Step 2: Create `scripts/qa/run_visual_qa.mjs`**

Behavior:

- Accept `--app app|admin`.
- Accept `--base-url <url>`.
- Run the matching Playwright command with `PLAYWRIGHT_BASE_URL`.
- Save artifacts under `artifacts/visual-qa/<app>/<sha-or-local>/`.
- Print the artifact directory.

- [x] **Step 3: Create `scripts/qa/agent_review.mjs`**

Behavior:

- Accept `--provider codex|claude`.
- Accept `--artifacts <dir>`.
- Accept `--dry-run`.
- For `codex`, call a configurable command from `CODEX_QA_COMMAND`, defaulting to `codex exec`.
- For `claude`, call a configurable command from `CLAUDE_QA_COMMAND`, defaulting to `claude -p`.
- Pass the prompt file and artifact manifest to the provider.
- Write `visual-qa-review.json`.
- In dry-run mode, write a valid JSON file with an empty findings array.

- [x] **Step 4: Create `scripts/qa/post_pr_feedback.mjs`**

Behavior:

- Accept `--review-json <path>`.
- Accept `--artifact-url <url>`.
- Accept `--repo owner/name`.
- Accept `--pr <number>`.
- Use `GITHUB_TOKEN`.
- Post or update a single PR comment headed `<!-- whidby-visual-qa -->`.
- Include severity counts, finding list, and artifact links.

- [x] **Step 5: Add package scripts**

Modify `package.json`:

```json
"qa:run": "node scripts/qa/run_visual_qa.mjs",
"qa:agent": "node scripts/qa/agent_review.mjs",
"qa:post": "node scripts/qa/post_pr_feedback.mjs"
```

- [x] **Step 6: Verify dry-run**

Run:

```bash
npm run qa:agent -- --dry-run --artifacts apps/app/playwright-report
```

Expected: `visual-qa-review.json` exists and contains:

```json
{ "summary": "dry run", "findings": [] }
```

Verification completed:

- `npm run qa:agent -- --dry-run --artifacts apps/app/playwright-report` passed and wrote `visual-qa-review.json`.
- `visual-qa-review.json` contained `summary: "dry run"` and an empty `findings` array.
- `node --check scripts/qa/run_visual_qa.mjs` passed.
- `node --check scripts/qa/agent_review.mjs` passed.
- `node --check scripts/qa/post_pr_feedback.mjs` passed.
- `node scripts/qa/post_pr_feedback.mjs --dry-run --review-json visual-qa-review.json --artifact-url https://example.com/artifacts --repo owner/name --pr 1` passed and printed the PR comment markdown without requiring `GITHUB_TOKEN`.
- `git diff --check` passed.

Spec review fix:

- `scripts/qa/run_visual_qa.mjs` now requires `--base-url <url>` and always passes that value as `PLAYWRIGHT_BASE_URL` to Playwright.
- `scripts/qa/agent_review.mjs` now runs the Codex/Claude provider subprocess with an explicit sanitized env: `PATH`, `HOME`, temp directory variables, and only the selected provider API key when present.
- Re-ran missing-base-url failure, agent dry-run, `node --check` for both scripts, and `git diff --check`.

Code quality fix:

- `scripts/qa/run_visual_qa.mjs` now validates `--sha` as a safe artifact id and checks the resolved artifact directory remains under `artifacts/visual-qa/<app>`.
- `scripts/qa/post_pr_feedback.mjs` now paginates issue comments while searching for the `<!-- whidby-visual-qa -->` marker.
- `scripts/qa/agent_review.mjs` now rejects malformed provider JSON before writing `visual-qa-review.json`; the validation probe uses `--mock-provider-json` and does not affect normal provider mode or dry-run mode.
- Verification passed: unsafe `--sha ../../tmp/out` failed non-zero, agent dry-run passed, malformed provider JSON failed clearly, all three `node --check` commands passed, and `git diff --check` passed.

- [x] **Step 7: Commit**

```bash
git add scripts/qa/prompts/visual-designer-review.md scripts/qa/run_visual_qa.mjs scripts/qa/agent_review.mjs scripts/qa/post_pr_feedback.mjs package.json
git commit -m "feat: add agent visual qa review"
```

---

## Task 8: Add Visual QA GitHub Workflow

**Files:**
- Create: `.github/workflows/visual-qa.yml`
- Test: `gh workflow view visual-qa.yml`

- [x] **Step 1: Create `.github/workflows/visual-qa.yml`**

```yaml
name: Visual QA

on:
  pull_request:
    branches: [dev, main]
    types: [opened, synchronize, reopened, labeled]
  workflow_dispatch:
    inputs:
      app:
        description: "app or admin"
        required: true
        default: "app"

permissions:
  contents: read
  pull-requests: write
  checks: read

concurrency:
  group: visual-qa-${{ github.event.pull_request.number || github.run_id }}
  cancel-in-progress: true

jobs:
  visual-qa:
    if: ${{ github.event_name == 'workflow_dispatch' || contains(github.event.pull_request.labels.*.name, 'visual-qa') }}
    runs-on: ubuntu-latest
    environment: preview
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: npm

      - run: npm ci

      - run: npx playwright install --with-deps chromium

      - name: Wait for Vercel preview
        run: npm run ci:wait-check -- --repo "${{ github.repository }}" --sha "${{ github.event.pull_request.head.sha || github.sha }}" --check-name "Vercel"
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Resolve preview URL
        id: preview
        run: |
          url=$(npm run --silent ci:find-preview -- --sha "${{ github.event.pull_request.head.sha || github.sha }}" --project-id "${{ secrets.VERCEL_PROJECT_ID_APP }}" --team-id "${{ secrets.VERCEL_ORG_ID }}")
          echo "url=$url" >> "$GITHUB_OUTPUT"
        env:
          VERCEL_TOKEN: ${{ secrets.VERCEL_TOKEN }}

      - name: Run Playwright visual QA
        run: npm run qa:run -- --app app --base-url "${{ steps.preview.outputs.url }}"
        env:
          E2E_AUTH_EMAIL: ${{ secrets.E2E_AUTH_EMAIL }}
          E2E_AUTH_PASSWORD: ${{ secrets.E2E_AUTH_PASSWORD }}

      - name: Agent review
        if: ${{ vars.AI_QA_PROVIDER != '' }}
        run: npm run qa:agent -- --provider "${{ vars.AI_QA_PROVIDER }}" --artifacts artifacts/visual-qa
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          CODEX_QA_COMMAND: ${{ vars.CODEX_QA_COMMAND }}
          CLAUDE_QA_COMMAND: ${{ vars.CLAUDE_QA_COMMAND }}

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        if: ${{ !cancelled() }}
        with:
          name: visual-qa
          path: |
            artifacts/visual-qa
            playwright-report
            test-results
          retention-days: 14

      - name: Post PR feedback
        if: ${{ github.event_name == 'pull_request' && !cancelled() }}
        run: npm run qa:post -- --review-json visual-qa-review.json --artifact-url "${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}" --repo "${{ github.repository }}" --pr "${{ github.event.pull_request.number }}"
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

- [x] **Step 2: Validate workflow syntax**

Run:

```bash
gh workflow view "Visual QA"
```

Expected: GitHub can parse the workflow after the branch is pushed.

Local verification completed before push:

- `gh workflow view "Visual QA"`: reached GitHub, but failed with `could not find any workflows named Visual QA` because the new workflow is not pushed/indexed yet.
- `python3 -c 'import pathlib, yaml; yaml.safe_load(pathlib.Path(".github/workflows/visual-qa.yml").read_text())'`: attempted; failed because `PyYAML` is not installed in this environment.
- `ruby -e 'require "yaml"; YAML.load_file(".github/workflows/visual-qa.yml"); puts "ok"'`: passed.
- `grep -n "pull_request.head.sha" .github/workflows/visual-qa.yml`: confirmed the PR SHA expression has an empty-string fallback before shell selection.
- `sed -n '1,180p' .github/workflows/visual-qa.yml`: inspected trigger, permissions, concurrency, label gate, preview wait/resolve, default review JSON, artifact upload, and PR feedback wiring.
- `git diff --check`: passed.

Concern recorded: `gh workflow view "Visual QA"` cannot validate this new workflow until the branch is pushed and GitHub indexes it, so local YAML parsing and shell/text inspection were used before commit.

Task 8 code quality fix:

- `workflow_dispatch` now keeps the `app` input and adds optional `preview_url` and `sha` inputs.
- Supplying `preview_url` skips Vercel check waiting and deployment lookup, then runs visual QA directly against that URL.
- Supplying `sha` on manual runs uses that value for artifact id and Vercel lookup when `preview_url` is not supplied; PR runs still use the PR head SHA.
- The Vercel preview check name now comes from `VERCEL_PREVIEW_CHECK_NAME` GitHub environment/repo variable with a shell fallback to `Vercel`, so configured repos are not hard-coded to one check name.
- Agent review remains optional, but fallback JSON now distinguishes unconfigured runs from configured review failures. Configured agent failures continue to artifact upload and PR feedback with a failure summary instead of silently reporting "not configured."
- Verification requested for this fix: Ruby YAML parse, workflow line inspection for `preview_url`, `sha`, configurable Vercel check name, and fallback review JSON status, plus `git diff --check`.

- [x] **Step 3: Commit**

```bash
git add .github/workflows/visual-qa.yml
git commit -m "ci: add visual qa workflow"
```

---

## Task 9: Add Greptile Review Workflow and PR Policy

**Files:**
- Create: `.github/workflows/ai-review.yml`
- Modify: `.github/workflows/quality-gates.yml`
- Modify: `docs-canonical/ENVIRONMENT.md`
- Modify: `docs/superpowers/plans/2026-05-17-ai-review-visual-qa-cicd.md`
- Test: Ruby YAML parse for `.github/workflows/ai-review.yml` and `.github/workflows/quality-gates.yml`; `git diff --check`

- [ ] **Step 1: Install and configure Greptile outside the repo**

Operator action:

1. Install Greptile GitHub App for the Whidby repository.
2. Enable repository indexing.
3. Configure reviews for PRs targeting `dev` and `main`.
4. Add a label trigger named `greptile-review`.
5. Set strictness to prioritize logic/security/regression comments over style-only comments.

Status: operator action, not executable by repo code. Repo changes below document and support the policy without requiring a Greptile token in CI.

- [x] **Step 2: Create `.github/workflows/ai-review.yml`**

```yaml
name: Greptile Review Policy

on:
  pull_request:
    branches: [dev, main]
    types: [opened, synchronize, reopened, labeled]
  workflow_dispatch:

permissions:
  contents: read
  pull-requests: read

jobs:
  greptile-policy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Explain Greptile review policy
        run: |
          cat <<'POLICY' >> "$GITHUB_STEP_SUMMARY"
          Greptile review is provided by the Greptile GitHub App.

          Required local fix loop:
          1. Open Cursor, Codex, or Claude Code with GREPTILE_API_KEY set.
          2. Use Greptile MCP to fetch unaddressed comments.
          3. Fix actionable issues.
          4. Push updates.
          5. Ask Greptile to re-review by label or @greptileai comment when needed.
          POLICY
```

- [x] **Step 3: Update `quality-gates.yml` permissions**

Set top-level permissions:

```yaml
permissions:
  contents: read
  pull-requests: read
```

Keep existing jobs unchanged.

- [x] **Step 4: Document the PR policy**

Add to `docs-canonical/ENVIRONMENT.md`:

```markdown
### PR AI Review Policy

Greptile is the code-review AI for PR-level source review. It runs through the GitHub App and is accessed locally through Greptile MCP in Cursor, Codex, or Claude Code. Visual QA is separate: Playwright captures user-flow artifacts and an optional local/CI agent reviews the rendered experience for product and design issues.
```

- [x] **Step 5: Commit**

```bash
git add .github/workflows/ai-review.yml .github/workflows/quality-gates.yml docs-canonical/ENVIRONMENT.md docs/superpowers/plans/2026-05-17-ai-review-visual-qa-cicd.md
git commit -m "ci: document ai review policy"
```

Task 9 repo-code verification result:

- `ruby -e 'require "yaml"; YAML.load_file(".github/workflows/ai-review.yml"); puts "ai-review.yml OK"'`: passed.
- `ruby -e 'require "yaml"; YAML.load_file(".github/workflows/quality-gates.yml"); puts "quality-gates.yml OK"'`: passed.
- `git diff --check`: passed.

Concern recorded: Greptile GitHub App installation, repository indexing, review trigger configuration, and strictness settings are operator actions outside repo code. This commit only adds the repo-owned workflow summary, least-privilege workflow permissions, and canonical policy documentation.

---

## Task 10: Add Supabase Preview Branch Handling

**Files:**
- Modify: `.github/workflows/visual-qa.yml`
- Create: `supabase/seed.sql` if a deterministic seed file does not already exist
- Modify: `docs-canonical/ENVIRONMENT.md`
- Test: open a PR changing `supabase/migrations/**`

- [ ] **Step 1: Configure Supabase GitHub integration outside the repo**

Operator action:

1. Enable Supabase Branching.
2. Connect the Supabase project to the GitHub repository.
3. Enable automatic branching for PRs targeting `dev` and `main`.
4. Connect Supabase to the Vercel project through the Vercel integration.
5. Confirm the `Supabase Preview` check appears on schema-changing PRs.

- [ ] **Step 2: Add Supabase wait step to `visual-qa.yml`**

Before resolving the Vercel preview URL, add:

```yaml
      - name: Detect Supabase migration changes
        id: migration_changes
        run: |
          if git diff --name-only "${{ github.event.pull_request.base.sha }}" "${{ github.event.pull_request.head.sha }}" | grep '^supabase/migrations/'; then
            echo "changed=true" >> "$GITHUB_OUTPUT"
          else
            echo "changed=false" >> "$GITHUB_OUTPUT"
          fi

      - name: Wait for Supabase preview when migrations changed
        if: ${{ steps.migration_changes.outputs.changed == 'true' }}
        run: npm run ci:wait-check -- --repo "${{ github.repository }}" --sha "${{ github.event.pull_request.head.sha }}" --check-name "Supabase Preview"
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

- [ ] **Step 3: Create `supabase/seed.sql` only if absent**

Seed only non-sensitive deterministic rows required for E2E:

```sql
-- Deterministic preview data for Playwright smoke and visual QA.
-- Do not copy production user data into preview branches.
```

The implementation must inspect current migrations and schema files before adding inserts.

- [ ] **Step 4: Document seed policy**

Add to `docs-canonical/ENVIRONMENT.md`:

```markdown
Supabase preview branches are data-less by default. Preview seed data must be deterministic, minimal, and free of production customer data. Auth users for E2E should be created through the approved staging/preview auth setup, not by committing real passwords into migrations.
```

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/visual-qa.yml docs-canonical/ENVIRONMENT.md supabase/seed.sql
git commit -m "ci: prepare supabase preview qa path"
```

---

## Task 11: End-to-End Dry Run and Closeout

**Files:**
- Modify: `.Codex/project_context.md`
- Test: `npm run env:check -- --offline`, `npm run qa:agent -- --dry-run --artifacts apps/app/playwright-report`, GitHub PR checks

- [ ] **Step 1: Run local static checks**

```bash
npm run env:check -- --offline
node -e 'JSON.parse(require("fs").readFileSync(".mcp.json","utf8")); JSON.parse(require("fs").readFileSync(".cursor/mcp.json","utf8")); console.log("json ok")'
git diff --check
```

Expected: all pass.

- [ ] **Step 2: Run visual QA dry-run**

```bash
npm run qa:agent -- --dry-run --artifacts apps/app/playwright-report
```

Expected: writes `visual-qa-review.json` with no findings.

- [ ] **Step 3: Push branch and open PR into `dev`**

```bash
git push -u origin codex/ai-review-visual-qa-cicd
gh pr create --base dev --head codex/ai-review-visual-qa-cicd --title "Add AI review and visual QA CI/CD plan" --body "Implements Greptile review integration, Playwright visual QA, agent review scaffolding, and environment manifest automation."
```

- [ ] **Step 4: Run hosted checks**

Expected hosted checks:

- Quality Gates
- Environment Audit
- Greptile Review Policy
- Vercel Preview
- Supabase Preview on schema-changing PRs
- Visual QA when `visual-qa` label is present

- [ ] **Step 5: Update `.Codex/project_context.md`**

Add a concise completed-work entry:

```markdown
## AI Review and Visual QA CI/CD

Added the CI/CD review plan and implementation scaffolding for Greptile PR review, Playwright visual QA, optional Codex/Claude agent critique, preview URL resolution, and environment manifest checks. The workflow keeps `dev -> main` as the release spine, uses preview/staging/prod environment separation, and avoids printing or committing secret values.
```

- [ ] **Step 6: Final commit**

```bash
git add .Codex/project_context.md
git commit -m "docs: record ai review qa workflow context"
```

---

## Security and Credential Rules

- Never run agent workflows with production secrets on untrusted pull request code.
- Prefer `pull_request` over `pull_request_target` for code execution.
- Keep `GITHUB_TOKEN` permissions minimal per job.
- Use GitHub environments for `preview`, `staging`, and `production`.
- Use GitHub environment protection for production deploy jobs.
- Use OIDC where external providers support it; otherwise use narrowly-scoped tokens stored as GitHub environment secrets.
- Do not print secret values in scripts, summaries, artifacts, or agent prompts.
- Do not pass raw `.env` files into agent context.
- For Cursor/Codex/Claude local MCP, store API keys in shell/profile or password manager injection, not committed files.
- Treat visual QA agent output as advisory unless it reports a functional blocker with artifact evidence.

---

## Open Operator Decisions

These are explicit product/platform decisions before implementation:

- Greptile review trigger: automatic on every PR to `dev`/`main`, label-only, or both.
- Vercel staging: Pro custom environment named `staging` or Hobby branch-scoped Preview variables for `dev`.
- Supabase preview branch usage: every feature PR or only schema-changing PRs.
- Agent provider for CI visual review: `codex`, `claude`, or local-only for the first rollout.
- Whether visual QA is blocking on PRs to `dev`, blocking only on `dev -> main`, or advisory until the first two weeks of results are reviewed.

Recommended initial choices:

- Greptile automatic for PRs to `dev`/`main`, plus manual `@greptileai` retrigger.
- Vercel custom `staging` if available; otherwise branch-scoped Preview variables for `dev`.
- Supabase preview branches only for schema-changing PRs at first.
- Visual QA advisory on feature PRs, blocking on `dev -> main` after baselines stabilize.
- Local agent review first, CI agent review after token/secret boundaries are verified.

---

## Self-Review

- Spec coverage: covers Greptile code review, Playwright visual QA, agent critique, Cursor/Codex/Claude MCP setup, Vercel preview links, Supabase preview/persistent branch strategy, GitHub environments, Render staging/prod split, and programmatic credential coordination.
- Red-flag scan: no secret values are required for committed files; secret values are referenced only through environment variable names.
- Type consistency: script names, package script names, workflow references, and artifact paths are consistent across tasks.
