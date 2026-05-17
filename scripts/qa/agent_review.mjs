#!/usr/bin/env node

import { existsSync, readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { relative, resolve } from "node:path";
import { spawnSync } from "node:child_process";

const VALID_PROVIDERS = new Set(["codex", "claude"]);
const VALID_SEVERITIES = new Set(["blocker", "major", "minor", "polish"]);
const REVIEW_OUTPUT = "visual-qa-review.json";
const PROMPT_PATH = resolve("scripts", "qa", "prompts", "visual-designer-review.md");
const MAX_MANIFEST_ENTRIES = 250;

function readFlagValue(argv, index, flagName) {
  const value = argv[index + 1];

  if (!value || value.startsWith("--")) {
    throw new Error(`Missing value for ${flagName}`);
  }

  return value;
}

function parseArgs(argv) {
  const parsed = {
    artifacts: undefined,
    dryRun: false,
    mockProviderJson: undefined,
    provider: "codex",
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];

    if (arg === "--dry-run") {
      parsed.dryRun = true;
      continue;
    }

    if (arg === "--artifacts") {
      parsed.artifacts = readFlagValue(argv, index, arg);
      index += 1;
      continue;
    }

    if (arg === "--provider") {
      parsed.provider = readFlagValue(argv, index, arg);
      index += 1;
      continue;
    }

    if (arg === "--mock-provider-json") {
      parsed.mockProviderJson = readFlagValue(argv, index, arg);
      index += 1;
      continue;
    }

    throw new Error(`Unknown argument: ${arg}`);
  }

  if (!VALID_PROVIDERS.has(parsed.provider)) {
    throw new Error("Invalid --provider value. Expected codex or claude.");
  }

  if (!parsed.artifacts) {
    throw new Error("Missing --artifacts");
  }

  return parsed;
}

function tokenizeCommand(command) {
  const tokens = [];
  let current = "";
  let quote = undefined;

  for (let index = 0; index < command.length; index += 1) {
    const char = command[index];

    if (quote) {
      if (char === quote) {
        quote = undefined;
      } else {
        current += char;
      }
      continue;
    }

    if (char === "'" || char === "\"") {
      quote = char;
      continue;
    }

    if (/\s/.test(char)) {
      if (current) {
        tokens.push(current);
        current = "";
      }
      continue;
    }

    current += char;
  }

  if (quote) {
    throw new Error("Provider command contains an unterminated quote");
  }

  if (current) {
    tokens.push(current);
  }

  if (tokens.length === 0) {
    throw new Error("Provider command is empty");
  }

  return tokens;
}

function providerCommand(provider) {
  if (provider === "codex") {
    return tokenizeCommand(process.env.CODEX_QA_COMMAND || "codex exec");
  }

  return tokenizeCommand(process.env.CLAUDE_QA_COMMAND || "claude -p");
}

function copyEnvValue(env, key) {
  if (process.env[key]) {
    env[key] = process.env[key];
  }
}

function providerEnv(provider) {
  const env = {};

  for (const key of ["PATH", "HOME", "TMPDIR", "TEMP", "TMP"]) {
    copyEnvValue(env, key);
  }

  if (provider === "codex") {
    copyEnvValue(env, "OPENAI_API_KEY");
  } else {
    copyEnvValue(env, "ANTHROPIC_API_KEY");
  }

  return env;
}

function redactedProviderStderr(provider, stderr) {
  if (!stderr) {
    return "";
  }

  const secretKey = provider === "codex" ? "OPENAI_API_KEY" : "ANTHROPIC_API_KEY";
  const secretValue = process.env[secretKey];

  if (!secretValue) {
    return stderr;
  }

  return stderr.split(secretValue).join("[redacted]");
}

function shouldSkipManifestEntry(filePath) {
  const normalized = filePath.toLowerCase();

  return (
    normalized.includes(".env") ||
    normalized.includes("secret") ||
    normalized.includes("token") ||
    normalized.includes("credential")
  );
}

function buildManifest(rootDir) {
  const root = resolve(rootDir);

  if (!existsSync(root)) {
    throw new Error(`Artifacts directory does not exist: ${rootDir}`);
  }

  const entries = [];

  function walk(dir) {
    if (entries.length >= MAX_MANIFEST_ENTRIES) {
      return;
    }

    for (const name of readdirSync(dir).sort()) {
      const path = resolve(dir, name);
      const stats = statSync(path);

      if (stats.isDirectory()) {
        walk(path);
        continue;
      }

      const relPath = relative(process.cwd(), path);
      if (shouldSkipManifestEntry(relPath)) {
        continue;
      }

      entries.push({
        path: relPath,
        size_bytes: stats.size,
      });

      if (entries.length >= MAX_MANIFEST_ENTRIES) {
        break;
      }
    }
  }

  walk(root);

  return {
    artifact_root: relative(process.cwd(), root),
    entry_count: entries.length,
    truncated: entries.length >= MAX_MANIFEST_ENTRIES,
    entries,
  };
}

function reviewRequest(prompt, manifest) {
  return [
    prompt,
    "",
    "Artifact manifest:",
    JSON.stringify(manifest, null, 2),
    "",
    "Return only valid JSON matching the requested schema.",
  ].join("\n");
}

function extractJson(text) {
  const trimmed = text.trim();

  if (!trimmed) {
    throw new Error("Provider returned empty output");
  }

  try {
    return JSON.parse(trimmed);
  } catch {
    const start = trimmed.indexOf("{");
    const end = trimmed.lastIndexOf("}");

    if (start === -1 || end === -1 || end <= start) {
      throw new Error("Provider output did not contain a JSON object");
    }

    return JSON.parse(trimmed.slice(start, end + 1));
  }
}

function normalizeReview(review) {
  if (!review || typeof review !== "object" || Array.isArray(review)) {
    throw new Error("Provider review must be a JSON object");
  }

  if (!isNonEmptyString(review.summary)) {
    throw new Error("Provider review is missing non-empty string summary");
  }

  if (!Array.isArray(review.findings)) {
    throw new Error("Provider review is missing findings array");
  }

  review.findings.forEach((finding, index) => validateFinding(finding, index));

  return {
    summary: review.summary.trim(),
    findings: review.findings,
  };
}

function isNonEmptyString(value) {
  return typeof value === "string" && value.trim().length > 0;
}

function validateFinding(finding, index) {
  if (!finding || typeof finding !== "object" || Array.isArray(finding)) {
    throw new Error(`Provider review finding ${index} must be an object`);
  }

  if (!VALID_SEVERITIES.has(finding.severity)) {
    throw new Error(
      `Provider review finding ${index} has invalid severity. Expected blocker, major, minor, or polish.`,
    );
  }

  for (const field of ["route", "viewport", "artifact", "title", "recommendation"]) {
    if (!isNonEmptyString(finding[field])) {
      throw new Error(`Provider review finding ${index} is missing non-empty string ${field}`);
    }

    finding[field] = finding[field].trim();
  }
}

function writeReview(review) {
  writeFileSync(REVIEW_OUTPUT, `${JSON.stringify(review, null, 2)}\n`);
}

try {
  const options = parseArgs(process.argv.slice(2));

  if (options.dryRun) {
    writeReview({ summary: "dry run", findings: [] });
    console.log(`Wrote ${REVIEW_OUTPUT}`);
    process.exit(0);
  }

  if (options.mockProviderJson) {
    const review = normalizeReview(extractJson(readFileSync(options.mockProviderJson, "utf8")));
    writeReview(review);
    console.log(`Wrote ${REVIEW_OUTPUT}`);
    process.exit(0);
  }

  const prompt = readFileSync(PROMPT_PATH, "utf8");
  const manifest = buildManifest(options.artifacts);
  const request = reviewRequest(prompt, manifest);
  const [command, ...commandArgs] = providerCommand(options.provider);
  const result = spawnSync(command, [...commandArgs, request], {
    encoding: "utf8",
    env: providerEnv(options.provider),
    maxBuffer: 10 * 1024 * 1024,
  });

  if (result.error) {
    throw new Error(`Failed to run ${options.provider} review command: ${result.error.message}`);
  }

  if (typeof result.status === "number" && result.status !== 0) {
    const stderr = redactedProviderStderr(options.provider, result.stderr);
    const detail = stderr ? `: ${stderr.slice(0, 500)}` : "";
    throw new Error(`${options.provider} review command failed with status ${result.status}${detail}`);
  }

  if (result.signal) {
    throw new Error(`${options.provider} review command terminated by signal ${result.signal}`);
  }

  const review = normalizeReview(extractJson(result.stdout));
  writeReview(review);
  console.log(`Wrote ${REVIEW_OUTPUT}`);
} catch (error) {
  console.error(error.message);
  process.exit(1);
}
