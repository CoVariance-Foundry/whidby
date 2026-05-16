"use client";

import { FormEvent, useMemo, useState } from "react";
import { Icon, I } from "@/lib/icons";
import type { StrategyCatalogEntry, StrategyDiscoverRequest } from "@/lib/strategies/types";

interface StrategyResultCard {
  id: string;
  rank: number | null;
  score: number | null;
  city: string;
  service: string;
  strategy_evidence: string[];
  warnings: string[];
}

interface DiscoverResponse {
  markets?: unknown[];
  results?: unknown[];
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" ? (value as Record<string, unknown>) : {};
}

function readString(record: Record<string, unknown>, keys: string[], fallback = "Unknown") {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "string" && value.trim()) return value;
  }
  return fallback;
}

function readNumber(record: Record<string, unknown>, keys: string[]) {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "number" && Number.isFinite(value)) return value;
    if (typeof value === "string" && value.trim() && Number.isFinite(Number(value))) {
      return Number(value);
    }
  }
  return null;
}

function readStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) {
    const record = asRecord(value);
    return Object.entries(record).map(([key, entry]) => `${key}: ${formatValue(entry)}`);
  }
  return value
    .map((item) => {
      if (typeof item === "string") return item;
      const record = asRecord(item);
      return readString(record, ["message", "label", "description", "evidence"], "");
    })
    .filter(Boolean);
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "not available";
  if (typeof value === "boolean") return value ? "yes" : "no";
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(2);
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

function normalizeResult(item: unknown, index: number): StrategyResultCard {
  const record = asRecord(item);
  const cityRecord = asRecord(record.city);
  const serviceRecord = asRecord(record.service);
  const score = readNumber(record, ["score", "strategy_score", "opportunity_score"]);
  const evidence = readStringArray(record.strategy_evidence).concat(readStringArray(record.evidence));
  const warnings = readStringArray(record.warnings);

  return {
    id: readString(record, ["id", "market_id", "cbsa_code"], `result-${index}`),
    rank: readNumber(record, ["rank"]) ?? index + 1,
    score,
    city: readString(record, ["city", "city_name", "metro_name", "cbsa_name"], readString(cityRecord, ["name", "city_name"], "Unknown city")),
    service: readString(record, ["service", "service_name", "niche"], readString(serviceRecord, ["name", "label"], "Unknown service")),
    strategy_evidence: evidence,
    warnings,
  };
}

function inputHint(strategy: StrategyCatalogEntry) {
  if (strategy.input_shape === "city_service_keyword") {
    return "Send a city, service, and one primary keyword to rank matching markets.";
  }
  if (strategy.input_shape === "reference_city_service") {
    return "Reference-city discovery is designed, but backend discovery still rejects reference_city_id.";
  }
  if (strategy.input_shape === "cached_scan") {
    return "This phase-2 cached scan is not part of the launch catalog.";
  }
  return "Send a city and service to search cached market intelligence.";
}

function buildPayload({
  strategy,
  city,
  service,
  primaryKeyword,
  referenceCityId,
  aiResilienceFilter,
  limit,
}: {
  strategy: StrategyCatalogEntry;
  city: string;
  service: string;
  primaryKeyword: string;
  referenceCityId: string;
  aiResilienceFilter: boolean;
  limit: number;
}): StrategyDiscoverRequest {
  return {
    lens_id: strategy.strategy_id,
    city_filters: city.trim()
      ? [{ field: "name", operator: "like", value: city.trim() }]
      : [],
    service_filters: service.trim()
      ? [{ field: "name", operator: "like", value: service.trim() }]
      : [],
    primary_keyword:
      strategy.input_shape === "city_service_keyword" ? primaryKeyword.trim() : null,
    reference_city_id:
      strategy.input_shape === "reference_city_service" ? referenceCityId.trim() : null,
    ai_resilience_filter: aiResilienceFilter,
    limit,
  };
}

function ResultCard({ result }: { result: StrategyResultCard }) {
  return (
    <article
      style={{
        background: "var(--card)",
        border: "1px solid var(--rule)",
        borderRadius: 8,
        padding: 16,
        display: "grid",
        gridTemplateColumns: "minmax(0, 1fr) auto",
        gap: 16,
      }}
    >
      <div style={{ minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          {result.rank ? (
            <span style={{ fontFamily: "var(--mono)", color: "var(--ink-3)", fontSize: 12 }}>
              #{result.rank}
            </span>
          ) : null}
          <h3 style={{ margin: 0, fontSize: 16, color: "var(--ink)" }}>
            {result.service} in {result.city}
          </h3>
        </div>
        {result.strategy_evidence.length > 0 ? (
          <ul style={{ margin: "10px 0 0", paddingLeft: 18, color: "var(--ink-2)", fontSize: 13, lineHeight: 1.5 }}>
            {result.strategy_evidence.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        ) : (
          <p style={{ margin: "10px 0 0", color: "var(--ink-3)", fontSize: 13 }}>
            No strategy evidence returned for this row.
          </p>
        )}
        {result.warnings.length > 0 ? (
          <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 6 }}>
            {result.warnings.map((warning) => (
              <span
                key={warning}
                style={{
                  alignSelf: "flex-start",
                  color: "var(--warn)",
                  background: "var(--warn-soft)",
                  border: "1px solid var(--rule)",
                  borderRadius: 999,
                  padding: "4px 8px",
                  fontSize: 12,
                }}
              >
                {warning}
              </span>
            ))}
          </div>
        ) : null}
      </div>
      <div
        aria-label="Strategy score"
        style={{
          width: 68,
          height: 68,
          borderRadius: 8,
          border: "1px solid var(--rule-strong)",
          display: "grid",
          placeItems: "center",
          color: "var(--accent)",
          background: "var(--accent-soft)",
          fontFamily: "var(--mono)",
          fontSize: 22,
          fontWeight: 800,
        }}
      >
        {result.score === null ? "—" : Math.round(result.score)}
      </div>
    </article>
  );
}

export default function StrategyPageClient({ strategy }: { strategy: StrategyCatalogEntry }) {
  const [city, setCity] = useState("");
  const [service, setService] = useState("");
  const [primaryKeyword, setPrimaryKeyword] = useState("");
  const [referenceCityId, setReferenceCityId] = useState("");
  const [aiResilienceFilter, setAiResilienceFilter] = useState(false);
  const [limit, setLimit] = useState(10);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<StrategyResultCard[]>([]);

  const isReferenceCityUnavailable = strategy.input_shape === "reference_city_service";
  const isPhase2Unavailable = strategy.status === "phase_2";
  const isUnavailable = isReferenceCityUnavailable || isPhase2Unavailable;

  const canSubmit = useMemo(() => {
    if (isUnavailable || isLoading) return false;
    if (strategy.input_shape === "city_service_keyword") {
      return city.trim().length > 0 && service.trim().length > 0 && primaryKeyword.trim().length > 0;
    }
    return city.trim().length > 0 && service.trim().length > 0;
  }, [city, isLoading, isUnavailable, primaryKeyword, service, strategy.input_shape]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit) return;

    const payload = buildPayload({
      strategy,
      city,
      service,
      primaryKeyword,
      referenceCityId,
      aiResilienceFilter,
      limit,
    });

    setIsLoading(true);
    setError(null);
    setResults([]);

    try {
      const res = await fetch("/api/strategies/discover", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const body = (await res.json().catch(() => ({}))) as DiscoverResponse & {
        detail?: string;
        message?: string;
      };

      if (!res.ok) {
        setError(body.detail ?? body.message ?? "Strategy discovery request failed.");
        return;
      }

      const rawResults = Array.isArray(body.markets) ? body.markets : Array.isArray(body.results) ? body.results : [];
      setResults(rawResults.map(normalizeResult));
      if (rawResults.length === 0) {
        setError("No matching cached markets were returned for this lens.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Strategy discovery request failed.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 340px), 1fr))",
        gap: 24,
        alignItems: "start",
      }}
    >
      <section
        style={{
          background: "var(--card)",
          border: "1px solid var(--rule)",
          borderRadius: 8,
          padding: 20,
        }}
      >
        <div style={{ marginBottom: 18 }}>
          <div style={{ color: "var(--ink-3)", fontFamily: "var(--mono)", fontSize: 12, marginBottom: 8 }}>
            {strategy.strategy_id}
          </div>
          <h1 className="page-h1" style={{ fontSize: 28, margin: 0 }}>
            {strategy.name}
          </h1>
          <p style={{ color: "var(--ink-2)", fontSize: 14, lineHeight: 1.5, margin: "10px 0 0" }}>
            {strategy.description}
          </p>
          <p style={{ color: "var(--ink-3)", fontSize: 13, lineHeight: 1.5, margin: "8px 0 0" }}>
            {inputHint(strategy)}
          </p>
        </div>

        {isReferenceCityUnavailable ? (
          <div
            role="status"
            style={{
              border: "1px solid var(--rule)",
              borderRadius: 8,
              background: "var(--warn-soft)",
              color: "var(--warn)",
              padding: 12,
              fontSize: 13,
              lineHeight: 1.5,
              marginBottom: 16,
            }}
          >
            Expand & Conquer is visible in the launch catalog, but reference-city discovery is pending backend support. This screen will not pretend the run works.
          </div>
        ) : null}

        {isPhase2Unavailable ? (
          <div
            role="status"
            style={{
              border: "1px solid var(--rule)",
              borderRadius: 8,
              background: "var(--warn-soft)",
              color: "var(--warn)",
              padding: 12,
              fontSize: 13,
              lineHeight: 1.5,
              marginBottom: 16,
            }}
          >
            Cash Cow is a phase-2 strategy and is not available for launch discovery runs.
          </div>
        ) : null}

        <form onSubmit={onSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {strategy.input_shape === "reference_city_service" ? (
            <label>
              <div className="field-label">Reference city id</div>
              <div className="input-wrap">
                <Icon d={I.mapPin} />
                <input
                  value={referenceCityId}
                  onChange={(event) => setReferenceCityId(event.target.value)}
                  placeholder="austin-tx"
                  disabled={isReferenceCityUnavailable}
                  aria-label="Reference city id"
                />
              </div>
            </label>
          ) : (
            <label>
              <div className="field-label">City</div>
              <div className="input-wrap">
                <Icon d={I.mapPin} />
                <input
                  value={city}
                  onChange={(event) => setCity(event.target.value)}
                  placeholder="Austin"
                  disabled={isUnavailable}
                  aria-label="City"
                />
              </div>
            </label>
          )}

          {strategy.input_shape !== "cached_scan" ? (
            <label>
              <div className="field-label">Service</div>
              <div className="input-wrap">
                <Icon d={I.search} />
                <input
                  value={service}
                  onChange={(event) => setService(event.target.value)}
                  placeholder="plumbing"
                  disabled={isUnavailable}
                  aria-label="Service"
                />
              </div>
            </label>
          ) : null}

          {strategy.input_shape === "city_service_keyword" ? (
            <label>
              <div className="field-label">Primary keyword</div>
              <div className="input-wrap">
                <Icon d={I.target} />
                <input
                  value={primaryKeyword}
                  onChange={(event) => setPrimaryKeyword(event.target.value)}
                  placeholder="emergency plumber"
                  disabled={isUnavailable}
                  aria-label="Primary keyword"
                />
              </div>
            </label>
          ) : null}

          <label>
            <div className="field-label">Result limit</div>
            <div className="input-wrap">
              <Icon d={I.sliders} />
              <input
                value={limit}
                min={1}
                max={50}
                type="number"
                onChange={(event) => setLimit(Number(event.target.value) || 10)}
                disabled={isUnavailable}
                aria-label="Result limit"
              />
            </div>
          </label>

          <label style={{ display: "flex", gap: 8, alignItems: "center", color: "var(--ink-2)", fontSize: 13 }}>
            <input
              type="checkbox"
              checked={aiResilienceFilter}
              onChange={(event) => setAiResilienceFilter(event.target.checked)}
              disabled={isUnavailable}
              style={{ accentColor: "var(--accent)" }}
            />
            Add AI resilience warning filter
          </label>

          <button type="submit" className="btn-primary" disabled={!canSubmit}>
            {isLoading ? "Searching..." : "Run discovery"} <Icon d={I.arrow} />
          </button>
        </form>
      </section>

      <section style={{ display: "flex", flexDirection: "column", gap: 12 }} aria-live="polite">
        <div>
          <h2 style={{ margin: 0, fontSize: 15, color: "var(--ink)" }}>Results</h2>
          <p style={{ margin: "5px 0 0", color: "var(--ink-3)", fontSize: 13 }}>
            Returned markets render with the service score, evidence, and warnings from the discovery API.
          </p>
        </div>

        {error ? (
          <div
            role="alert"
            style={{
              background: "var(--danger-soft)",
              color: "var(--danger)",
              border: "1px solid var(--rule)",
              borderRadius: 8,
              padding: 12,
              fontSize: 13,
            }}
          >
            {error}
          </div>
        ) : null}

        {results.length > 0 ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {results.map((result) => (
              <ResultCard key={result.id} result={result} />
            ))}
          </div>
        ) : (
          <div
            style={{
              background: "var(--card)",
              border: "1px solid var(--rule)",
              borderRadius: 8,
              padding: 22,
              color: "var(--ink-3)",
              fontSize: 14,
            }}
          >
            Run a launch strategy to populate this list.
          </div>
        )}
      </section>
    </div>
  );
}
