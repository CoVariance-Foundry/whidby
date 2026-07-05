"use client";

import { FormEvent, useMemo, useRef, useState } from "react";
import { AIResilienceModifierControls } from "@/components/AIResilienceModifierControls";
import Term from "@/components/glossary/Term";
import { StrategyResultSummary } from "@/components/strategies/StrategyResultSummary";
import {
  DEFAULT_AI_RESILIENCE_MODIFIER_STATE,
  type AIResilienceModifierState,
  filterAIResilienceFlagged,
  readAIResilienceScore,
  toAIResilienceFilterPayload,
} from "@/lib/ai-resilience-modifier";
import { Icon, I } from "@/lib/icons";
import {
  createInlineStrategyResultSummary,
  type StrategyResultSummaryDto,
} from "@/lib/strategy-result-summary";
import type {
  StrategyCatalogEntry,
  StrategyDiscoverRequest,
  StrategyInputShape,
  StrategyRunRequest,
} from "@/lib/strategies/types";

interface DiscoverResponse {
  markets?: unknown[];
  results?: unknown[];
}

interface LiveReportTarget {
  strategyId: string;
  inputShape: StrategyInputShape;
  city: string;
  service: string;
  cbsaCode: string;
  primaryKeyword: string;
  referenceCityId: string;
  feasibilityPreflightPassed: boolean;
  aiResilienceModifier: AIResilienceModifierState;
  limit: number;
}

export interface StrategyInitialInputs {
  city?: string;
  cbsa_code?: string;
  service?: string;
  primary_keyword?: string;
  reference_city_id?: string;
}

interface StrategyRunResponse {
  status?: string;
  code?: string;
  message?: string;
  detail?: string;
  run_id?: string;
  report_id?: string;
  tier?: string;
  monthly_report_limit?: number;
}

type LiveRunState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; response: StrategyRunResponse }
  | { status: "upgrade"; message: string }
  | { status: "quota"; message: string }
  | { status: "error"; message: string };

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

function readOptionalString(record: Record<string, unknown>, keys: string[]) {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "string" && value.trim()) return value.trim();
  }
  return null;
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

function normalizeResult({
  item,
  index,
  strategy,
}: {
  item: unknown;
  index: number;
  strategy: StrategyCatalogEntry;
}): StrategyResultSummaryDto {
  const record = asRecord(item);
  const cityRecord = asRecord(record.city);
  const serviceRecord = asRecord(record.service);
  const score = readNumber(record, ["score", "strategy_score", "opportunity_score"]);
  const evidence = readStringArray(record.strategy_evidence).concat(readStringArray(record.evidence));
  const warnings = readStringArray(record.warnings);
  const strategyEvidence =
    strategy.strategy_id === "keyword_hijack"
      ? [...evidence, "Feasibility preflight passed"]
      : evidence;
  const strategyWarnings =
    strategy.strategy_id === "keyword_hijack"
      ? [...warnings, "Keyword Hijack risk: keep the keyword lens narrow"]
      : warnings;
  const aiResilienceScore = readAIResilienceScore(record);
  const scores = asRecord(record.scores);
  const confidence = asRecord(record.confidence ?? scores.confidence);
  const city = readString(record, ["city", "city_name", "metro_name", "cbsa_name"], readString(cityRecord, ["name", "city_name"], "Unknown city"));
  const service = readString(record, ["service", "service_name", "niche"], readString(serviceRecord, ["name", "label"], "Unknown service"));

  return createInlineStrategyResultSummary({
    id: readString(record, ["id", "market_id", "cbsa_code"], `result-${index}`),
    rank: readNumber(record, ["rank"]) ?? index + 1,
    score,
    city,
    service,
    confidenceScore: readNumber(record, ["confidence_score"]) ?? readNumber(confidence, ["score"]),
    reportId: readOptionalString(record, ["report_id"]),
    evidence: strategyEvidence,
    warnings: strategyWarnings,
    aiResilienceScore,
    sourceContext: {
      strategy_id: strategy.strategy_id,
      strategy_name: strategy.name,
      segment: strategy.path_role ?? strategy.status,
    },
  });
}

function inputHint(strategy: StrategyCatalogEntry) {
  if (strategy.input_shape === "city_service_keyword") {
    return "Validate one primary keyword before any fresh-report spend.";
  }
  if (strategy.input_shape === "reference_city_service") {
    return "Send a reference city and service to search lookalike expansion markets.";
  }
  if (strategy.input_shape === "cached_scan") {
    return "This phase-2 cached scan is not part of the launch catalog.";
  }
  return "Send a city and service to search cached market intelligence.";
}

function primaryKeywordTokenCount(value: string): number {
  return value.match(/[a-z0-9]+/gi)?.length ?? 0;
}

function buildPayload({
  strategy,
  city,
  cbsaCode,
  service,
  primaryKeyword,
  referenceCityId,
  aiResilienceModifier,
  limit,
}: {
  strategy: StrategyCatalogEntry;
  city: string;
  cbsaCode: string;
  service: string;
  primaryKeyword: string;
  referenceCityId: string;
  aiResilienceModifier: AIResilienceModifierState;
  limit: number;
}): StrategyDiscoverRequest {
  return {
    lens_id: strategy.strategy_id,
    city_filters: cbsaCode.trim()
      ? [{ field: "cbsa_code", operator: "=", value: cbsaCode.trim() }]
      : city.trim()
      ? [{ field: "name", operator: "like", value: city.trim() }]
      : [],
    service_filters: service.trim()
      ? [{ field: "name", operator: "like", value: service.trim() }]
      : [],
    primary_keyword:
      strategy.input_shape === "city_service_keyword" ? primaryKeyword.trim() : null,
    reference_city_id:
      strategy.input_shape === "reference_city_service" ? referenceCityId.trim() : null,
    ...toAIResilienceFilterPayload(aiResilienceModifier),
    limit,
  };
}

function liveReportTarget({
  strategy,
  city,
  cbsaCode,
  service,
  primaryKeyword,
  referenceCityId,
  feasibilityPreflightPassed,
  aiResilienceModifier,
  limit,
}: {
  strategy: StrategyCatalogEntry;
  city: string;
  cbsaCode: string;
  service: string;
  primaryKeyword: string;
  referenceCityId: string;
  feasibilityPreflightPassed: boolean;
  aiResilienceModifier: AIResilienceModifierState;
  limit: number;
}): LiveReportTarget {
  return {
    strategyId: strategy.strategy_id,
    inputShape: strategy.input_shape,
    city: strategy.input_shape === "reference_city_service" ? "" : city.trim(),
    cbsaCode: strategy.input_shape === "reference_city_service" ? "" : cbsaCode.trim(),
    service: service.trim(),
    primaryKeyword:
      strategy.input_shape === "city_service_keyword" ? primaryKeyword.trim() : "",
    referenceCityId:
      strategy.input_shape === "reference_city_service" ? referenceCityId.trim() : "",
    feasibilityPreflightPassed:
      strategy.strategy_id === "keyword_hijack" ? feasibilityPreflightPassed : false,
    aiResilienceModifier,
    limit,
  };
}

function liveReportTargetLabel(target: LiveReportTarget) {
  if (target.inputShape === "reference_city_service") {
    return `${target.referenceCityId} + ${target.service}`;
  }
  return `${target.city} + ${target.service}`;
}

function liveReportTargetKey(target: LiveReportTarget) {
  return JSON.stringify([
    target.strategyId,
    target.inputShape,
    target.city,
    target.cbsaCode,
    target.referenceCityId,
    target.service,
    target.primaryKeyword,
    target.feasibilityPreflightPassed,
    target.aiResilienceModifier.threshold,
    target.aiResilienceModifier.hide_flagged,
    target.limit,
  ]);
}

function buildFreshRunPayload(target: LiveReportTarget): StrategyRunRequest {
  const payload: StrategyRunRequest = {
    mode: "fresh",
    strategy_id: target.strategyId,
    service: target.service,
    ...toAIResilienceFilterPayload(target.aiResilienceModifier),
    limit: target.limit,
  };

  if (target.inputShape === "reference_city_service") {
    payload.reference_city_id = target.referenceCityId;
    payload.city = target.referenceCityId;
  } else {
    payload.city = target.city;
  }

  if (target.inputShape === "city_service_keyword") {
    payload.primary_keyword = target.primaryKeyword;
  }

  if (target.strategyId === "keyword_hijack") {
    payload.feasibility_preflight_passed = target.feasibilityPreflightPassed;
  }

  return payload;
}

function responseMessage(body: StrategyRunResponse, fallback: string) {
  return body.message ?? body.detail ?? fallback;
}

function isUpgradePath(body: StrategyRunResponse) {
  return body.code === "fresh_strategy_runs_not_included" || body.status === "tier_limit";
}

function isQuotaExhausted(body: StrategyRunResponse) {
  return (
    body.code === "monthly_report_quota_exceeded" ||
    body.code === "quota_exceeded" ||
    body.status === "quota_exceeded"
  );
}

function initialInputValue(value: string | undefined): string {
  return value?.trim() ?? "";
}

function LiveReportRecoveryCard({
  target,
  state,
  onRun,
}: {
  target: LiveReportTarget;
  state: LiveRunState;
  onRun: () => void;
}) {
  const targetLabel = liveReportTargetLabel(target);
  const isRunning = state.status === "loading";
  const reportId = state.status === "success" ? state.response.report_id : null;
  const runId = state.status === "success" ? state.response.run_id : null;

  return (
    <article
      style={{
        background: "var(--card)",
        border: "1px solid var(--rule-strong)",
        borderRadius: 8,
        padding: 18,
        display: "flex",
        flexDirection: "column",
        gap: 14,
      }}
    >
      <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
        <div
          aria-hidden="true"
          style={{
            width: 34,
            height: 34,
            borderRadius: 8,
            display: "grid",
            placeItems: "center",
            color: "var(--accent-ink)",
            background: "var(--accent-soft)",
            flex: "0 0 auto",
          }}
        >
          <Icon d={I.sparkle} size={18} />
        </div>
        <div>
          <div style={{ color: "var(--ink-3)", fontFamily: "var(--mono)", fontSize: 12, marginBottom: 6 }}>
            Live report option
          </div>
          <h3 style={{ margin: 0, color: "var(--ink)", fontSize: 17 }}>
            Run a fresh report for this target
          </h3>
          <p style={{ margin: "8px 0 0", color: "var(--ink-2)", fontSize: 13, lineHeight: 1.55 }}>
            Cached discovery did not have a match for {targetLabel}. Generate fresh data and open the report when it is ready.
          </p>
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
          gap: 10,
        }}
      >
        <div
          style={{
            border: "1px solid var(--rule)",
            borderRadius: 8,
            padding: 10,
            background: "color-mix(in srgb, var(--accent-soft) 18%, var(--card))",
          }}
        >
          <div style={{ color: "var(--ink-3)", fontSize: 12 }}>Target</div>
          <strong style={{ color: "var(--ink)", fontSize: 13 }}>{targetLabel}</strong>
        </div>
        {target.inputShape === "city_service_keyword" ? (
          <div
            style={{
              border: "1px solid var(--rule)",
              borderRadius: 8,
              padding: 10,
              background: "color-mix(in srgb, var(--accent-soft) 18%, var(--card))",
            }}
          >
            <div style={{ color: "var(--ink-3)", fontSize: 12 }}>Primary keyword</div>
            <strong style={{ color: "var(--ink)", fontSize: 13 }}>{target.primaryKeyword}</strong>
          </div>
        ) : null}
        <div
          style={{
            border: "1px solid var(--rule)",
            borderRadius: 8,
            padding: 10,
            background: "color-mix(in srgb, var(--accent-soft) 18%, var(--card))",
          }}
        >
          <div style={{ color: "var(--ink-3)", fontSize: 12 }}>Paid plan cost</div>
          <strong style={{ color: "var(--ink)", fontSize: 13 }}>1 report credit</strong>
        </div>
      </div>

      {target.strategyId === "keyword_hijack" ? (
        <div
          style={{
            border: "1px solid var(--rule)",
            borderRadius: 8,
            background: "var(--warn-soft)",
            color: "var(--warn)",
            padding: 12,
            fontSize: 13,
            lineHeight: 1.5,
          }}
        >
          Feasibility preflight passed. Keep the keyword lens narrow and avoid keyword stuffing or misleading page intent.
        </div>
      ) : null}

      <p style={{ margin: 0, color: "var(--ink-2)", fontSize: 13, lineHeight: 1.5 }}>
        Live report generation uses 1 monthly report credit for paid users. Free users can keep browsing cached results or upgrade from Settings.
      </p>

      {state.status === "upgrade" ? (
        <div
          role="alert"
          style={{
            border: "1px solid var(--rule)",
            borderRadius: 8,
            background: "var(--warn-soft)",
            color: "var(--warn)",
            padding: 12,
            fontSize: 13,
            lineHeight: 1.5,
          }}
        >
          {state.message}{" "}
          <a href="/settings" style={{ color: "inherit", fontWeight: 800 }}>
            Upgrade to run live
          </a>
          .
        </div>
      ) : null}

      {state.status === "quota" ? (
        <div
          role="alert"
          style={{
            border: "1px solid var(--rule)",
            borderRadius: 8,
            background: "var(--warn-soft)",
            color: "var(--warn)",
            padding: 12,
            fontSize: 13,
            lineHeight: 1.5,
          }}
        >
          {state.message}{" "}
          <a href="/settings" style={{ color: "inherit", fontWeight: 800 }}>
            Manage your plan in Settings
          </a>
          .
        </div>
      ) : null}

      {state.status === "error" ? (
        <div
          role="alert"
          style={{
            border: "1px solid var(--rule)",
            borderRadius: 8,
            background: "var(--danger-soft)",
            color: "var(--danger)",
            padding: 12,
            fontSize: 13,
          }}
        >
          {state.message}
        </div>
      ) : null}

      {state.status === "success" ? (
        <div
          role="status"
          style={{
            border: "1px solid var(--rule)",
            borderRadius: 8,
            background: "var(--accent-soft)",
            color: "var(--accent-ink)",
            padding: 12,
            fontSize: 13,
            lineHeight: 1.6,
          }}
        >
          Live report queued.
          {runId ? (
            <> Run id <span style={{ fontFamily: "var(--mono)", color: "var(--ink)" }}>{runId}</span>.</>
          ) : null}
          {reportId ? (
            <>
              {" "}
              <a href={`/reports/${encodeURIComponent(reportId)}`} style={{ color: "inherit", fontWeight: 800 }}>
                Open report
              </a>
              .
            </>
          ) : null}
        </div>
      ) : null}

      <button type="button" className="btn-primary" onClick={onRun} disabled={isRunning || state.status === "success"}>
        {isRunning ? "Queueing live report..." : "Run live report"} <Icon d={I.arrow} />
      </button>
    </article>
  );
}

export default function StrategyPageClient({
  strategy,
  lockedReason = null,
  initialInputs = {},
}: {
  strategy: StrategyCatalogEntry;
  lockedReason?: string | null;
  initialInputs?: StrategyInitialInputs;
}) {
  const [city, setCity] = useState(() => initialInputValue(initialInputs.city));
  const [cbsaCode, setCbsaCode] = useState(() => initialInputValue(initialInputs.cbsa_code));
  const [service, setService] = useState(() => initialInputValue(initialInputs.service));
  const [primaryKeyword, setPrimaryKeyword] = useState(() =>
    initialInputValue(initialInputs.primary_keyword),
  );
  const [referenceCityId, setReferenceCityId] = useState(() =>
    initialInputValue(initialInputs.reference_city_id),
  );
  const [keywordIntentConfirmed, setKeywordIntentConfirmed] = useState(false);
  const [keywordComplianceConfirmed, setKeywordComplianceConfirmed] = useState(false);
  const [aiResilienceModifier, setAiResilienceModifier] = useState<AIResilienceModifierState>(
    DEFAULT_AI_RESILIENCE_MODIFIER_STATE,
  );
  const [limit, setLimit] = useState(10);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<StrategyResultSummaryDto[]>([]);
  const [zeroResultTarget, setZeroResultTarget] = useState<LiveReportTarget | null>(null);
  const [liveRunState, setLiveRunState] = useState<LiveRunState>({ status: "idle" });
  const liveRunRequestIdRef = useRef(0);
  const zeroResultTargetKeyRef = useRef<string | null>(null);

  const isPhase2Unavailable = strategy.status === "phase_2";
  const isUnavailable = isPhase2Unavailable || Boolean(lockedReason);
  const isKeywordHijack = strategy.strategy_id === "keyword_hijack";
  const feasibilityPreflightPassed =
    !isKeywordHijack || (keywordIntentConfirmed && keywordComplianceConfirmed);

  const visibleResults = useMemo(
    () =>
      filterAIResilienceFlagged(
        results,
        (result) => result.ai_resilience_score,
        aiResilienceModifier,
      ),
    [aiResilienceModifier, results],
  );
  const hiddenFlaggedResultCount = results.length - visibleResults.length;

  const canSubmit = useMemo(() => {
    if (isUnavailable || isLoading) return false;
    if (strategy.input_shape === "reference_city_service") {
      return referenceCityId.trim().length > 0 && service.trim().length > 0;
    }
    if (strategy.input_shape === "city_service_keyword") {
      return (
        city.trim().length > 0 &&
        service.trim().length > 0 &&
        primaryKeyword.trim().length > 0 &&
        (!isKeywordHijack || primaryKeywordTokenCount(primaryKeyword) >= 2) &&
        feasibilityPreflightPassed
      );
    }
    return city.trim().length > 0 && service.trim().length > 0;
  }, [
    city,
    feasibilityPreflightPassed,
    isKeywordHijack,
    isLoading,
    isUnavailable,
    primaryKeyword,
    referenceCityId,
    service,
    strategy.input_shape,
  ]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit) return;

    const payload = buildPayload({
      strategy,
      city,
      cbsaCode,
      service,
      primaryKeyword,
      referenceCityId,
      aiResilienceModifier,
      limit,
    });
    const requestedTarget = liveReportTarget({
      strategy,
      city,
      cbsaCode,
      service,
      primaryKeyword,
      referenceCityId,
      feasibilityPreflightPassed,
      aiResilienceModifier,
      limit,
    });

    setIsLoading(true);
    setError(null);
    setResults([]);
    setZeroResultTarget(null);
    setLiveRunState({ status: "idle" });
    liveRunRequestIdRef.current += 1;
    zeroResultTargetKeyRef.current = null;

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
      setResults(
        rawResults.map((item, index) =>
          normalizeResult({
            item,
            index,
            strategy,
          }),
        ),
      );
      if (rawResults.length === 0) {
        zeroResultTargetKeyRef.current = liveReportTargetKey(requestedTarget);
        setZeroResultTarget(requestedTarget);
        setError(`No matching cached markets were returned for ${liveReportTargetLabel(requestedTarget)}.`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Strategy discovery request failed.");
    } finally {
      setIsLoading(false);
    }
  }

  async function runLiveReport() {
    if (!zeroResultTarget || liveRunState.status === "loading") return;

    const requestTarget = zeroResultTarget;
    const requestTargetKey = liveReportTargetKey(requestTarget);
    const requestId = liveRunRequestIdRef.current + 1;
    liveRunRequestIdRef.current = requestId;
    zeroResultTargetKeyRef.current = requestTargetKey;
    setLiveRunState({ status: "loading" });

    const isCurrentLiveRun = () =>
      liveRunRequestIdRef.current === requestId &&
      zeroResultTargetKeyRef.current === requestTargetKey;

    try {
      const response = await fetch("/api/strategies/runs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildFreshRunPayload(requestTarget)),
      });
      const body = (await response.json().catch(() => ({}))) as StrategyRunResponse;
      if (!isCurrentLiveRun()) return;

      if (!response.ok) {
        if (isUpgradePath(body)) {
          setLiveRunState({
            status: "upgrade",
            message: responseMessage(
              body,
              "Live reports are available on paid plans. Upgrade to run this fresh report.",
            ),
          });
          return;
        }
        if (isQuotaExhausted(body)) {
          setLiveRunState({
            status: "quota",
            message: responseMessage(
              body,
              "This account has used its monthly live report credits.",
            ),
          });
          return;
        }
        setLiveRunState({
          status: "error",
          message: responseMessage(body, "Live report could not be queued."),
        });
        return;
      }

      setLiveRunState({ status: "success", response: body });
    } catch (err) {
      if (!isCurrentLiveRun()) return;
      setLiveRunState({
        status: "error",
        message: err instanceof Error ? err.message : "Live report could not be queued.",
      });
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

        {lockedReason ? (
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
            {lockedReason}
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
                  onChange={(event) => {
                    setCity(event.target.value);
                    setCbsaCode("");
                  }}
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

          {isKeywordHijack ? (
            <fieldset
              style={{
                border: "1px solid var(--rule)",
                borderRadius: 8,
                padding: 12,
                display: "flex",
                flexDirection: "column",
                gap: 10,
                background: "var(--paper-alt)",
              }}
            >
              <legend
                style={{
                  color: "var(--ink)",
                  fontSize: 13,
                  fontWeight: 800,
                  padding: "0 4px",
                }}
              >
                <Term termKey="feasibility" label="Feasibility preflight" />
              </legend>
              <p style={{ color: "var(--ink-2)", fontSize: 13, lineHeight: 1.5, margin: 0 }}>
                Confirm the keyword is a real service-intent query before spending a fresh report credit.
              </p>
              <label style={{ display: "flex", gap: 8, alignItems: "flex-start", color: "var(--ink-2)", fontSize: 13, lineHeight: 1.45 }}>
                <input
                  type="checkbox"
                  checked={keywordIntentConfirmed}
                  onChange={(event) => setKeywordIntentConfirmed(event.target.checked)}
                  disabled={isUnavailable}
                />
                The keyword matches the city and service intent.
              </label>
              <label style={{ display: "flex", gap: 8, alignItems: "flex-start", color: "var(--ink-2)", fontSize: 13, lineHeight: 1.45 }}>
                <input
                  type="checkbox"
                  checked={keywordComplianceConfirmed}
                  onChange={(event) => setKeywordComplianceConfirmed(event.target.checked)}
                  disabled={isUnavailable}
                />
                The plan avoids keyword stuffing and misleading page intent.
              </label>
            </fieldset>
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

          <AIResilienceModifierControls
            value={aiResilienceModifier}
            onChange={setAiResilienceModifier}
            disabled={isUnavailable}
            idPrefix={`strategy-${strategy.strategy_id}-ai-resilience`}
          />

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

        {hiddenFlaggedResultCount > 0 ? (
          <div
            role="status"
            style={{
              background: "var(--warn-soft)",
              color: "var(--warn)",
              border: "1px solid var(--rule)",
              borderRadius: 8,
              padding: 12,
              fontSize: 13,
              lineHeight: 1.5,
            }}
          >
            {hiddenFlaggedResultCount} flagged{" "}
            {hiddenFlaggedResultCount === 1 ? "market is" : "markets are"} hidden by
            the AI Resilience modifier.
          </div>
        ) : null}

        {visibleResults.length > 0 ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {visibleResults.map((result) => (
              <StrategyResultSummary
                key={result.id}
                summary={result}
                aiResilienceThreshold={aiResilienceModifier.threshold}
                modifierState={aiResilienceModifier}
              />
            ))}
          </div>
        ) : results.length > 0 ? (
          <div
            style={{
              background: "var(--card)",
              border: "1px solid var(--rule)",
              borderRadius: 8,
              padding: 16,
              color: "var(--ink-3)",
              fontSize: 13,
              lineHeight: 1.5,
            }}
          >
            All returned markets are hidden by the current AI Resilience threshold.
          </div>
        ) : zeroResultTarget ? (
          <>
            <LiveReportRecoveryCard target={zeroResultTarget} state={liveRunState} onRun={runLiveReport} />
            <div
              style={{
                background: "var(--card)",
                border: "1px solid var(--rule)",
                borderRadius: 8,
                padding: 16,
                color: "var(--ink-3)",
                fontSize: 13,
                lineHeight: 1.5,
              }}
            >
              Cached discovery returned zero rows for this strategy lens and target.
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
            }}
          >
            Run a launch strategy to populate this list.
          </div>
        )}
      </section>
    </div>
  );
}
