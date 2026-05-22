"use client";

import { FormEvent, useMemo, useState } from "react";
import NextMoveCard from "@/components/NextMoveCard";
import { Icon, I } from "@/lib/icons";
import type { StrategyCatalogEntry, StrategyDiscoverRequest } from "@/lib/strategies/types";

interface SignalEntry {
  label: string;
  value: string;
  numeric_value: number | null;
}

interface StrategyResultCard {
  id: string;
  rank: number | null;
  score: number | null;
  city: string;
  service: string;
  strategy_evidence: string[];
  warnings: string[];
  signals: SignalEntry[];
  ai_resilience: string;
  confidence: string;
}

interface SubmittedContext {
  city: string;
  service: string;
  primary_keyword: string;
  reference_city_id: string;
}

interface DiscoverResponse {
  markets?: unknown[];
  results?: unknown[];
}

const STRATEGY_ACCENTS: Record<string, { ink: string; bg: string; soft: string }> = {
  easy_win: { ink: "#047857", bg: "#10b981", soft: "#ecfdf5" },
  gbp_blitz: { ink: "#be123c", bg: "#f43f5e", soft: "#fff1f2" },
  keyword_hijack: { ink: "#0369a1", bg: "#0ea5e9", soft: "#f0f9ff" },
  expand_conquer: { ink: "#4338ca", bg: "#6366f1", soft: "#eef2ff" },
  cash_cow: { ink: "#b45309", bg: "#f59e0b", soft: "#fffbeb" },
};

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

function formatLabel(raw: string): string {
  return raw
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "Unavailable";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(2);
  if (typeof value === "string") return value;
  const record = asRecord(value);
  if (typeof record.score === "number") return String(Math.round(record.score));
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

function readNumericValue(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim() && Number.isFinite(Number(value))) {
    return Number(value);
  }
  const record = asRecord(value);
  if (typeof record.score === "number" && Number.isFinite(record.score)) return record.score;
  return null;
}

function readStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) {
    const record = asRecord(value);
    return Object.entries(record).map(([key, entry]) => `${key}: ${formatValue(entry).toLowerCase()}`);
  }
  return value
    .map((item) => {
      if (typeof item === "string") return item;
      const record = asRecord(item);
      return readString(record, ["message", "label", "description", "evidence"], "");
    })
    .filter(Boolean);
}

function readSignals(value: unknown): SignalEntry[] {
  if (Array.isArray(value)) {
    return value
      .map((item, index) => {
        if (typeof item === "string") return { label: `Signal ${index + 1}`, value: item, numeric_value: null };
        const record = asRecord(item);
        const label = readString(record, ["label", "name", "key"], `Signal ${index + 1}`);
        const rawValue = record.value ?? record.score ?? record.description ?? record.message ?? record.evidence;
        return { label, value: formatValue(rawValue), numeric_value: readNumericValue(rawValue) };
      })
      .filter((entry) => entry.value !== "Unavailable");
  }

  return Object.entries(asRecord(value)).map(([key, entry]) => ({
    label: formatLabel(key),
    value: formatValue(entry),
    numeric_value: readNumericValue(entry),
  }));
}

function uniqueSignals(signals: SignalEntry[]): SignalEntry[] {
  const seen = new Set<string>();
  return signals.filter((signal) => {
    const key = `${signal.label}:${signal.value}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function normalizeResult(item: unknown, index: number): StrategyResultCard {
  const record = asRecord(item);
  const cityRecord = asRecord(record.city);
  const serviceRecord = asRecord(record.service);
  const scoreBreakdown = asRecord(record.score_breakdown);
  const score = readNumber(record, ["score", "strategy_score", "opportunity_score"])
    ?? readNumber(scoreBreakdown, ["projection_score", "opportunity"]);
  const evidenceValue = record.strategy_evidence ?? record.evidence;
  const evidence = readStringArray(evidenceValue);
  const warnings = readStringArray(record.warnings);
  const confidenceRecord = asRecord(scoreBreakdown.confidence ?? record.confidence);
  const confidence = formatValue(confidenceRecord.score ?? scoreBreakdown.confidence ?? record.confidence);
  const aiResilience = formatValue(scoreBreakdown.ai_resilience ?? record.ai_resilience);

  return {
    id: readString(record, ["id", "market_id", "cbsa_code"], `result-${index}`),
    rank: readNumber(record, ["rank"]) ?? index + 1,
    score,
    city: readString(record, ["city", "city_name", "metro_name", "cbsa_name"], readString(cityRecord, ["name", "city_name"], "Unknown city")),
    service: readString(record, ["service", "service_name", "niche"], readString(serviceRecord, ["name", "label"], "Unknown service")),
    strategy_evidence: evidence,
    warnings,
    signals: uniqueSignals([...readSignals(scoreBreakdown), ...readSignals(evidenceValue)]).slice(0, 8),
    ai_resilience: aiResilience,
    confidence,
  };
}

function inputHint(strategy: StrategyCatalogEntry) {
  if (strategy.input_shape === "city_service_keyword") {
    return "Which keyword-led market can you steal first?";
  }
  if (strategy.input_shape === "reference_city_service") {
    return "Where does this proven city-service pattern repeat?";
  }
  if (strategy.input_shape === "cached_scan") {
    return "Which markets have the strongest lead economics?";
  }
  return "Where is this service easiest to rank and monetize?";
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

function verdictForScore(score: number | null): string {
  if (score === null) return "Score unavailable";
  if (score >= 85) return "Strong launch candidate";
  if (score >= 70) return "Promising with focused validation";
  if (score >= 50) return "Mixed opportunity";
  return "Needs more proof";
}

function scoreColor(score: number | null): string {
  if (score === null) return "var(--ink-3)";
  if (score >= 75) return "#047857";
  if (score >= 50) return "#b45309";
  return "#be123c";
}

function timeToRankLabel(result: StrategyResultCard): string {
  if (result.score === null) return "Unavailable";
  if (result.score >= 80 && result.warnings.length === 0) return "Fast";
  if (result.score >= 60) return "Moderate";
  return "Needs validation";
}

function signalTrend(signal: SignalEntry): { direction: "up" | "down"; color: string } | null {
  if (signal.numeric_value === null) return null;
  const normalized = signal.label.toLowerCase();
  if (
    normalized.includes("difficulty") ||
    normalized.includes("risk") ||
    normalized.includes("warning") ||
    normalized.includes("competition")
  ) {
    return { direction: "down", color: "var(--danger)" };
  }
  return { direction: "up", color: "var(--accent-ink)" };
}

function contextLine(context: SubmittedContext | null, topResult: StrategyResultCard | null): string {
  if (!context) return "Run a cached discovery to generate market context.";
  const city = context.reference_city_id || context.city || topResult?.city || "Unknown city";
  const service = context.service || topResult?.service || "Unknown service";
  const keyword = context.primary_keyword ? ` · ${context.primary_keyword}` : "";
  return `${city} · ${service}${keyword}`;
}

function encode(value: string): string {
  return encodeURIComponent(value);
}

function exploreHref(city: string, service: string): string {
  return `/explore?city=${encode(city)}&service=${encode(service)}`;
}

function nextMovesForStrategy(strategy: StrategyCatalogEntry, result: StrategyResultCard) {
  const context = `${result.service} in ${result.city}`;

  if (strategy.strategy_id === "blue_ocean") {
    return [
      {
        href: "/strategies/easy_win",
        title: "Validate rank ease",
        subtitle: `Check whether ${context} can rank quickly.`,
      },
      {
        href: "/explore",
        title: "Check cities for #1",
        subtitle: `Browse adjacent city options for ${result.service}.`,
        primary: true,
      },
    ];
  }

  const shared = [
    {
      href: "/strategies",
      title: "Try another lens",
      subtitle: "Compare this result against another strategy.",
    },
    {
      href: exploreHref(result.city, result.service),
      title: strategy.strategy_id === "easy_win" ? "Browse similar markets" : "Browse Explore",
      subtitle: `Keep scanning ${context}.`,
    },
    {
      href: "/reports",
      title: strategy.strategy_id === "cash_cow" ? "Review saved reports" : "Review report library",
      subtitle: `Compare ${context} against saved market reports.`,
      primary: true,
    },
  ];

  if (strategy.strategy_id === "cash_cow") {
    return [
      {
        href: "/strategies/easy_win",
        title: "Check ease of rank",
        subtitle: "Validate whether this market can move quickly.",
      },
      ...shared.slice(0, 1),
      shared[2],
    ];
  }

  return shared;
}

function StrategyResultHeader({
  strategy,
  context,
  topResult,
  aiResilienceFilter,
  onAiResilienceFilterChange,
}: {
  strategy: StrategyCatalogEntry;
  context: SubmittedContext | null;
  topResult: StrategyResultCard | null;
  aiResilienceFilter: boolean;
  onAiResilienceFilterChange: (value: boolean) => void;
}) {
  return (
    <div
      style={{
        background: "var(--paper-alt)",
        border: "1px solid var(--rule)",
        borderRadius: 8,
        padding: 16,
        display: "flex",
        justifyContent: "space-between",
        gap: 16,
        flexWrap: "wrap",
        alignItems: "center",
      }}
    >
      <div>
        <h2 style={{ margin: 0, fontSize: 17, color: "var(--ink)" }}>{strategy.name} results</h2>
        <p style={{ margin: "5px 0 0", color: "var(--ink-2)", fontSize: 13 }}>
          {contextLine(context, topResult)}
        </p>
        <p style={{ margin: "5px 0 0", color: "var(--ink-3)", fontSize: 12 }}>
          0 scans · cached discovery
        </p>
      </div>
      <label
        style={{
          border: "1px solid var(--rule-strong)",
          borderRadius: 999,
          padding: "8px 12px",
          display: "flex",
          gap: 8,
          alignItems: "center",
          color: "var(--ink-2)",
          fontSize: 13,
          background: "var(--card)",
        }}
      >
        <input
          type="checkbox"
          checked={aiResilienceFilter}
          onChange={(event) => onAiResilienceFilterChange(event.target.checked)}
          style={{ accentColor: "var(--accent)" }}
        />
        AI-Proof mode {aiResilienceFilter ? "on" : "off"}
      </label>
    </div>
  );
}

function ScoreCircle({ score }: { score: number | null }) {
  const color = scoreColor(score);
  return (
    <div
      aria-label="Strategy score"
      style={{
        width: 100,
        height: 100,
        borderRadius: "50%",
        border: `8px solid ${color}`,
        display: "grid",
        placeItems: "center",
        color,
        background: "var(--card)",
        fontFamily: "var(--mono)",
        fontSize: 30,
        fontWeight: 800,
        flex: "0 0 auto",
      }}
    >
      {score === null ? "—" : Math.round(score)}
    </div>
  );
}

function Badge({ children }: { children: React.ReactNode }) {
  return (
    <span
      style={{
        color: "var(--ink-2)",
        background: "var(--paper-alt)",
        border: "1px solid var(--rule)",
        borderRadius: 999,
        padding: "5px 9px",
        fontSize: 12,
        fontWeight: 600,
      }}
    >
      {children}
    </span>
  );
}

function SignalCard({ signal }: { signal: SignalEntry }) {
  const trend = signalTrend(signal);

  return (
    <div
      style={{
        border: "1px solid var(--rule)",
        borderRadius: 8,
        padding: 14,
        background: "var(--card)",
      }}
    >
      <div style={{ color: "var(--ink-3)", fontSize: 11, fontWeight: 700, textTransform: "uppercase" }}>
        {signal.label}
      </div>
      <div
        style={{
          color: "var(--ink)",
          fontFamily: "var(--mono)",
          fontSize: 20,
          fontWeight: 800,
          marginTop: 5,
          display: "flex",
          alignItems: "center",
          gap: 8,
        }}
      >
        <span>{signal.value}</span>
        {trend ? (
          <span
            aria-label={`Signal trend ${trend.direction}`}
            style={{
              display: "inline-grid",
              placeItems: "center",
              color: trend.color,
            }}
          >
            <Icon d={trend.direction === "up" ? I.arrowUp : I.arrowDown} size={14} />
          </span>
        ) : null}
      </div>
    </div>
  );
}

function HeroResult({ result }: { result: StrategyResultCard }) {
  const progress = result.score === null ? 0 : Math.max(0, Math.min(result.score, 100));
  return (
    <article
      style={{
        background: "var(--card)",
        border: "1px solid var(--rule)",
        borderRadius: 8,
        padding: 24,
        display: "flex",
        flexDirection: "column",
        gap: 22,
      }}
    >
      <div style={{ display: "flex", gap: 20, alignItems: "center", flexWrap: "wrap" }}>
        <ScoreCircle score={result.score} />
        <div style={{ minWidth: 0 }}>
          <div style={{ color: "var(--ink-3)", fontFamily: "var(--mono)", fontSize: 12, marginBottom: 6 }}>
            #{result.rank ?? 1} top result
          </div>
          <h3 style={{ margin: 0, fontSize: 24, color: "var(--ink)" }}>
            {result.service} in {result.city}
          </h3>
          <p style={{ margin: "8px 0 0", color: scoreColor(result.score), fontSize: 15, fontWeight: 700 }}>
            {verdictForScore(result.score)}
          </p>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 14 }}>
            <Badge>Time-to-rank: {timeToRankLabel(result)}</Badge>
            <Badge>AI resilience: {result.ai_resilience}</Badge>
            <Badge>Confidence: {result.confidence}</Badge>
          </div>
          {result.warnings.length > 0 ? (
            <div
              aria-label="Result warnings"
              style={{
                display: "flex",
                gap: 8,
                flexWrap: "wrap",
                marginTop: 10,
              }}
            >
              {result.warnings.map((warning) => (
                <span
                  key={warning}
                  style={{
                    color: "var(--warn)",
                    background: "var(--warn-soft)",
                    border: "1px solid var(--rule)",
                    borderRadius: 999,
                    padding: "4px 8px",
                    fontSize: 12,
                    fontWeight: 600,
                  }}
                >
                  {warning}
                </span>
              ))}
            </div>
          ) : null}
        </div>
      </div>

      <div>
        <div style={{ fontSize: 12, fontWeight: 700, color: "var(--ink)", textTransform: "uppercase", marginBottom: 10 }}>
          Signals
        </div>
        {result.signals.length > 0 ? (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 170px), 1fr))",
              gap: 10,
            }}
          >
            {result.signals.map((signal) => (
              <SignalCard key={`${signal.label}-${signal.value}`} signal={signal} />
            ))}
          </div>
        ) : (
          <p style={{ margin: 0, color: "var(--ink-3)", fontSize: 13 }}>
            Signal details are unavailable for this cached result.
          </p>
        )}
      </div>

      <div>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "end" }}>
          <div>
            <div style={{ color: "var(--ink-3)", fontSize: 12 }}>Composite opportunity score</div>
            <div style={{ color: scoreColor(result.score), fontFamily: "var(--mono)", fontSize: 36, fontWeight: 900 }}>
              {result.score === null ? "—" : Math.round(result.score)}
            </div>
          </div>
          <p style={{ margin: 0, color: "var(--ink-3)", fontSize: 12, textAlign: "right" }}>
            Higher scores indicate stronger launch-fit in cached discovery.
          </p>
        </div>
        <div style={{ height: 6, background: "var(--paper-alt)", borderRadius: 999, overflow: "hidden", marginTop: 10 }}>
          <div
            style={{
              height: "100%",
              width: `${progress}%`,
              background: scoreColor(result.score),
              borderRadius: 999,
            }}
          />
        </div>
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
  const [submittedContext, setSubmittedContext] = useState<SubmittedContext | null>(null);

  const isPhase2Unavailable = strategy.status === "phase_2";
  const isUnavailable = isPhase2Unavailable;
  const accent = STRATEGY_ACCENTS[strategy.strategy_id] ?? STRATEGY_ACCENTS.easy_win;
  const topResult = results[0] ?? null;

  const canSubmit = useMemo(() => {
    if (isUnavailable || isLoading) return false;
    if (strategy.input_shape === "reference_city_service") {
      return referenceCityId.trim().length > 0 && service.trim().length > 0;
    }
    if (strategy.input_shape === "city_service_keyword") {
      return city.trim().length > 0 && service.trim().length > 0 && primaryKeyword.trim().length > 0;
    }
    return city.trim().length > 0 && service.trim().length > 0;
  }, [city, isLoading, isUnavailable, primaryKeyword, referenceCityId, service, strategy.input_shape]);

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
    setSubmittedContext({
      city: city.trim(),
      service: service.trim(),
      primary_keyword: primaryKeyword.trim(),
      reference_city_id: referenceCityId.trim(),
    });

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
    <div style={{ display: "flex", flexDirection: "column", gap: 28 }}>
      <section
        style={{
          maxWidth: 672,
          width: "100%",
          margin: "0 auto",
          textAlign: "center",
        }}
      >
        <div
          style={{
            width: 56,
            height: 56,
            borderRadius: 14,
            display: "grid",
            placeItems: "center",
            color: accent.ink,
            background: accent.soft,
            margin: "0 auto 14px",
          }}
        >
          <Icon d={I.target} size={28} />
        </div>
        <h1 className="page-h1" style={{ fontSize: 28, margin: 0 }}>
          Run {strategy.name}
        </h1>
        <p style={{ color: "var(--ink-3)", fontSize: 14, fontStyle: "italic", lineHeight: 1.5, margin: "8px 0 18px" }}>
          {inputHint(strategy)}
        </p>

        {isPhase2Unavailable ? (
          <div
            role="status"
            style={{
              border: "1px solid var(--rule)",
              borderRadius: 8,
              background: accent.soft,
              color: accent.ink,
              padding: 12,
              fontSize: 13,
              lineHeight: 1.5,
              marginBottom: 16,
              textAlign: "left",
            }}
          >
            Cash Cow is a phase-2 strategy and is not available for launch discovery runs.
          </div>
        ) : null}

        <form
          onSubmit={onSubmit}
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 14,
            background: "var(--card)",
            border: "1px solid var(--rule)",
            borderRadius: 12,
            padding: 24,
            textAlign: "left",
          }}
        >
          <label
            style={{
              border: `1px solid ${aiResilienceFilter ? accent.bg : "var(--rule)"}`,
              borderRadius: 10,
              padding: 14,
              display: "flex",
              gap: 12,
              justifyContent: "space-between",
              alignItems: "center",
              background: aiResilienceFilter ? accent.soft : "var(--paper-alt)",
              color: "var(--ink)",
            }}
          >
            <span>
              <span style={{ display: "block", fontSize: 13, fontWeight: 700 }}>AI-Proof mode</span>
              <span style={{ display: "block", fontSize: 12, color: "var(--ink-3)", marginTop: 2 }}>
                Add the AI resilience warning filter to the next discovery run.
              </span>
            </span>
            <input
              type="checkbox"
              checked={aiResilienceFilter}
              onChange={(event) => setAiResilienceFilter(event.target.checked)}
              disabled={isUnavailable}
              style={{ accentColor: accent.bg }}
              aria-label="AI resilience warning filter"
            />
          </label>

          {strategy.input_shape === "reference_city_service" ? (
            <label>
              <div className="field-label">Reference city id</div>
              <div className="input-wrap">
                <Icon d={I.mapPin} />
                <input
                  value={referenceCityId}
                  onChange={(event) => setReferenceCityId(event.target.value)}
                  placeholder="austin-tx"
                  disabled={isUnavailable}
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

          <button
            type="submit"
            disabled={!canSubmit}
            style={{
              border: "none",
              borderRadius: 8,
              padding: "12px 16px",
              color: "#fff",
              background: canSubmit ? accent.bg : "var(--ink-3)",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 8,
              fontWeight: 800,
              cursor: canSubmit ? "pointer" : "not-allowed",
            }}
          >
            {isLoading ? "Searching..." : "Run discovery"} <Icon d={I.arrow} />
          </button>
        </form>
        <p style={{ margin: "10px 0 0", color: "var(--ink-3)", fontSize: 12 }}>
          0 scans · cached discovery
        </p>
      </section>

      <section style={{ maxWidth: 960, width: "100%", margin: "0 auto", display: "flex", flexDirection: "column", gap: 12 }} aria-live="polite">
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

        {topResult ? (
          <>
            <StrategyResultHeader
              strategy={strategy}
              context={submittedContext}
              topResult={topResult}
              aiResilienceFilter={aiResilienceFilter}
              onAiResilienceFilterChange={setAiResilienceFilter}
            />
            <HeroResult result={topResult} />
            <div>
              <h3 style={{ margin: "4px 0 10px", fontSize: 12, fontWeight: 800, color: "var(--ink)", textTransform: "uppercase" }}>
                Next Moves
              </h3>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 220px), 1fr))",
                  gap: 12,
                }}
              >
                {nextMovesForStrategy(strategy, topResult).map((move) => (
                  <NextMoveCard key={`${move.title}-${move.href}`} {...move} />
                ))}
              </div>
            </div>
          </>
        ) : (
          <div
            style={{
              background: "var(--card)",
              border: "1px solid var(--rule)",
              borderRadius: 8,
              padding: 22,
              color: "var(--ink-3)",
              fontSize: 14,
              textAlign: "center",
            }}
          >
            Run a launch strategy to populate this list.
          </div>
        )}
      </section>
    </div>
  );
}
