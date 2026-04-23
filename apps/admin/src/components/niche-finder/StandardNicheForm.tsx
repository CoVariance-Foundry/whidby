"use client";

import { useState } from "react";
import CityAutocomplete from "@/components/niche-finder/CityAutocomplete";
import type { PlaceSuggestion } from "@/lib/niche-finder/place-suggest";
import type { NicheQueryInput } from "@/lib/niche-finder/types";

interface StandardNicheFormProps {
  initialQuery: NicheQueryInput;
  onSubmit: (query: NicheQueryInput) => void;
  disabled?: boolean;
}

export default function StandardNicheForm({
  initialQuery,
  onSubmit,
  disabled = false,
}: StandardNicheFormProps) {
  const [city, setCity] = useState(initialQuery.city);
  const [service, setService] = useState(initialQuery.service);
  const [state, setState] = useState<string | undefined>(initialQuery.state);
  const [placeId, setPlaceId] = useState<string | undefined>(initialQuery.place_id);
  const [dataforseoLocationCode, setDataforseoLocationCode] = useState<number | undefined>(
    initialQuery.dataforseo_location_code,
  );

  function handleCityChange(text: string, suggestion?: PlaceSuggestion) {
    if (suggestion) {
      // User picked from the dropdown — capture both city and state.
      setCity(suggestion.city);
      const normalizedRegion = suggestion.region?.trim().toUpperCase();
      setState(normalizedRegion && normalizedRegion.length === 2 ? normalizedRegion : undefined);
      setPlaceId(suggestion.place_id?.trim() || undefined);
      setDataforseoLocationCode(
        typeof suggestion.dataforseo_location_code === "number"
          ? suggestion.dataforseo_location_code
          : undefined,
      );
    } else {
      // Free-typed edit — update city and clear any previously resolved state
      // so we never send a mismatched city+state pair.
      if (text !== city) {
        setState(undefined);
        setPlaceId(undefined);
        setDataforseoLocationCode(undefined);
      }
      setCity(text);
    }
  }

  return (
    <form
      className="grid gap-3 rounded-lg border border-[var(--color-dark-border)] bg-[var(--color-dark-card)] p-4 md:grid-cols-3"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit({
          city,
          service,
          ...(state ? { state } : {}),
          ...(placeId ? { place_id: placeId } : {}),
          ...(typeof dataforseoLocationCode === "number"
            ? { dataforseo_location_code: dataforseoLocationCode }
            : {}),
        });
      }}
    >
      <CityAutocomplete
        data-testid="city-input"
        value={city}
        onChange={handleCityChange}
        disabled={disabled}
        placeholder="City (e.g. Phoenix)"
      />
      <input
        data-testid="service-input"
        className="rounded-md border border-[var(--color-dark-border)] bg-[var(--color-dark)] px-3 py-2 text-sm"
        placeholder="Service (e.g. roofing)"
        value={service}
        onChange={(event) => setService(event.target.value)}
        disabled={disabled}
      />
      <button
        data-testid="score-niche-btn"
        type="submit"
        disabled={disabled}
        className="rounded-md bg-[var(--color-accent)] px-3 py-2 text-sm font-medium text-white hover:bg-[var(--color-accent-dark)] disabled:cursor-not-allowed disabled:opacity-60"
      >
        Score Niche
      </button>
    </form>
  );
}
