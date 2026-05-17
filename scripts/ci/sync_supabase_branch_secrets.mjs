#!/usr/bin/env node
import fs from "node:fs";

const MANIFEST_PATH = "config/environments/manifest.json";
const ALLOWED_ENVIRONMENTS = new Set(["preview", "staging"]);

function readFlagValue(argv, index, flagName) {
  const value = argv[index + 1];

  if (!value || value.startsWith("--")) {
    throw new Error(`Missing value for ${flagName}`);
  }

  return value;
}

function parseArgs(argv) {
  const parsed = {
    apply: false,
    branch: undefined,
    environment: undefined,
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];

    if (arg === "--apply") {
      parsed.apply = true;
      continue;
    }

    if (arg === "--branch") {
      parsed.branch = readFlagValue(argv, index, arg);
      index += 1;
      continue;
    }

    if (arg === "--environment") {
      parsed.environment = readFlagValue(argv, index, arg);
      index += 1;
      continue;
    }

    throw new Error(`Unknown argument: ${arg}`);
  }

  if (parsed.environment === "production") {
    throw new Error("Supabase branch secret sync refuses --environment production");
  }

  if (!parsed.environment || !ALLOWED_ENVIRONMENTS.has(parsed.environment)) {
    throw new Error("Missing or invalid --environment preview|staging");
  }

  if (!parsed.branch) {
    throw new Error("Missing --branch <name>");
  }

  return parsed;
}

function readManifest() {
  try {
    return JSON.parse(fs.readFileSync(MANIFEST_PATH, "utf8"));
  } catch (error) {
    throw new Error(`Failed to parse ${MANIFEST_PATH}: ${error.message}`);
  }
}

function selectVariables(manifest, environment) {
  return manifest.variables.filter(
    (variable) => variable.platforms.includes("supabase") && variable.environments.includes(environment),
  );
}

function printPlan(variables, environment, branch, apply) {
  const action = apply ? "sync" : "would sync";

  if (variables.length === 0) {
    console.log(`No Supabase variables declared for ${environment} branch ${branch}.`);
    return;
  }

  for (const variable of variables) {
    const present = Boolean(process.env[variable.name]);
    console.log(`${action} ${variable.name} to Supabase ${environment} branch ${branch}: ${present ? "present" : "missing"}`);
  }
}

try {
  const { apply, branch, environment } = parseArgs(process.argv.slice(2));
  const manifest = readManifest();
  const variables = selectVariables(manifest, environment);

  printPlan(variables, environment, branch, apply);

  if (apply) {
    if (!process.env.SUPABASE_ACCESS_TOKEN || !process.env.SUPABASE_PROJECT_ID) {
      throw new Error("Missing SUPABASE_ACCESS_TOKEN or SUPABASE_PROJECT_ID for apply mode");
    }

    throw new Error(
      "Live Supabase branch secret sync is not implemented yet. Re-run without --apply or implement Supabase API/CLI calls before applying changes.",
    );
  }
} catch (error) {
  console.error(error.message);
  process.exit(1);
}
