#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDir, "../..");

const DEFAULT_SOURCE = path.join(repoRoot, ".env");
const APP_ENV_PATH = path.join(repoRoot, "apps/app/.env.local");

const REQUIRED_ROOT_KEYS = [
  "NEXT_PUBLIC_SUPABASE_URL",
  "SUPABASE_SERVICE_ROLE_KEY",
  "DATAFORSEO_LOGIN",
  "DATAFORSEO_PASSWORD",
  "ANTHROPIC_API_KEY",
];

const REQUIRED_APP_KEYS = [
  "NEXT_PUBLIC_SUPABASE_URL",
  "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY",
];

function parseArgs(argv) {
  const options = {
    source: process.env.WHIDBY_ENV_SOURCE || DEFAULT_SOURCE,
    skipNetwork: false,
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--source") {
      const value = argv[index + 1];
      if (!value || value.startsWith("--")) {
        throw new Error("Missing value for --source");
      }
      options.source = value;
      index += 1;
      continue;
    }
    if (arg === "--skip-network") {
      options.skipNetwork = true;
      continue;
    }
    if (arg === "--help" || arg === "-h") {
      printHelp();
      process.exit(0);
    }
    throw new Error(`Unknown argument: ${arg}`);
  }

  return options;
}

function printHelp() {
  console.log(`Usage:
  npm run runtime:check
  node scripts/dev/check_runtime_env.mjs [--source /path/to/.env] [--skip-network]

Checks that ignored local env files are present in this worktree, service-role
Supabase keys can read a harmless table, and the Python runtime can import the
Supabase client. Secret values are never printed.`);
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

function parseEnvFile(filePath) {
  if (!fs.existsSync(filePath)) {
    throw new Error(`Env file not found: ${filePath}`);
  }
  const stat = fs.statSync(filePath);
  if (!stat.isFile()) {
    throw new Error(`Env path is not a file: ${filePath}`);
  }

  const values = new Map();
  const content = fs.readFileSync(filePath, "utf8");
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

function relativePath(filePath) {
  return path.relative(repoRoot, filePath) || ".";
}

function projectRef(url) {
  return url.match(/^https:\/\/([^.]+)\.supabase\.co\b/)?.[1] ?? "(unknown)";
}

function keyShape(value) {
  if (!value) return "missing";
  if (value.startsWith("eyJ")) return "jwt";
  if (value.startsWith("sb_")) return "sb_key";
  return "set";
}

function reportKeyPresence(label, values, requiredKeys) {
  const missing = requiredKeys.filter((key) => !values.get(key));
  if (missing.length > 0) {
    throw new Error(`${label} is missing required keys: ${missing.join(", ")}`);
  }
  console.log(`ok: ${label} has required keys (${requiredKeys.join(", ")})`);
}

async function checkSupabaseRead({ label, url, key, required }) {
  if (!url || !key) {
    const message = `${label} skipped: missing url or key`;
    if (required) throw new Error(message);
    console.log(`warn: ${message}`);
    return;
  }

  const endpoint = new URL(`${url.replace(/\/$/, "")}/rest/v1/metros`);
  endpoint.searchParams.set("select", "cbsa_code");
  endpoint.searchParams.set("limit", "1");

  const response = await fetch(endpoint, {
    headers: {
      apikey: key,
      Authorization: `Bearer ${key}`,
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    const body = await response.text();
    const message = `${label} failed HTTP ${response.status}: ${body.slice(0, 140)}`;
    if (required) throw new Error(message);
    console.log(`warn: ${message}`);
    return;
  }

  console.log(
    `ok: ${label} can read metros on ${projectRef(url)} (${keyShape(key)})`,
  );
}

function checkPythonRuntime(values) {
  const code = [
    "import sys",
    "from supabase import create_client",
    "assert sys.version_info >= (3, 11), sys.version",
    "print(f'python={sys.version.split()[0]} supabase_client=ok')",
  ].join("; ");

  const env = { ...process.env };
  for (const [key, value] of values) {
    if (env[key] === undefined) env[key] = value;
  }

  const result = spawnSync("uv", ["run", "python", "-c", code], {
    cwd: repoRoot,
    env,
    encoding: "utf8",
  });

  if (result.error) {
    throw result.error;
  }
  if (result.status !== 0) {
    throw new Error(
      `Python runtime check failed:\n${result.stderr || result.stdout}`.trim(),
    );
  }
  console.log(`ok: ${result.stdout.trim()}`);
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  const sourcePath = path.resolve(options.source);
  const rootEnv = parseEnvFile(sourcePath);
  const appEnv = parseEnvFile(APP_ENV_PATH);

  console.log(`checking root env: ${sourcePath}`);
  console.log(`checking app env: ${relativePath(APP_ENV_PATH)}`);
  reportKeyPresence("root env", rootEnv, REQUIRED_ROOT_KEYS);
  reportKeyPresence("apps/app env", appEnv, REQUIRED_APP_KEYS);

  if (!options.skipNetwork) {
    await checkSupabaseRead({
      label: "production service-role key",
      url: rootEnv.get("NEXT_PUBLIC_SUPABASE_URL"),
      key: rootEnv.get("SUPABASE_SERVICE_ROLE_KEY"),
      required: true,
    });
    await checkSupabaseRead({
      label: "staging service-role key",
      url: rootEnv.get("STAGING_SUPABASE_URL"),
      key: rootEnv.get("STAGING_SUPABASE_SERVICE_ROLE_KEY"),
      required: false,
    });
    await checkSupabaseRead({
      label: "production publishable key",
      url: rootEnv.get("NEXT_PUBLIC_SUPABASE_URL"),
      key: rootEnv.get("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY"),
      required: false,
    });
    await checkSupabaseRead({
      label: "staging publishable key",
      url: rootEnv.get("STAGING_SUPABASE_URL"),
      key: rootEnv.get("STAGING_NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY"),
      required: false,
    });
  } else {
    console.log("skipped: network Supabase checks");
  }

  checkPythonRuntime(rootEnv);
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
});
