import type { NicheQueryInput, StandardSurfaceResponse } from "@/lib/niche-finder/types";

export async function fetchStandardScore(
  input: NicheQueryInput
): Promise<StandardSurfaceResponse> {
  const response = await fetch("/api/agent/scoring", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });

  const data = (await response.json()) as StandardSurfaceResponse;
  if (!response.ok) {
    return {
      ...data,
      status: data.status ?? "unavailable",
      message: data.message ?? "Unable to fetch score.",
    };
  }

  return data;
}
