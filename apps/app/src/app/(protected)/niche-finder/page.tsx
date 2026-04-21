"use client";

import { useState } from "react";
import Link from "next/link";
import Sidebar from "@/components/Sidebar";
import Topbar from "@/components/Topbar";
import CityAutocomplete from "@/components/niche-finder/CityAutocomplete";
import type { MetroSuggestion } from "@/lib/niche-finder/metro-suggest";
import type { StandardSurfaceResponse } from "@/lib/niche-finder/types";
import { validateNicheQueryInput } from "@/lib/niche-finder/request-validation";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type PageState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "success"; data: StandardSurfaceResponse };

// ---------------------------------------------------------------------------
// Score pill — maps classification_label to an archetype-like style
// ---------------------------------------------------------------------------

const LABEL_STYLE: Record<string, { className: string; label: string }> = {
  High:   { className: "arch-pack-vuln", label: "High opportunity" },
  Medium: { className: "arch-pack-est",  label: "Medium opportunity" },
  Low:    { className: "arch-barren",    label: "Low opportunity" },
};

function ClassificationPill({ label }: { label: string }) {
  const style = LABEL_STYLE[label] ?? { className: "arch-mixed", label };
  return (
    <span
      className={style.className}
      style={{
        display: "inline-block",
        padding: "3px 10px",
        borderRadius: 999,
        fontSize: 11.5,
        fontFamily: "var(--sans)",
        fontWeight: 600,
        letterSpacing: "0.02em",
        textTransform: "uppercase" as const,
      }}
    >
      {style.label}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function NicheFinderPage() {
  const [city, setCity] = useState("");
  const [state, setState] = useState<string | undefined>(undefined);
  const [service, setService] = useState("");
  const [pageState, setPageState] = useState<PageState>({ kind: "idle" });

  // Called by CityAutocomplete: free-type clears resolved state; selection sets both.
  const handleCityChange = (newCity: string, suggestion?: MetroSuggestion) => {
    if (suggestion) {
      // Dropdown selection passes a display string like "Phoenix, AZ".
      // Keep query city canonical for API payloads.
      setCity(suggestion.city);
      setState(suggestion.state);
    } else {
      setCity(newCity);
      // Free-typed text — clear any previously resolved state
      setState(undefined);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const validation = validateNicheQueryInput({ city, service });
    if (!validation.ok) {
      setPageState({ kind: "error", message: validation.message ?? "Invalid input." });
      return;
    }

    setPageState({ kind: "loading" });

    try {
      const body: Record<string, string> = { city: city.trim(), service: service.trim() };
      if (state) body.state = state;

      const res = await fetch("/api/agent/scoring", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      const json: StandardSurfaceResponse = await res.json();

      if (!res.ok || json.status !== "success") {
        setPageState({
          kind: "error",
          message: json.message ?? `Scoring failed (HTTP ${res.status}).`,
        });
        return;
      }

      setPageState({ kind: "success", data: json });
    } catch (err) {
      setPageState({
        kind: "error",
        message: err instanceof Error ? err.message : "An unexpected error occurred.",
      });
    }
  };

  const isLoading = pageState.kind === "loading";

  return (
    <div className="app">
      <Sidebar active="finder" />
      <div className="main">
        <Topbar crumbs={["Niche finder"]} />
        <div className="page">
          {/* ── Header ── */}
          <div style={{ marginBottom: 28 }}>
            <div className="kicker">Score a niche</div>
            <div className="page-h1" style={{ marginTop: 6 }}>
              Find a niche
            </div>
            <div className="page-sub">
              Score a service-area business opportunity in a specific metro.
            </div>
          </div>

          {/* ── Form card ── */}
          <div
            style={{
              background: "var(--card)",
              border: "1px solid var(--rule)",
              borderRadius: 10,
              padding: "24px 24px 20px",
              maxWidth: 520,
            }}
          >
            <form onSubmit={handleSubmit} noValidate>
              {/* City input */}
              <div style={{ marginBottom: 16 }}>
                <label
                  htmlFor="nf-city"
                  className="field-label"
                  style={{ display: "block", marginBottom: 6 }}
                >
                  City
                </label>
                <CityAutocomplete
                  value={city}
                  onChange={handleCityChange}
                  disabled={isLoading}
                  placeholder="City (e.g. Phoenix, AZ)"
                  data-testid="city-input"
                />
              </div>

              {/* Service input */}
              <div style={{ marginBottom: 20 }}>
                <label
                  htmlFor="nf-service"
                  className="field-label"
                  style={{ display: "block", marginBottom: 6 }}
                >
                  Service
                </label>
                <div className="input-wrap">
                  <input
                    id="nf-service"
                    data-testid="service-input"
                    type="text"
                    value={service}
                    onChange={(e) => setService(e.target.value)}
                    disabled={isLoading}
                    placeholder="e.g. roofing, water damage restoration"
                    autoComplete="off"
                  />
                </div>
              </div>

              {/* Submit */}
              <button
                type="submit"
                className="btn-primary"
                disabled={isLoading}
                style={{ width: "100%", justifyContent: "center" }}
                data-testid="submit-btn"
              >
                {isLoading ? "Scoring…" : "Score niche"}
              </button>
            </form>
          </div>

          {/* ── Loading state ── */}
          {pageState.kind === "loading" && (
            <div
              role="status"
              aria-live="polite"
              data-testid="loading-banner"
              style={{
                marginTop: 20,
                maxWidth: 520,
                background: "var(--info-soft)",
                border: "1px solid var(--info)",
                borderRadius: 8,
                padding: "14px 16px",
                fontFamily: "var(--serif)",
                fontStyle: "italic",
                fontSize: 14,
                color: "var(--info)",
              }}
            >
              Running live scoring pipeline — this takes up to a minute on first run.
            </div>
          )}

          {/* ── Error state ── */}
          {pageState.kind === "error" && (
            <div
              role="alert"
              data-testid="error-banner"
              style={{
                marginTop: 20,
                maxWidth: 520,
                background: "var(--danger-soft)",
                border: "1px solid var(--danger)",
                borderRadius: 8,
                padding: "14px 16px",
                fontFamily: "var(--serif)",
                fontSize: 14,
                color: "var(--danger)",
              }}
            >
              {pageState.message}
            </div>
          )}

          {/* ── Success: result card ── */}
          {pageState.kind === "success" && (
            <div
              data-testid="result-card"
              style={{
                marginTop: 20,
                maxWidth: 520,
                background: "var(--card)",
                border: "1px solid var(--rule)",
                borderRadius: 10,
                padding: "24px",
              }}
            >
              {/* Metro label */}
              <div
                style={{
                  fontFamily: "var(--serif)",
                  fontStyle: "italic",
                  fontSize: 13,
                  color: "var(--ink-3)",
                  marginBottom: 12,
                }}
              >
                {pageState.data.query.city}
                {pageState.data.query.state ? `, ${pageState.data.query.state}` : ""}
                {" · "}
                {pageState.data.query.service}
              </div>

              {/* Score row */}
              <div
                style={{
                  display: "flex",
                  alignItems: "flex-end",
                  gap: 16,
                  marginBottom: 16,
                }}
              >
                <div>
                  <div
                    className="field-label"
                    style={{ marginBottom: 4 }}
                  >
                    Opportunity score
                  </div>
                  <div
                    data-testid="opportunity-score"
                    className="score"
                    style={{ fontSize: 48, lineHeight: 1 }}
                  >
                    {pageState.data.score_result.opportunity_score}
                  </div>
                  {/* Score bar */}
                  <div style={{ width: 120, marginTop: 8 }}>
                    <div className="score-bar">
                      <div
                        style={{
                          width: pageState.data.score_result.opportunity_score + "%",
                        }}
                      />
                    </div>
                  </div>
                </div>

                {/* Classification pill */}
                <div style={{ paddingBottom: 6 }}>
                  <ClassificationPill
                    label={pageState.data.score_result.classification_label}
                  />
                </div>
              </div>

              {/* CTA */}
              {pageState.data.report_id ? (
                <Link
                  href={`/reports/${pageState.data.report_id}`}
                  className="btn-ghost"
                  style={{ textDecoration: "none", display: "inline-flex" }}
                >
                  View full report →
                </Link>
              ) : (
                <span
                  style={{
                    fontSize: 12,
                    color: "var(--ink-3)",
                    fontFamily: "var(--serif)",
                    fontStyle: "italic",
                  }}
                >
                  Full report not yet available.
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
