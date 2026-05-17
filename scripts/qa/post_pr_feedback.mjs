#!/usr/bin/env node

import { readFileSync } from "node:fs";

const COMMENT_MARKER = "<!-- whidby-visual-qa -->";
const DEFAULT_REQUEST_TIMEOUT_MS = 15_000;
const SEVERITIES = ["blocker", "major", "minor", "polish"];

function readFlagValue(argv, index, flagName) {
  const value = argv[index + 1];

  if (!value || value.startsWith("--")) {
    throw new Error(`Missing value for ${flagName}`);
  }

  return value;
}

function parsePositiveInteger(value, flagName) {
  if (!/^\d+$/.test(value)) {
    throw new Error(`Invalid value for ${flagName}. Expected a positive integer.`);
  }

  const parsed = Number(value);
  if (!Number.isSafeInteger(parsed) || parsed <= 0) {
    throw new Error(`Invalid value for ${flagName}. Expected a positive integer.`);
  }

  return parsed;
}

function parseArgs(argv) {
  const parsed = {
    artifactUrl: undefined,
    dryRun: false,
    pr: undefined,
    repo: undefined,
    requestTimeoutMs: DEFAULT_REQUEST_TIMEOUT_MS,
    reviewJson: undefined,
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];

    if (arg === "--dry-run") {
      parsed.dryRun = true;
      continue;
    }

    if (arg === "--artifact-url") {
      parsed.artifactUrl = readFlagValue(argv, index, arg);
      index += 1;
      continue;
    }

    if (arg === "--pr") {
      parsed.pr = parsePositiveInteger(readFlagValue(argv, index, arg), arg);
      index += 1;
      continue;
    }

    if (arg === "--repo") {
      parsed.repo = readFlagValue(argv, index, arg);
      index += 1;
      continue;
    }

    if (arg === "--request-timeout-ms") {
      parsed.requestTimeoutMs = parsePositiveInteger(readFlagValue(argv, index, arg), arg);
      index += 1;
      continue;
    }

    if (arg === "--review-json") {
      parsed.reviewJson = readFlagValue(argv, index, arg);
      index += 1;
      continue;
    }

    throw new Error(`Unknown argument: ${arg}`);
  }

  if (!parsed.reviewJson) {
    throw new Error("Missing --review-json");
  }

  if (!parsed.artifactUrl) {
    throw new Error("Missing --artifact-url");
  }

  if (!parsed.repo) {
    throw new Error("Missing --repo owner/name");
  }

  if (!/^[^/\s]+\/[^/\s]+$/.test(parsed.repo)) {
    throw new Error("Invalid --repo value. Expected owner/name.");
  }

  if (!parsed.pr) {
    throw new Error("Missing --pr");
  }

  return parsed;
}

function loadReview(path) {
  const review = JSON.parse(readFileSync(path, "utf8"));

  if (!review || typeof review !== "object" || Array.isArray(review)) {
    throw new Error("Review JSON must be an object");
  }

  if (typeof review.summary !== "string") {
    throw new Error("Review JSON is missing string summary");
  }

  if (!Array.isArray(review.findings)) {
    throw new Error("Review JSON is missing findings array");
  }

  return review;
}

function severityCounts(findings) {
  const counts = Object.fromEntries(SEVERITIES.map((severity) => [severity, 0]));

  for (const finding of findings) {
    if (counts[finding?.severity] !== undefined) {
      counts[finding.severity] += 1;
    }
  }

  return counts;
}

function safeText(value, fallback = "unspecified") {
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}

function renderComment(review, artifactUrl) {
  const counts = severityCounts(review.findings);
  const countLine = SEVERITIES.map((severity) => `${severity}: ${counts[severity]}`).join(", ");
  const lines = [
    COMMENT_MARKER,
    "## Visual QA Review",
    "",
    review.summary,
    "",
    `Severity counts: ${countLine}`,
    "",
    `Artifacts: ${artifactUrl}`,
    "",
    "Findings:",
  ];

  if (review.findings.length === 0) {
    lines.push("- No findings.");
  } else {
    for (const finding of review.findings) {
      const severity = safeText(finding?.severity);
      const route = safeText(finding?.route);
      const viewport = safeText(finding?.viewport);
      const title = safeText(finding?.title, "Untitled finding");
      const artifact = safeText(finding?.artifact);
      const recommendation = safeText(finding?.recommendation, "No recommendation provided.");
      lines.push(`- [${severity}] ${title} (${route}, ${viewport})`);
      lines.push(`  Artifact: ${artifact}`);
      lines.push(`  Recommendation: ${recommendation}`);
    }
  }

  return `${lines.join("\n")}\n`;
}

async function fetchWithTimeout(url, init, timeoutMs, label) {
  const controller = new AbortController();
  const timeout = setTimeout(() => {
    controller.abort();
  }, timeoutMs);

  try {
    return await fetch(url, {
      ...init,
      signal: controller.signal,
    });
  } catch (error) {
    if (error?.name === "AbortError") {
      throw new Error(`${label} timed out after ${timeoutMs}ms`);
    }

    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

async function githubRequest(path, token, requestTimeoutMs, options = {}) {
  const response = await fetchWithTimeout(
    `https://api.github.com${path}`,
    {
      ...options,
      headers: {
        Accept: "application/vnd.github+json",
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
        "User-Agent": "whidby-visual-qa-feedback",
        "X-GitHub-Api-Version": "2022-11-28",
        ...options.headers,
      },
    },
    requestTimeoutMs,
    "GitHub API request",
  );

  if (!response.ok) {
    const body = await response.text();
    const detail = body ? `: ${body.slice(0, 300)}` : "";
    throw new Error(`GitHub API request failed with ${response.status}${detail}`);
  }

  if (response.status === 204) {
    return undefined;
  }

  return response.json();
}

async function findExistingComment(repo, pr, token, requestTimeoutMs) {
  const encodedRepo = encodeURIComponent(repo).replace("%2F", "/");

  for (let page = 1; ; page += 1) {
    const comments = await githubRequest(
      `/repos/${encodedRepo}/issues/${pr}/comments?per_page=100&page=${page}`,
      token,
      requestTimeoutMs,
    );

    if (!Array.isArray(comments) || comments.length === 0) {
      return undefined;
    }

    const existing = comments.find(
      (comment) => typeof comment.body === "string" && comment.body.includes(COMMENT_MARKER),
    );

    if (existing) {
      return existing;
    }

    if (comments.length < 100) {
      return undefined;
    }
  }
}

async function upsertComment(options, body) {
  const token = process.env.GITHUB_TOKEN;
  if (!token) {
    throw new Error("Missing GITHUB_TOKEN for live PR feedback posting");
  }

  const encodedRepo = encodeURIComponent(options.repo).replace("%2F", "/");
  const existing = await findExistingComment(options.repo, options.pr, token, options.requestTimeoutMs);

  if (existing) {
    await githubRequest(`/repos/${encodedRepo}/issues/comments/${existing.id}`, token, options.requestTimeoutMs, {
      body: JSON.stringify({ body }),
      method: "PATCH",
    });
    console.log(`Updated visual QA PR comment ${existing.id}`);
    return;
  }

  const created = await githubRequest(`/repos/${encodedRepo}/issues/${options.pr}/comments`, token, options.requestTimeoutMs, {
    body: JSON.stringify({ body }),
    method: "POST",
  });
  console.log(`Created visual QA PR comment ${created.id}`);
}

try {
  const options = parseArgs(process.argv.slice(2));
  const review = loadReview(options.reviewJson);
  const body = renderComment(review, options.artifactUrl);

  if (options.dryRun) {
    console.log(body);
    process.exit(0);
  }

  await upsertComment(options, body);
} catch (error) {
  console.error(error.message);
  process.exit(1);
}
