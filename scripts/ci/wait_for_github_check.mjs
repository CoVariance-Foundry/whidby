#!/usr/bin/env node

const DEFAULT_TIMEOUT_MS = 10 * 60 * 1000;
const DEFAULT_INTERVAL_MS = 10 * 1000;
const DEFAULT_REQUEST_TIMEOUT_MS = 15_000;
const TERMINAL_CHECK_CONCLUSIONS = new Set(["success", "failure", "cancelled", "timed_out"]);
const TERMINAL_STATUS_STATES = new Set(["success", "failure", "error"]);

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
    checkName: undefined,
    dryRun: false,
    intervalMs: DEFAULT_INTERVAL_MS,
    repo: undefined,
    requestTimeoutMs: DEFAULT_REQUEST_TIMEOUT_MS,
    sha: undefined,
    timeoutMs: DEFAULT_TIMEOUT_MS,
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];

    if (arg === "--dry-run") {
      parsed.dryRun = true;
      continue;
    }

    if (arg === "--check-name") {
      parsed.checkName = readFlagValue(argv, index, arg);
      index += 1;
      continue;
    }

    if (arg === "--repo") {
      parsed.repo = readFlagValue(argv, index, arg);
      index += 1;
      continue;
    }

    if (arg === "--sha") {
      parsed.sha = readFlagValue(argv, index, arg);
      index += 1;
      continue;
    }

    if (arg === "--request-timeout-ms") {
      parsed.requestTimeoutMs = parsePositiveInteger(readFlagValue(argv, index, arg), arg);
      index += 1;
      continue;
    }

    if (arg === "--timeout-ms") {
      parsed.timeoutMs = parsePositiveInteger(readFlagValue(argv, index, arg), arg);
      index += 1;
      continue;
    }

    if (arg === "--interval-ms") {
      parsed.intervalMs = parsePositiveInteger(readFlagValue(argv, index, arg), arg);
      index += 1;
      continue;
    }

    throw new Error(`Unknown argument: ${arg}`);
  }

  if (!parsed.checkName) {
    throw new Error("Missing --check-name");
  }

  if (!parsed.repo) {
    throw new Error("Missing --repo owner/name");
  }

  if (!/^[^/\s]+\/[^/\s]+$/.test(parsed.repo)) {
    throw new Error("Invalid --repo value. Expected owner/name.");
  }

  if (!parsed.sha) {
    throw new Error("Missing --sha");
  }

  return parsed;
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

async function githubRequest(path, token, requestTimeoutMs) {
  const response = await fetchWithTimeout(
    `https://api.github.com${path}`,
    {
      headers: {
        Accept: "application/vnd.github+json",
        Authorization: `Bearer ${token}`,
        "User-Agent": "whidby-ci-wait-for-github-check",
        "X-GitHub-Api-Version": "2022-11-28",
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

  return response.json();
}

async function fetchCheckRuns(repo, sha, token, requestTimeoutMs) {
  const encodedRepo = encodeURIComponent(repo).replace("%2F", "/");
  const path = `/repos/${encodedRepo}/commits/${encodeURIComponent(sha)}/check-runs?per_page=100`;
  const payload = await githubRequest(path, token, requestTimeoutMs);
  return Array.isArray(payload.check_runs) ? payload.check_runs : [];
}

async function fetchStatuses(repo, sha, token, requestTimeoutMs) {
  const encodedRepo = encodeURIComponent(repo).replace("%2F", "/");
  const path = `/repos/${encodedRepo}/commits/${encodeURIComponent(sha)}/status`;
  const payload = await githubRequest(path, token, requestTimeoutMs);
  return Array.isArray(payload.statuses) ? payload.statuses : [];
}

function findTarget(checkRuns, statuses, checkName) {
  const checkRun = checkRuns.find((run) => run.name === checkName);
  if (checkRun) {
    return {
      kind: "check run",
      name: checkRun.name,
      status: checkRun.status,
      conclusion: checkRun.conclusion,
    };
  }

  const status = statuses.find((item) => item.context === checkName);
  if (status) {
    return {
      kind: "commit status",
      name: status.context,
      state: status.state,
    };
  }

  return undefined;
}

function evaluateTarget(target) {
  if (!target) {
    return { done: false, ok: false, message: "not found yet" };
  }

  if (target.kind === "check run") {
    if (target.conclusion && TERMINAL_CHECK_CONCLUSIONS.has(target.conclusion)) {
      return {
        done: true,
        ok: target.conclusion === "success",
        message: `${target.kind} ${target.name} concluded ${target.conclusion}`,
      };
    }

    return { done: false, ok: false, message: `${target.kind} ${target.name} is ${target.status}` };
  }

  if (TERMINAL_STATUS_STATES.has(target.state)) {
    return {
      done: true,
      ok: target.state === "success",
      message: `${target.kind} ${target.name} is ${target.state}`,
    };
  }

  return { done: false, ok: false, message: `${target.kind} ${target.name} is ${target.state}` };
}

function sleep(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

async function waitForCheck(options) {
  const token = process.env.GITHUB_TOKEN;
  if (!token) {
    throw new Error("Missing GITHUB_TOKEN for live GitHub check polling");
  }

  const startedAt = Date.now();
  const expiresAt = startedAt + options.timeoutMs;

  while (Date.now() <= expiresAt) {
    const [checkRuns, statuses] = await Promise.all([
      fetchCheckRuns(options.repo, options.sha, token, options.requestTimeoutMs),
      fetchStatuses(options.repo, options.sha, token, options.requestTimeoutMs),
    ]);
    const target = findTarget(checkRuns, statuses, options.checkName);
    const result = evaluateTarget(target);

    console.log(result.message);

    if (result.done) {
      if (result.ok) {
        return;
      }

      throw new Error(`GitHub check did not succeed: ${result.message}`);
    }

    const remainingMs = expiresAt - Date.now();
    if (remainingMs <= 0) {
      break;
    }

    await sleep(Math.min(options.intervalMs, remainingMs));
  }

  throw new Error(`Timed out waiting for ${options.checkName} on ${options.repo}@${options.sha}`);
}

try {
  const options = parseArgs(process.argv.slice(2));

  if (options.dryRun) {
    console.log(`Dry run: would wait for ${options.checkName} on ${options.repo}@${options.sha}`);
    process.exit(0);
  }

  await waitForCheck(options);
} catch (error) {
  console.error(error.message);
  process.exit(1);
}
