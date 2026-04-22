"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import CityAutocomplete from "@/components/niche-finder/CityAutocomplete";
import NicheFinderTabs, { type TabKey } from "@/components/niche-finder/NicheFinderTabs";
import StrategyPresetRail from "@/components/niche-finder/StrategyPresetRail";
import PinnedRecentRail from "@/components/niche-finder/PinnedRecentRail";
import type { MetroSuggestion } from "@/lib/niche-finder/metro-suggest";
import type { StandardSurfaceResponse } from "@/lib/niche-finder/types";
import type { HistoryEntry } from "@/lib/niche-finder/history-storage";
import { validateNicheQueryInput } from "@/lib/niche-finder/request-validation";
import { loadPinned, loadRecent, pushRecent } from "@/lib/niche-finder/history-storage";

type PageState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "success"; data: StandardSurfaceResponse };

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

function Toast({ message, onDone }: { message: string; onDone: () => void }) {
  useEffect(() => {
    const t = setTimeout(onDone, 2400);
    return () => clearTimeout(t);
  }, [onDone]);

  return (
    <div
      role="status"
      aria-live="polite"
      style={{
        position: "fixed",
        bottom: 24,
        left: "50%",
        transform: "translateX(-50%)",
        background: "var(--ink)",
        color: "var(--card)",
        fontFamily: "var(--sans)",
        fontSize: 13.5,
        fontWeight: 500,
        padding: "10px 20px",
        borderRadius: 999,
        boxShadow: "0 4px 20px rgba(31,27,22,0.18)",
        zIndex: 9999,
        whiteSpace: "nowrap",
      }}
    >
      {message}
    </div>
  );
}

export default function NicheFinderClient() {
  const [city, setCity] = useState("");
  const [state, setState] = useState<string | undefined>(undefined);
  const [service, setService] = useState("");
  const [pageState, setPageState] = useState<PageState>({ kind: "idle" });
  const [activeTab, setActiveTab] = useState<TabKey>("niche");
  const [pinned, setPinned] = useState<HistoryEntry[]>([]);
  const [recent, setRecent] = useState<HistoryEntry[]>([]);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    setPinned(loadPinned());
    setRecent(loadRecent());
  }, []);

  const showToast = useCallback((msg: string) => setToast(msg), []);
  const dismissToast = useCallback(() => setToast(null), []);

  const handleCityChange = (newCity: string, suggestion?: MetroSuggestion) => {
    if (suggestion) {
      setCity(suggestion.city);
      setState(suggestion.state);
    } else {
      setCity(newCity);
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
      pushRecent({ city: city.trim(), service: service.trim(), at: Date.now() });
      setRecent(loadRecent());
    } catch (err) {
      setPageState({
        kind: "error",
        message: err instanceof Error ? err.message : "An unexpected error occurred.",
      });
    }
  };

  const handleRailPick = (entry: HistoryEntry) => {
    setCity(entry.city);
    setService(entry.service);
    setState(undefined);
    setActiveTab("niche");
  };

  const isLoading = pageState.kind === "loading";

  return (
    <>
      <div className="page" style={{ display: "flex", gap: 32 }}>
        {/* Left: main column */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ marginBottom: 20 }}>
            <div className="kicker">Score a niche</div>
            <div className="page-h1" style={{ marginTop: 6 }}>
              Find a niche
            </div>
            <div className="page-sub">
              Score a service-area business opportunity in a specific metro.
            </div>
          </div>

          <div style={{ marginBottom: 20 }}>
            <NicheFinderTabs active={activeTab} onChange={setActiveTab} />
          </div>

          {activeTab === "niche" && (
            <>
              <form
                onSubmit={handleSubmit}
                noValidate
                style={{
                  display: "flex",
                  gap: 10,
                  alignItems: "flex-end",
                  flexWrap: "wrap",
                  marginBottom: 20,
                }}
              >
                <div style={{ flex: "1 1 200px", minWidth: 180 }}>
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

                <div style={{ flex: "1 1 200px", minWidth: 180 }}>
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

                <button
                  type="submit"
                  className="btn-primary"
                  disabled={isLoading}
                  data-testid="submit-btn"
                  style={{ whiteSpace: "nowrap" }}
                >
                  {isLoading ? "Scoring…" : "Score niche"}
                </button>
              </form>

              {pageState.kind === "loading" && (
                <div
                  role="status"
                  aria-live="polite"
                  data-testid="loading-banner"
                  style={{
                    marginBottom: 16,
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

              {pageState.kind === "error" && (
                <div
                  role="alert"
                  data-testid="error-banner"
                  style={{
                    marginBottom: 16,
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

              {pageState.kind === "success" && (
                <div
                  data-testid="result-card"
                  style={{
                    background: "var(--card)",
                    border: "1px solid var(--rule)",
                    borderRadius: 10,
                    padding: "24px",
                  }}
                >
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

                  <div
                    style={{
                      display: "flex",
                      alignItems: "flex-end",
                      gap: 16,
                      marginBottom: 16,
                    }}
                  >
                    <div>
                      <div className="field-label" style={{ marginBottom: 4 }}>
                        Opportunity score
                      </div>
                      <div
                        data-testid="opportunity-score"
                        className="score"
                        style={{ fontSize: 48, lineHeight: 1 }}
                      >
                        {pageState.data.score_result.opportunity_score}
                      </div>
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

                    <div style={{ paddingBottom: 6 }}>
                      <ClassificationPill
                        label={pageState.data.score_result.classification_label}
                      />
                    </div>
                  </div>

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
            </>
          )}

          {activeTab === "strategy" && (
            <StrategyPresetRail
              onPick={() => showToast("Strategy search coming soon — Phase 3.")}
            />
          )}
        </div>

        {/* Right rail */}
        <PinnedRecentRail
          pinned={pinned}
          recent={recent}
          onPick={handleRailPick}
        />
      </div>

      {toast && <Toast message={toast} onDone={dismissToast} />}
    </>
  );
}
