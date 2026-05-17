#!/usr/bin/env node

const DEFAULT_ALLOWED_SUFFIXES = [".vercel.app"];

function readFlagValue(argv, index, flagName) {
  const value = argv[index + 1];

  if (!value || value.startsWith("--")) {
    throw new Error(`Missing value for ${flagName}`);
  }

  return value;
}

function splitList(value) {
  return (value || "")
    .split(",")
    .map((entry) => entry.trim().toLowerCase())
    .filter(Boolean);
}

function parseArgs(argv) {
  const parsed = {
    url: undefined,
    allowedHosts: splitList(process.env.VISUAL_QA_ALLOWED_HOSTS),
    allowedSuffixes: splitList(process.env.VISUAL_QA_ALLOWED_HOST_SUFFIXES),
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];

    if (arg === "--url") {
      parsed.url = readFlagValue(argv, index, arg);
      index += 1;
      continue;
    }

    if (arg === "--allowed-host") {
      parsed.allowedHosts.push(readFlagValue(argv, index, arg).toLowerCase());
      index += 1;
      continue;
    }

    if (arg === "--allowed-suffix") {
      parsed.allowedSuffixes.push(readFlagValue(argv, index, arg).toLowerCase());
      index += 1;
      continue;
    }

    throw new Error(`Unknown argument: ${arg}`);
  }

  if (!parsed.url) {
    throw new Error("Missing --url");
  }

  if (parsed.allowedHosts.length === 0 && parsed.allowedSuffixes.length === 0) {
    parsed.allowedSuffixes = DEFAULT_ALLOWED_SUFFIXES;
  }

  return parsed;
}

function hostMatchesSuffix(hostname, suffix) {
  const normalizedSuffix = suffix.startsWith(".") ? suffix : `.${suffix}`;

  return hostname.endsWith(normalizedSuffix) && hostname.length > normalizedSuffix.length;
}

function validatePreviewUrl(options) {
  let parsed;

  try {
    parsed = new URL(options.url);
  } catch {
    throw new Error("Preview URL is not a valid URL");
  }

  if (parsed.protocol !== "https:") {
    throw new Error("Preview URL must use https");
  }

  if (parsed.username || parsed.password) {
    throw new Error("Preview URL must not include credentials");
  }

  const hostname = parsed.hostname.toLowerCase();
  const allowed =
    options.allowedHosts.includes(hostname) ||
    options.allowedSuffixes.some((suffix) => hostMatchesSuffix(hostname, suffix));

  if (!allowed) {
    throw new Error(
      `Preview URL host ${hostname} is not allowlisted. Set VISUAL_QA_ALLOWED_HOSTS or VISUAL_QA_ALLOWED_HOST_SUFFIXES if this is an approved preview host.`,
    );
  }

  return parsed.origin;
}

try {
  const options = parseArgs(process.argv.slice(2));
  process.stdout.write(`${validatePreviewUrl(options)}\n`);
} catch (error) {
  console.error(error.message);
  process.exit(1);
}
