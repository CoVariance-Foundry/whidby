#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const DEFAULT_SOURCE =
  "/Users/antwoineflowers/Desktop/development/covariance/whidby/.env";
const REQUIRED_APP_KEYS = [
  "NEXT_PUBLIC_SUPABASE_URL",
  "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY",
];

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDir, "../..");

function parseArgs(argv) {
  const separatorIndex = argv.indexOf("--");
  const ownArgs = separatorIndex === -1 ? argv : argv.slice(0, separatorIndex);
  const command = separatorIndex === -1 ? [] : argv.slice(separatorIndex + 1);
  const options = {
    source: process.env.WHIDBY_ENV_SOURCE || DEFAULT_SOURCE,
  };

  for (let index = 0; index < ownArgs.length; index += 1) {
    const arg = ownArgs[index];
    if (arg === "--source") {
      const value = ownArgs[index + 1];
      if (!value || value.startsWith("--")) {
        throw new Error("Missing value for --source");
      }
      options.source = value;
      index += 1;
      continue;
    }
    if (arg === "--help" || arg === "-h") {
      printHelp();
      process.exit(0);
    }
    throw new Error(`Unknown argument: ${arg}`);
  }

  return { options, command };
}

function printHelp() {
  console.log(`Usage:
  npm run env:sync:local
  node scripts/dev/sync_worktree_env.mjs [--source /path/to/.env]
  node scripts/dev/sync_worktree_env.mjs -- npm --workspace apps/app run test:e2e

Copies an ignored local Whidby .env into this worktree's root .env and
apps/app/.env.local. When a command is supplied after --, the command runs with
the copied env values loaded into its process environment. Values are never
printed.`);
}

function parseEnv(content) {
  const values = new Map();
  for (const rawLine of content.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) continue;

    const match = line.match(/^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)$/);
    if (!match) continue;

    const [, key, rawValue] = match;
    values.set(key, normalizeValue(rawValue));
  }
  return values;
}

function normalizeValue(rawValue) {
  let value = rawValue.trim();
  if (
    (value.startsWith('"') && value.endsWith('"')) ||
    (value.startsWith("'") && value.endsWith("'"))
  ) {
    value = value.slice(1, -1);
  }
  return value;
}

function ensureReadableSource(sourcePath) {
  if (!fs.existsSync(sourcePath)) {
    throw new Error(`Source env file not found: ${sourcePath}`);
  }
  const stat = fs.statSync(sourcePath);
  if (!stat.isFile()) {
    throw new Error(`Source env path is not a file: ${sourcePath}`);
  }
}

function writeSecretFile(targetPath, content) {
  fs.mkdirSync(path.dirname(targetPath), { recursive: true });
  fs.writeFileSync(targetPath, content, { mode: 0o600 });
  fs.chmodSync(targetPath, 0o600);
}

function buildAppEnvContent(sourceContent, values) {
  const additions = [];
  if (!values.has("E2E_AUTH_EMAIL") && values.has("WHIDBY_TEST_USER_EMAIL")) {
    additions.push(["E2E_AUTH_EMAIL", values.get("WHIDBY_TEST_USER_EMAIL")]);
  }
  if (
    !values.has("E2E_AUTH_PASSWORD") &&
    values.has("WHIDBY_TEST_USER_PASSWORD")
  ) {
    additions.push(["E2E_AUTH_PASSWORD", values.get("WHIDBY_TEST_USER_PASSWORD")]);
  }

  if (additions.length === 0) return sourceContent;

  const derivedLines = additions.map(([key, value]) => `${key}=${value}`);
  return `${sourceContent.trimEnd()}

# Derived aliases for local Playwright E2E in worktrees.
${derivedLines.join("\n")}
`;
}

function buildRuntimeEnv(values) {
  const env = { ...process.env };
  for (const [key, value] of values) {
    if (env[key] === undefined) {
      env[key] = value;
    }
  }
  if (env.E2E_AUTH_EMAIL === undefined && values.has("WHIDBY_TEST_USER_EMAIL")) {
    env.E2E_AUTH_EMAIL = values.get("WHIDBY_TEST_USER_EMAIL");
  }
  if (
    env.E2E_AUTH_PASSWORD === undefined &&
    values.has("WHIDBY_TEST_USER_PASSWORD")
  ) {
    env.E2E_AUTH_PASSWORD = values.get("WHIDBY_TEST_USER_PASSWORD");
  }
  return env;
}

function reportMissingRequired(values) {
  const missing = REQUIRED_APP_KEYS.filter((key) => !values.has(key));
  if (missing.length === 0) {
    console.log(`Required app env keys present: ${REQUIRED_APP_KEYS.join(", ")}`);
    return;
  }
  throw new Error(
    `Source env file is missing required app keys: ${missing.join(", ")}`,
  );
}

function runCommand(command, env) {
  if (command.length === 0) return;

  console.log(`Running with synced env: ${command.join(" ")}`);
  const result = spawnSync(command[0], command.slice(1), {
    cwd: repoRoot,
    env,
    stdio: "inherit",
  });

  if (result.error) {
    throw result.error;
  }
  process.exit(result.status ?? 1);
}

try {
  const { options, command } = parseArgs(process.argv.slice(2));
  const sourcePath = path.resolve(options.source);
  ensureReadableSource(sourcePath);

  const sourceContent = fs.readFileSync(sourcePath, "utf8");
  const values = parseEnv(sourceContent);
  reportMissingRequired(values);

  const rootTarget = path.join(repoRoot, ".env");
  const appTarget = path.join(repoRoot, "apps/app/.env.local");
  writeSecretFile(rootTarget, sourceContent);
  writeSecretFile(appTarget, buildAppEnvContent(sourceContent, values));

  console.log(`Synced env from ${sourcePath}`);
  console.log(`Wrote ${path.relative(repoRoot, rootTarget)}`);
  console.log(`Wrote ${path.relative(repoRoot, appTarget)}`);

  runCommand(command, buildRuntimeEnv(values));
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
}
