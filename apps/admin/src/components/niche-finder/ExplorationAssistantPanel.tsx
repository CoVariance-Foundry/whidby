"use client";

import { useState } from "react";
import type { NicheQueryInput } from "@/lib/niche-finder/types";
import type { ExplorationAssistantResponse } from "@/lib/niche-finder/exploration-types";
import { askExplorationAssistant } from "@/lib/niche-finder/exploration-assistant-service";
import AssistantFallbackState from "@/components/niche-finder/AssistantFallbackState";

interface ExplorationAssistantPanelProps {
  queryContext: NicheQueryInput;
}

export default function ExplorationAssistantPanel({
  queryContext,
}: ExplorationAssistantPanelProps) {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<ExplorationAssistantResponse | null>(null);

  async function handleSubmit() {
    if (!question.trim() || loading) return;

    setLoading(true);
    const next = await askExplorationAssistant({
      session_id: "exploration-session",
      query_context: queryContext,
      question,
    });
    setResponse(next);
    setLoading(false);
  }

  return (
    <section className="rounded-lg border border-[var(--color-dark-border)] bg-[var(--color-dark-card)] p-4">
      <h2 className="text-sm font-semibold">Exploration Assistant</h2>
      <p className="mt-1 text-xs text-[var(--color-text-muted)]">
        Ask follow-up questions for {queryContext.city} - {queryContext.service}.
      </p>

      <div className="mt-3 flex gap-2">
        <input
          data-testid="assistant-input"
          className="flex-1 rounded-md border border-[var(--color-dark-border)] bg-[var(--color-dark)] px-3 py-2 text-sm"
          placeholder="What evidence supports this score?"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
        />
        <button
          data-testid="assistant-ask-btn"
          onClick={handleSubmit}
          disabled={loading}
          className="rounded-md bg-[var(--color-accent)] px-3 py-2 text-sm font-medium text-white hover:bg-[var(--color-accent-dark)] disabled:opacity-60"
        >
          {loading ? "Asking..." : "Ask"}
        </button>
      </div>

      {response && (
        <div className="mt-3 space-y-2">
          {response.status === "unsupported" ? (
            <AssistantFallbackState message={response.answer} />
          ) : (
            <div data-testid="assistant-answer" className="rounded-md border border-[var(--color-dark-border)] bg-[var(--color-dark)] p-3 text-sm text-[var(--color-text-primary)]">
              {response.answer}
            </div>
          )}
          {response.evidence_references.length > 0 && (
            <div data-testid="evidence-references" className="rounded-md border border-[var(--color-dark-border)] bg-[var(--color-dark)] p-3">
              <p className="text-xs uppercase tracking-wide text-[var(--color-text-muted)]">
                Evidence References
              </p>
              <ul className="mt-2 space-y-1 text-sm text-[var(--color-text-secondary)]">
                {response.evidence_references.map((item) => (
                  <li key={`${item.category}-${item.reference_label}`}>
                    {item.category}: {item.reference_label}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
