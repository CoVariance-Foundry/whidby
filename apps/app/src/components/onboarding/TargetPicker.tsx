"use client";

import { useState } from "react";
import CityAutocomplete from "@/components/niche-finder/CityAutocomplete";
import type { PlaceSuggestion } from "@/lib/niche-finder/place-suggest";
import type {
  OnboardingGeoScope,
  OnboardingMetadataSource,
} from "@/lib/onboarding/types";

export interface OnboardingTargetChoice {
  geo_scope: OnboardingGeoScope;
  city?: string;
  state?: string;
  cbsa_code?: string;
  place_id?: string;
  dataforseo_location_code?: number;
  resolved_label: string;
  metadata_source: OnboardingMetadataSource;
}

interface TargetPickerProps {
  serviceLabel: string;
  value: OnboardingTargetChoice | null;
  onSelect: (target: OnboardingTargetChoice) => void;
  onBack: () => void;
}

export default function TargetPicker({
  serviceLabel,
  value,
  onSelect,
  onBack,
}: TargetPickerProps) {
  const [mode, setMode] = useState<"city" | "broad">(
    value?.geo_scope && value.geo_scope !== "city" ? "broad" : "city",
  );
  const [cityInput, setCityInput] = useState(value?.resolved_label ?? value?.city ?? "");
  const [cityTarget, setCityTarget] = useState<OnboardingTargetChoice | null>(
    value?.geo_scope === "city" ? value : null,
  );
  const [broadScope, setBroadScope] = useState<"state" | "nationwide">(
    value?.geo_scope === "state" ? "state" : "nationwide",
  );
  const [stateValue, setStateValue] = useState(
    value?.geo_scope === "state" ? value.resolved_label : "",
  );

  const handleCityChange = (nextCity: string, suggestion?: PlaceSuggestion) => {
    setCityInput(nextCity);
    if (suggestion) {
      const normalizedState = suggestion.region?.trim().toUpperCase();
      const selected: OnboardingTargetChoice = {
        geo_scope: "city",
        city: suggestion.city,
        state:
          normalizedState && normalizedState.length === 2
            ? normalizedState
            : suggestion.region?.trim() || undefined,
        place_id: suggestion.place_id?.trim() || undefined,
        dataforseo_location_code:
          typeof suggestion.dataforseo_location_code === "number"
            ? suggestion.dataforseo_location_code
            : undefined,
        resolved_label: suggestion.region
          ? `${suggestion.city}, ${suggestion.region}`
          : suggestion.city,
        metadata_source:
          suggestion.enrichment_status === "fallback_cbsa"
            ? "fallback_cbsa"
            : "mapbox_selected",
      };
      setCityTarget(selected);
      return;
    }

    setCityTarget(
      nextCity.trim()
        ? {
            geo_scope: "city",
            city: nextCity.trim(),
            resolved_label: nextCity.trim(),
            metadata_source: "typed",
          }
        : null,
    );
  };

  const broadTarget =
    broadScope === "nationwide"
      ? {
          geo_scope: "nationwide" as const,
          resolved_label: "Nationwide",
          metadata_source: "typed" as const,
        }
      : stateValue.trim()
        ? {
            geo_scope: "state" as const,
            state: stateValue.trim(),
            resolved_label: stateValue.trim(),
            metadata_source: "typed" as const,
          }
        : null;

  const selectedTarget = mode === "city" ? cityTarget : broadTarget;

  return (
    <section aria-labelledby="target-heading">
      <button type="button" className="btn-ghost" onClick={onBack}>
        Back
      </button>

      <div style={{ marginTop: 18 }}>
        <p className="field-label">Step 3 of 4</p>
        <h1 id="target-heading" className="page-h1" style={{ margin: 0 }}>
          Choose the market.
        </h1>
        <p className="page-sub">
          City targets can start a fresh report when your plan includes it.
          Broad targets continue through cached Explore workflows.
        </p>
      </div>

      <div
        role="radiogroup"
        aria-label="Target type"
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
          gap: 10,
          marginTop: 24,
        }}
      >
        {[
          ["city", "One city", `Fresh ${serviceLabel} report`],
          ["broad", "Broad scan", "Cached Explore path"],
        ].map(([id, label, note]) => {
          const active = mode === id;
          return (
            <button
              key={id}
              type="button"
              role="radio"
              aria-checked={active}
              onClick={() => setMode(id as "city" | "broad")}
              style={{
                padding: 14,
                minHeight: 82,
                borderRadius: 8,
                textAlign: "left",
                border: `1px solid ${active ? "var(--accent)" : "var(--rule)"}`,
                background: active ? "var(--accent-soft)" : "var(--card)",
              }}
            >
              <span
                style={{
                  display: "block",
                  fontFamily: "var(--serif)",
                  fontSize: 17,
                  fontWeight: 600,
                }}
              >
                {label}
              </span>
              <span style={{ display: "block", marginTop: 5, fontSize: 12, color: "var(--ink-2)" }}>
                {note}
              </span>
            </button>
          );
        })}
      </div>

      <div style={{ marginTop: 20 }}>
        {mode === "city" ? (
          <>
            <label className="field-label" htmlFor="city-target-input">
              City
            </label>
            <CityAutocomplete
              id="city-target-input"
              value={cityInput}
              onChange={handleCityChange}
              placeholder="e.g. Phoenix, Dallas, Tampa"
              data-testid="city-target-input"
            />
          </>
        ) : (
          <div style={{ display: "grid", gap: 14 }}>
            <div role="radiogroup" aria-label="Broad geography" style={{ display: "flex", gap: 8 }}>
              <button
                type="button"
                role="radio"
                aria-checked={broadScope === "nationwide"}
                className={broadScope === "nationwide" ? "btn-primary" : "btn-ghost"}
                onClick={() => setBroadScope("nationwide")}
              >
                Nationwide
              </button>
              <button
                type="button"
                role="radio"
                aria-checked={broadScope === "state"}
                className={broadScope === "state" ? "btn-primary" : "btn-ghost"}
                onClick={() => setBroadScope("state")}
              >
                State
              </button>
            </div>

            {broadScope === "state" && (
              <div>
                <label className="field-label" htmlFor="state-target-input">
                  State or region
                </label>
                <div className="input-wrap">
                  <input
                    id="state-target-input"
                    data-testid="state-target-input"
                    value={stateValue}
                    onChange={(event) => setStateValue(event.target.value)}
                    placeholder="e.g. Arizona"
                  />
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <button
        type="button"
        className="btn-primary"
        disabled={!selectedTarget}
        onClick={() => selectedTarget && onSelect(selectedTarget)}
        style={{ marginTop: 24 }}
      >
        Review target
      </button>
    </section>
  );
}
