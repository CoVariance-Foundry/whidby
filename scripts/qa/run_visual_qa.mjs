#!/usr/bin/env node

import { existsSync, cpSync, mkdirSync } from "node:fs";
import { resolve, sep } from "node:path";
import { spawnSync } from "node:child_process";

const VALID_APPS = new Set(["app", "admin"]);
const DEFAULT_SHA = "local";
const SAFE_ARTIFACT_ID = /^[A-Za-z0-9._-]+$/;

function readFlagValue(argv, index, flagName) {
  const value = argv[index + 1];

  if (!value || value.startsWith("--")) {
    throw new Error(`Missing value for ${flagName}`);
  }

  return value;
}

function parseArgs(argv) {
  const parsed = {
    app: undefined,
    baseUrl: undefined,
    sha: DEFAULT_SHA,
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];

    if (arg === "--app") {
      parsed.app = readFlagValue(argv, index, arg);
      index += 1;
      continue;
    }

    if (arg === "--base-url") {
      parsed.baseUrl = readFlagValue(argv, index, arg);
      index += 1;
      continue;
    }

    if (arg === "--sha") {
      parsed.sha = readFlagValue(argv, index, arg);
      index += 1;
      continue;
    }

    throw new Error(`Unknown argument: ${arg}`);
  }

  if (!parsed.app) {
    throw new Error("Missing --app app|admin");
  }

  if (!VALID_APPS.has(parsed.app)) {
    throw new Error("Invalid --app value. Expected app or admin.");
  }

  if (!parsed.baseUrl) {
    throw new Error("Missing --base-url <url>");
  }

  validateArtifactId(parsed.sha);

  return parsed;
}

function validateArtifactId(value) {
  if (typeof value !== "string" || value.length === 0) {
    throw new Error("Invalid --sha value. Expected a non-empty artifact id.");
  }

  if (
    value === "." ||
    value.includes("..") ||
    value.includes("/") ||
    value.includes("\\") ||
    !SAFE_ARTIFACT_ID.test(value)
  ) {
    throw new Error("Invalid --sha value. Use only letters, numbers, dots, underscores, and dashes.");
  }
}

function resolveArtifactDir(app, artifactId) {
  const artifactRoot = resolve("artifacts", "visual-qa", app);
  const artifactDir = resolve(artifactRoot, artifactId);
  const rootPrefix = `${artifactRoot}${sep}`;

  if (!artifactDir.startsWith(rootPrefix)) {
    throw new Error("Resolved artifact directory escapes the visual QA artifact root.");
  }

  return artifactDir;
}

function copyIfPresent(source, destination) {
  if (!existsSync(source)) {
    return false;
  }

  cpSync(source, destination, {
    force: true,
    recursive: true,
  });

  return true;
}

function copyArtifacts(app, sha) {
  const artifactDir = resolveArtifactDir(app, sha);
  mkdirSync(artifactDir, { recursive: true });

  const sources = [
    {
      from: resolve("apps", app, "playwright-report"),
      to: resolve(artifactDir, "playwright-report"),
    },
    {
      from: resolve("apps", app, "test-results"),
      to: resolve(artifactDir, "test-results"),
    },
  ];

  const copied = sources
    .map((source) => copyIfPresent(source.from, source.to))
    .filter(Boolean).length;

  return { artifactDir, copied };
}

try {
  const options = parseArgs(process.argv.slice(2));
  const scriptName = `qa:visual:${options.app}`;
  const env = {
    ...process.env,
    PLAYWRIGHT_BASE_URL: options.baseUrl,
  };

  const result = spawnSync("npm", ["run", scriptName], {
    env,
    stdio: "inherit",
  });

  const { artifactDir, copied } = copyArtifacts(options.app, options.sha);
  console.log(`Visual QA artifacts: ${artifactDir}`);

  if (copied === 0) {
    console.warn("No Playwright artifacts found to copy.");
  }

  if (result.error) {
    throw result.error;
  }

  if (typeof result.status === "number" && result.status !== 0) {
    process.exit(result.status);
  }

  if (result.signal) {
    throw new Error(`Playwright command terminated by signal ${result.signal}`);
  }
} catch (error) {
  console.error(error.message);
  process.exit(1);
}
