import { createClient } from '@vercel/edge-config';

const edgeConfig = createClient(process.env.EDGE_CONFIG);

export async function getFlag(key: string, defaultValue: boolean = false): Promise<boolean> {
  try {
    const value = await edgeConfig.get<boolean>(key);
    return value ?? defaultValue;
  } catch {
    return defaultValue;
  }
}
