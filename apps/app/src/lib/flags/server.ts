import { PostHog } from "posthog-node";

let posthog: PostHog | null = null;

function getPostHogClient(): PostHog | null {
  const key = process.env.NEXT_PUBLIC_POSTHOG_KEY ?? process.env.POSTHOG_KEY;
  if (!key) return null;

  if (!posthog) {
    posthog = new PostHog(key, {
      host:
        process.env.NEXT_PUBLIC_POSTHOG_HOST ??
        process.env.POSTHOG_HOST ??
        "https://us.i.posthog.com",
      flushAt: 1,
      flushInterval: 0,
    });
  }

  return posthog;
}

export async function getServerFeatureFlag(
  key: string,
  defaultValue: boolean,
  distinctId: string,
  properties: Record<string, string | number | boolean | null> = {},
): Promise<boolean> {
  const envOverride = readBooleanEnv(key);
  if (envOverride !== null) return envOverride;

  const client = getPostHogClient();
  if (!client) return defaultValue;

  try {
    const value = await client.getFeatureFlag(key, distinctId, {
      personProperties: stringifyProperties(properties),
    });
    return typeof value === "boolean" ? value : defaultValue;
  } catch (error) {
    console.warn("[posthog] feature flag fallback", {
      key,
      error: error instanceof Error ? error.message : String(error),
    });
    return defaultValue;
  }
}

function readBooleanEnv(key: string): boolean | null {
  const value = process.env[key.toUpperCase().replace(/-/g, "_")];
  if (!value) return null;

  const normalized = value.trim().toLowerCase();
  if (["1", "true", "yes", "on"].includes(normalized)) return true;
  if (["0", "false", "no", "off"].includes(normalized)) return false;
  return null;
}

function stringifyProperties(
  properties: Record<string, string | number | boolean | null>,
): Record<string, string> {
  return Object.fromEntries(
    Object.entries(properties)
      .filter((entry): entry is [string, string | number | boolean] => entry[1] !== null)
      .map(([key, value]) => [key, String(value)]),
  );
}

export function captureServerEvent(
  distinctId: string,
  event: string,
  properties: Record<string, string | number | boolean | null> = {},
) {
  const client = getPostHogClient();
  if (!client) return;

  try {
    client.capture({ distinctId, event, properties });
  } catch (error) {
    console.warn("[posthog] capture skipped", {
      event,
      error: error instanceof Error ? error.message : String(error),
    });
  }
}
