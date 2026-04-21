"use client";

import { useState } from "react";
import CityAutocomplete from "@/components/niche-finder/CityAutocomplete";
import type { MetroSuggestion } from "@/lib/niche-finder/metro-suggest";
import type { NicheQueryInput } from "@/lib/niche-finder/types";

interface ExplorationQueryFormProps {
  initialQuery: NicheQueryInput;
  onSubmit: (query: NicheQueryInput) => void;
  disabled?: boolean;
}

export default function ExplorationQueryForm({
  initialQuery,
  onSubmit,
  disabled = false,
}: ExplorationQueryFormProps) {
  const [city, setCity] = useState(initialQuery.city);
  const [service, setService] = useState(initialQuery.service);
  const [state, setState] = useState<string | undefined>(initialQuery.state);

  function handleCityChange(text: string, suggestion?: MetroSuggestion) {
    if (suggestion) {
      // User picked from the dropdown — capture both city and state.
      setCity(suggestion.city);
      setState(suggestion.state);
    } else {
      // Free-typed edit — update city and clear any previously resolved state
      // so we never send a mismatched city+state pair.
      if (text !== city) {
        setState(undefined);
      }
      setCity(text);
    }
  }

  return (
    <form
      className="grid gap-3 rounded-lg border border-[var(--color-dark-border)] bg-[var(--color-dark-card)] p-4 md:grid-cols-3"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit({ city, service, ...(state ? { state } : {}) });
      }}
    >
      <CityAutocomplete
        data-testid="explore-city-input"
        value={city}
        onChange={handleCityChange}
        disabled={disabled}
        placeholder="City"
      />
      <input
        data-testid="explore-service-input"
        className="rounded-md border border-[var(--color-dark-border)] bg-[var(--color-dark)] px-3 py-2 text-sm"
        placeholder="Service"
        value={service}
        onChange={(event) => setService(event.target.value)}
        disabled={disabled}
      />
      <button
        data-testid="explore-btn"
        type="submit"
        disabled={disabled}
        className="rounded-md bg-[var(--color-accent)] px-3 py-2 text-sm font-medium text-white hover:bg-[var(--color-accent-dark)] disabled:cursor-not-allowed disabled:opacity-60"
      >
        Explore Score Inputs
      </button>
    </form>
  );
}
