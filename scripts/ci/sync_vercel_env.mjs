#!/usr/bin/env node
import fs from "node:fs";

const MANIFEST_PATH = "config/environments/manifest.json";
const ALLOWED_ENVIRONMENTS = new Set(["preview", "staging", "production"]);

function readFlagValue(argv, index, flagName) {
  const value = argv[index + 1];

  if (!value || value.startsWith("--")) {
    throw new Error(`Missing value for ${flagName}`);
  }

  return value;
}

function parseArgs(argv) {
  const parsed = {
    dryRun: false,
    environment: undefined,
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];

    if (arg === "--dry-run") {
      parsed.dryRun = true;
      continue;
    }

    if (arg === "--environment") {
      parsed.environment = readFlagValue(argv, index, arg);
      index += 1;
      continue;
    }

    throw new Error(`Unknown argument: ${arg}`);
  }

  if (!parsed.environment || !ALLOWED_ENVIRONMENTS.has(parsed.environment)) {
    throw new Error("Missing or invalid --environment preview|staging|production");
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
    (variable) => variable.platforms.includes("vercel") && variable.environments.includes(environment),
  );
}

function printPlan(variables, environment, dryRun) {
  if (variables.length === 0) {
    const message = `No vercel variables configured for ${environment}`;

    if (dryRun) {
      console.log(message);
      return;
    }

    throw new Error(`${message}; live sync cannot apply an empty selection`);
  }

  for (const variable of variables) {
    const present = Boolean(process.env[variable.name]);
    const action = dryRun ? "would sync" : "sync";
    console.log(`${action} ${variable.name} to Vercel ${environment}: ${present ? "present" : "missing"}`);
  }
}

try {
  const { dryRun, environment } = parseArgs(process.argv.slice(2));
  const manifest = readManifest();
  const variables = selectVariables(manifest, environment);

  printPlan(variables, environment, dryRun);

  if (!dryRun) {
    throw new Error(
      "Live Vercel environment sync is not implemented yet. Re-run with --dry-run or implement Vercel provider API calls before applying changes.",
    );
  }
} catch (error) {
  console.error(error.message);
  process.exit(1);
}
