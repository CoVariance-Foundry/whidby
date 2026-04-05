import { createClient, type EdgeConfigClient } from '@vercel/edge-config';

let edgeConfig: EdgeConfigClient | null = null;

function getClient(): EdgeConfigClient | null {
  if (edgeConfig) return edgeConfig;
  const connectionString = process.env.EDGE_CONFIG;
  if (!connectionString) {
    console.warn('[flags] EDGE_CONFIG not set — feature flags will use defaults');
    return null;
  }
  edgeConfig = createClient(connectionString);
  return edgeConfig;
}

export async function getFlag(key: string, defaultValue: boolean = false): Promise<boolean> {
  const client = getClient();
  if (!client) return defaultValue;
  try {
    const value = await client.get<boolean>(key);
    return value ?? defaultValue;
  } catch {
    return defaultValue;
  }
}
