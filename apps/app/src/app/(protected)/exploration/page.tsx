"use client";

import { useState } from "react";
import EvidencePanel from "@/components/niche-finder/EvidencePanel";
import ExplorationAssistantPanel from "@/components/niche-finder/ExplorationAssistantPanel";
import ExplorationQueryForm from "@/components/niche-finder/ExplorationQueryForm";
import ExplorationScoreSummary from "@/components/niche-finder/ExplorationScoreSummary";
import StandardSurfaceState from "@/components/niche-finder/StandardSurfaceState";
import type { ExplorationSurfaceResponse } from "@/lib/niche-finder/exploration-types";
import { compareScoreParity } from "@/lib/niche-finder/parity-guard";
import { loadQueryContext, saveQueryContext } from "@/lib/niche-finder/session-context";
import { fetchStandardScore } from "@/lib/niche-finder/standard-surface-service";
import type { NicheQueryInput, StandardSurfaceResponse } from "@/lib/niche-finder/types";

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
  const [standard, setStandard] = useState<StandardSurfaceResponse | null>(null);
  const [exploration, setExploration] = useState<ExplorationSurfaceResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(nextQuery: NicheQueryInput) {
    setLoading(true);
    setError(null);
    setQuery(nextQuery);
    saveQueryContext(nextQuery);

    const [standardResponse, explorationResponse] = await Promise.all([
      fetchStandardScore(nextQuery),
      fetchExploration(nextQuery),
    ]);

    if (standardResponse.status !== "success" || explorationResponse.status === "validation_error") {
      setError(
        standardResponse.message ??
          explorationResponse.message ??
          "Unable to load exploration data."
      );
      setLoading(false);
      return;
    }

    setStandard(standardResponse);
    setExploration(explorationResponse);
    setLoading(false);
  }

  const parity = compareScoreParity(standard, exploration);

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
          <div className="rounded-md border border-[var(--color-dark-border)] bg-[var(--color-dark-card)] p-3 text-sm">
            Score parity with standard surface:{" "}
            <span className={parity.isParity ? "text-green-400" : "text-yellow-400"}>
              {parity.isParity ? "Matched" : `Delta ${parity.delta}`}
            </span>
          </div>
          <EvidencePanel evidence={exploration.evidence} />
          <ExplorationAssistantPanel queryContext={query} />
        </>
      )}
    </div>
  );
}
