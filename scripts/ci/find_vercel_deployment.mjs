#!/usr/bin/env node

const DRY_RUN_URL = "https://example-preview.vercel.app";
const DEFAULT_REQUEST_TIMEOUT_MS = 15_000;
const READY_DEPLOYMENT_STATES = new Set(["READY"]);
const PREVIEW_TARGET_VALUES = new Set(["preview"]);

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
    dryRun: false,
    mock: false,
    projectId: undefined,
    requestTimeoutMs: DEFAULT_REQUEST_TIMEOUT_MS,
    sha: undefined,
    teamId: undefined,
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];

    if (arg === "--dry-run") {
      parsed.dryRun = true;
      continue;
    }

    if (arg === "--mock") {
      parsed.mock = true;
      continue;
    }

    if (arg === "--sha") {
      parsed.sha = readFlagValue(argv, index, arg);
      index += 1;
      continue;
    }

    if (arg === "--project-id") {
      parsed.projectId = readFlagValue(argv, index, arg);
      index += 1;
      continue;
    }

    if (arg === "--request-timeout-ms") {
      parsed.requestTimeoutMs = parsePositiveInteger(readFlagValue(argv, index, arg), arg);
      index += 1;
      continue;
    }

    if (arg === "--team-id") {
      parsed.teamId = readFlagValue(argv, index, arg);
      index += 1;
      continue;
    }

    throw new Error(`Unknown argument: ${arg}`);
  }

  if (!parsed.sha) {
    throw new Error("Missing --sha");
  }

  if (process.env.VERCEL_DEPLOYMENTS_MOCK_JSON && !parsed.mock && !parsed.dryRun) {
    throw new Error("VERCEL_DEPLOYMENTS_MOCK_JSON is set; pass --mock to use mocked deployments");
  }

  if (!parsed.dryRun && !parsed.mock && !parsed.projectId) {
    throw new Error("Missing --project-id for live Vercel deployment lookup");
  }

  if (!parsed.dryRun && !parsed.mock && !parsed.teamId) {
    throw new Error("Missing --team-id for live Vercel deployment lookup");
  }

  return parsed;
}

function deploymentUrl(deployment) {
  if (typeof deployment?.url !== "string" || deployment.url.length === 0) {
    return undefined;
  }

  return deployment.url.startsWith("https://") ? deployment.url : `https://${deployment.url}`;
}

function deploymentMatchesSha(deployment, sha) {
  return deployment?.meta?.githubCommitSha === sha;
}

function deploymentIsReady(deployment) {
  return READY_DEPLOYMENT_STATES.has(deployment?.state);
}

function deploymentTargetValues(deployment) {
  return [
    deployment?.target,
    deployment?.environment,
    deployment?.meta?.target,
    deployment?.meta?.environment,
    deployment?.meta?.vercelTarget,
    deployment?.meta?.VERCEL_ENV,
  ].filter((value) => typeof value === "string" && value.length > 0);
}

function deploymentIsPreviewTargeted(deployment) {
  const targetValues = deploymentTargetValues(deployment);

  // Fail closed: READY + matching SHA is not enough unless Vercel exposes preview metadata.
  return targetValues.some((value) => PREVIEW_TARGET_VALUES.has(value.toLowerCase()));
}

function deploymentIsSelectable(deployment, sha) {
  return (
    deploymentUrl(deployment) &&
    deploymentMatchesSha(deployment, sha) &&
    deploymentIsReady(deployment) &&
    deploymentIsPreviewTargeted(deployment)
  );
}

function findMatchingDeploymentUrl(deployments, sha) {
  const match = deployments.find((deployment) => deploymentIsSelectable(deployment, sha));

  return deploymentUrl(match);
}

function deploymentsFromMock() {
  if (!process.env.VERCEL_DEPLOYMENTS_MOCK_JSON) {
    return undefined;
  }

  const payload = JSON.parse(process.env.VERCEL_DEPLOYMENTS_MOCK_JSON);

  return Array.isArray(payload.deployments) ? payload.deployments : payload;
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

async function findDeployment(options) {
  if (options.mock) {
    const mockedDeployments = deploymentsFromMock();
    const deployments = Array.isArray(mockedDeployments) ? mockedDeployments : [];
    const url = findMatchingDeploymentUrl(deployments, options.sha);

    if (!url) {
      throw new Error(`No Vercel deployment found for commit ${options.sha}`);
    }

    return url;
  }

  const token = process.env.VERCEL_TOKEN;
  if (!token) {
    throw new Error("Missing VERCEL_TOKEN for live Vercel deployment lookup");
  }

  const params = new URLSearchParams({
    limit: "20",
    projectId: options.projectId,
    "meta-githubCommitSha": options.sha,
    teamId: options.teamId,
  });

  const response = await fetchWithTimeout(
    `https://api.vercel.com/v6/deployments?${params.toString()}`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    },
    options.requestTimeoutMs,
    "Vercel API request",
  );

  if (!response.ok) {
    const body = await response.text();
    const detail = body ? `: ${body.slice(0, 300)}` : "";
    throw new Error(`Vercel API request failed with ${response.status}${detail}`);
  }

  const payload = await response.json();
  const deployments = Array.isArray(payload.deployments) ? payload.deployments : [];
  const url = findMatchingDeploymentUrl(deployments, options.sha);

  if (!url) {
    throw new Error(`No Vercel deployment found for commit ${options.sha}`);
  }

  return url;
}

try {
  const options = parseArgs(process.argv.slice(2));

  if (options.dryRun) {
    console.log(DRY_RUN_URL);
    process.exit(0);
  }

  console.log(await findDeployment(options));
} catch (error) {
  console.error(error.message);
  process.exit(1);
}
