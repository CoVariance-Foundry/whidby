#!/usr/bin/env node
import fs from "node:fs";

const MANIFEST_PATH = "config/environments/manifest.json";
const KNOWN_PLATFORMS = new Set(["github", "vercel", "render", "supabase"]);
const KNOWN_KINDS = new Set(["public", "secret"]);
const PROVIDER_FLAGS = new Set(["--github", "--vercel", "--render", "--supabase"]);

const args = new Set(process.argv.slice(2));
const selectedProviders = [...PROVIDER_FLAGS].filter((flag) => args.has(flag));
const errors = [];

function readManifest() {
  try {
    return JSON.parse(fs.readFileSync(MANIFEST_PATH, "utf8"));
  } catch (error) {
    console.error(`Failed to parse ${MANIFEST_PATH}: ${error.message}`);
    process.exit(1);
  }
}

function validateStringArray(variableName, key, value) {
  if (!Array.isArray(value) || value.length === 0) {
    errors.push(`${variableName} ${key} must be a non-empty array`);
    return [];
  }

  const invalidItems = value.filter((item) => typeof item !== "string" || item.length === 0);
  if (invalidItems.length > 0) {
    errors.push(`${variableName} ${key} must contain only non-empty strings`);
  }

  return value;
}

function validateManifest(manifest) {
  if (!manifest || typeof manifest !== "object" || Array.isArray(manifest)) {
    errors.push("manifest must be a JSON object");
    return;
  }

  if (!manifest.environments || typeof manifest.environments !== "object" || Array.isArray(manifest.environments)) {
    errors.push("manifest.environments must be an object");
    return;
  }

  if (!Array.isArray(manifest.variables)) {
    errors.push("manifest.variables must be an array");
    return;
  }

  const knownEnvironments = new Set(Object.keys(manifest.environments));
  if (knownEnvironments.size === 0) {
    errors.push("manifest.environments must define at least one environment");
  }

  for (const variable of manifest.variables) {
    const variableName = typeof variable?.name === "string" && variable.name.length > 0 ? variable.name : "<unnamed>";

    if (!variable || typeof variable !== "object" || Array.isArray(variable)) {
      errors.push(`${variableName} must be an object`);
      continue;
    }

    for (const key of ["name", "kind", "platforms", "environments"]) {
      if (!(key in variable)) {
        errors.push(`${variableName} missing ${key}`);
      }
    }

    if (typeof variable.name !== "string" || variable.name.length === 0) {
      errors.push(`${variableName} name must be a non-empty string`);
    }

    if (!KNOWN_KINDS.has(variable.kind)) {
      errors.push(`${variableName} kind must be one of: ${[...KNOWN_KINDS].join(", ")}`);
    }

    if (variable.kind === "secret" && variable.name?.startsWith("NEXT_PUBLIC_")) {
      errors.push(`${variable.name} is marked secret but is public by naming convention`);
    }

    const platforms = validateStringArray(variableName, "platforms", variable.platforms);
    const environments = validateStringArray(variableName, "environments", variable.environments);

    for (const platform of platforms) {
      if (!KNOWN_PLATFORMS.has(platform)) {
        errors.push(`${variableName} references unknown platform: ${platform}`);
      }
    }

    for (const environment of environments) {
      if (!knownEnvironments.has(environment)) {
        errors.push(`${variableName} references unknown environment: ${environment}`);
      }
    }
  }
}

function printRequiredMatrix(manifest) {
  for (const variable of manifest.variables) {
    console.log(
      `${variable.name}: ${variable.kind} -> ${variable.platforms.join(",")} / ${variable.environments.join(",")}`,
    );
  }
}

const manifest = readManifest();
validateManifest(manifest);

if (errors.length > 0) {
  console.error(errors.join("\n"));
  process.exit(1);
}

if (args.has("--offline")) {
  printRequiredMatrix(manifest);
  process.exit(0);
}

if (selectedProviders.length > 0) {
  const providers = selectedProviders.map((flag) => flag.slice(2)).join(", ");
  console.log(`Live checks for ${providers} are not implemented yet; manifest validation passed.`);
  process.exit(0);
}

console.log("Manifest validation passed. Use --offline to print the required matrix or provider flags for future live checks.");
