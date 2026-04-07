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
      responseId: crypto.randomUUID(),
      sessionId: input.sessionId,
      queryContext: input.queryContext,
      answer: "Exploration assistant is unavailable right now. Please try again.",
      evidenceReferences: [],
      status: "unsupported",
    };
  }
  return data;
}
