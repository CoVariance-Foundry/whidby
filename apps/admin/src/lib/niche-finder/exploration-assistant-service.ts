import type {
  ExplorationAssistantRequest,
  ExplorationAssistantResponse,
} from "@/lib/niche-finder/exploration-types";

export async function askExplorationAssistant(
  input: ExplorationAssistantRequest
): Promise<ExplorationAssistantResponse> {
  const response = await fetch("/api/agent/exploration-chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });

  const data = (await response.json()) as ExplorationAssistantResponse;
  if (!response.ok) {
    return {
      response_id: crypto.randomUUID(),
      session_id: input.session_id,
      query_context: input.query_context,
      answer: "Exploration assistant is unavailable right now. Please try again.",
      evidence_references: [],
      status: "unsupported",
    };
  }
  return data;
}
