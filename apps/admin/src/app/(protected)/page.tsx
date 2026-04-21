"use client";

import { useState } from "react";
import StandardNicheForm from "@/components/niche-finder/StandardNicheForm";
import StandardScoreResult from "@/components/niche-finder/StandardScoreResult";
import StandardSurfaceState from "@/components/niche-finder/StandardSurfaceState";
import { loadQueryContext, saveQueryContext } from "@/lib/niche-finder/session-context";
import { fetchStandardScore } from "@/lib/niche-finder/standard-surface-service";
import type { NicheQueryInput, StandardSurfaceResponse } from "@/lib/niche-finder/types";

const DEFAULT_QUERY: NicheQueryInput = {
  city: "Phoenix",
  service: "roofing",
};

export default function Home() {
  const [query, setQuery] = useState<NicheQueryInput>(() => {
    return loadQueryContext() ?? DEFAULT_QUERY;
  });
  const [result, setResult] = useState<StandardSurfaceResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(nextQuery: NicheQueryInput) {
    setLoading(true);
    setError(null);
    setQuery(nextQuery);
    saveQueryContext(nextQuery);

    const response = await fetchStandardScore(nextQuery);
    if (response.status !== "success") {
      setResult(null);
      setError(response.message ?? "Unable to calculate score.");
      setLoading(false);
      return;
    }

    setResult(response);
    setLoading(false);
  }

  return (
    <div className="mx-auto max-w-4xl space-y-4 px-6 py-6">
      <header>
        <h1 className="text-xl font-semibold">Niche Finder</h1>
        <p className="text-sm text-[var(--color-text-muted)]">
          Submit a city and service to generate an opportunity score.
        </p>
      </header>

      <StandardNicheForm initialQuery={query} onSubmit={handleSubmit} disabled={loading} />

      {result ? (
        <StandardScoreResult result={result} />
      ) : (
        <StandardSurfaceState loading={loading} error={error} />
      )}
    </div>
  );
}
