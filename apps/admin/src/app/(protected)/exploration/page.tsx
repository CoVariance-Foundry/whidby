"use client";

import { useState } from "react";
import EvidencePanel from "@/components/niche-finder/EvidencePanel";
import ExplorationAssistantPanel from "@/components/niche-finder/ExplorationAssistantPanel";
import ExplorationQueryForm from "@/components/niche-finder/ExplorationQueryForm";
import ExplorationScoreSummary from "@/components/niche-finder/ExplorationScoreSummary";
import StandardSurfaceState from "@/components/niche-finder/StandardSurfaceState";
import type { ExplorationSurfaceResponse } from "@/lib/niche-finder/exploration-types";
import { loadQueryContext, saveQueryContext } from "@/lib/niche-finder/session-context";
import type { NicheQueryInput } from "@/lib/niche-finder/types";

const DEFAULT_QUERY: NicheQueryInput = {
  city: "Phoenix",
  service: "roofing",
};

async function fetchExploration(query: NicheQueryInput): Promise<ExplorationSurfaceResponse> {
  const response = await fetch("/api/agent/exploration", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(query),
  });

  return (await response.json()) as ExplorationSurfaceResponse;
}

export default function ExplorationPage() {
  const [query, setQuery] = useState<NicheQueryInput>(() => {
    return loadQueryContext() ?? DEFAULT_QUERY;
  });
  const [exploration, setExploration] = useState<ExplorationSurfaceResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(nextQuery: NicheQueryInput) {
    setLoading(true);
    setError(null);
    setExploration(null);
    setQuery(nextQuery);
    saveQueryContext(nextQuery);

    try {
      const explorationResponse = await fetchExploration(nextQuery);

      if (
        explorationResponse.status === "validation_error" ||
        explorationResponse.status === "unavailable"
      ) {
        setError(
          explorationResponse.message ?? "Unable to load exploration data."
        );
        return;
      }

      setExploration(explorationResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error — please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-4 px-6 py-6">
      <header>
        <h1 className="text-xl font-semibold">Niche Finder Exploration</h1>
        <p className="text-sm text-[var(--color-text-muted)]">
          Inspect raw evidence behind the score and run guided follow-up exploration.
        </p>
      </header>

      <ExplorationQueryForm initialQuery={query} onSubmit={handleSubmit} disabled={loading} />

      {!exploration ? (
        <StandardSurfaceState loading={loading} error={error} />
      ) : (
        <>
          <ExplorationScoreSummary result={exploration} />
          <EvidencePanel evidence={exploration.evidence} />
          <ExplorationAssistantPanel queryContext={query} />
        </>
      )}
    </div>
  );
}
