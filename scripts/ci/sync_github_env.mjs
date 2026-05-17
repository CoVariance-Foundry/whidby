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
    apply: false,
    environment: undefined,
    repo: undefined,
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];

    if (arg === "--apply") {
      parsed.apply = true;
      continue;
    }

    if (arg === "--environment") {
      parsed.environment = readFlagValue(argv, index, arg);
      index += 1;
      continue;
    }

    if (arg === "--repo") {
      parsed.repo = readFlagValue(argv, index, arg);
      index += 1;
      continue;
    }

    throw new Error(`Unknown argument: ${arg}`);
  }

  if (!parsed.environment || !ALLOWED_ENVIRONMENTS.has(parsed.environment)) {
    throw new Error("Missing or invalid --environment preview|staging|production");
  }

  if (parsed.repo && !/^[^/\s]+\/[^/\s]+$/.test(parsed.repo)) {
    throw new Error("Invalid --repo value. Expected owner/name.");
  }

  if (parsed.apply && !parsed.repo) {
    throw new Error("Missing --repo owner/name for apply mode");
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
    (variable) => variable.platforms.includes("github") && variable.environments.includes(environment),
  );
}

function printPlan(variables, environment, repo, apply) {
  const target = repo ? `GitHub ${repo} ${environment}` : `GitHub ${environment}`;
  const action = apply ? "sync" : "would sync";

  if (variables.length === 0) {
    const message = `No github variables configured for ${environment}`;

    if (!apply) {
      console.log(message);
      return;
    }

    throw new Error(`${message}; apply mode cannot sync an empty selection`);
  }

  for (const variable of variables) {
    const present = Boolean(process.env[variable.name]);
    console.log(`${action} ${variable.name} to ${target}: ${present ? "present" : "missing"}`);
  }
}

try {
  const { apply, environment, repo } = parseArgs(process.argv.slice(2));
  const manifest = readManifest();
  const variables = selectVariables(manifest, environment);

  printPlan(variables, environment, repo, apply);

  if (apply) {
    const token = process.env.GH_TOKEN || process.env.GITHUB_TOKEN;
    if (!token) {
      throw new Error("Missing GH_TOKEN or GITHUB_TOKEN for apply mode");
    }

    throw new Error(
      "Live GitHub environment sync is not implemented yet. Re-run without --apply or implement GitHub REST public-key encryption and upsert calls before applying changes.",
    );
  }
} catch (error) {
  console.error(error.message);
  process.exit(1);
}
