import type { NicheQueryInput, StandardSurfaceResponse } from "@/lib/niche-finder/types";

async function safeJson(response: Response): Promise<StandardSurfaceResponse | null> {
  try {
    return (await response.json()) as StandardSurfaceResponse;
  } catch {
    return null;
  }
}

export async function fetchStandardScore(
  input: NicheQueryInput
): Promise<StandardSurfaceResponse> {
  const response = await fetch("/api/agent/scoring", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });

  const data = await safeJson(response);

  if (!response.ok || !data) {
    return {
      query: input,
      score_result: { opportunity_score: 0, classification_label: "Low" },
      status: data?.status ?? "unavailable",
      message: data?.message ?? `Scoring unavailable (HTTP ${response.status}).`,
    };
  }

  return data;
}
