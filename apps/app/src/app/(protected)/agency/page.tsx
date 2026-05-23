"use client";

import Link from "next/link";
import {
  type CSSProperties,
  type ReactNode,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import StateMultiselect from "@/components/StateMultiselect";
import { Icon, I } from "@/lib/icons";

type Step = "configure" | "confirm" | "complete";
type StrategyId = "easy_win" | "gbp_blitz" | "keyword_hijack" | "expand_conquer";
type TargetSource = "cached" | "custom";

interface ServiceOption {
  id: string;
  label: string;
  note: string;
}

interface DiscoveryMarket {
  rank?: number;
  opportunity_score?: number;
  city?: {
    city_id?: string;
    name?: string;
    state?: string | null;
    population?: number | null;
  };
  service?: {
    service_id?: string;
    name?: string;
  };
}

interface DiscoveryResponse {
  markets?: DiscoveryMarket[];
  detail?: string;
  message?: string;
  code?: string;
}

interface QueuedTarget {
  cbsa_code: string;
  city_name: string;
  state: string | null;
  population: number | null;
  niche_normalized: string;
  niche_keyword: string;
  primary_keyword?: string;
  opportunity_score: number | null;
  rank: number | null;
  source: TargetSource;
}

interface CustomTargetRow {
  id: string;
  city: string;
  state: string;
  service: string;
  primary_keyword: string;
}

interface RunResponse {
  run_id?: string;
  status?: string;
  target_count?: number;
  detail?: string;
  message?: string;
  code?: string;
}

const TARGET_CAP = 100;
const SCAN_COST = 1;
const SERVICE_OPTIONS: ServiceOption[] = [
  { id: "plumbing", label: "Plumbing", note: "Emergency and repair demand" },
  { id: "hvac", label: "HVAC", note: "Seasonal replacement value" },
  { id: "roofing", label: "Roofing", note: "High-ticket local leads" },
  { id: "tree_service", label: "Tree service", note: "Fragmented local SERPs" },
  { id: "pest_control", label: "Pest control", note: "Recurring service intent" },
  { id: "water_damage", label: "Water damage", note: "Urgent restoration searches" },
];
const STRATEGY_LENSES: {
  id: StrategyId;
  label: string;
  copy: string;
  icon: string;
}[] = [
  {
    id: "easy_win",
    label: "Easy Win",
    copy: "Weaker competition and useful demand.",
    icon: I.star,
  },
  {
    id: "gbp_blitz",
    label: "GBP Blitz",
    copy: "Local pack gaps and profile weakness.",
    icon: I.mapPin,
  },
  {
    id: "keyword_hijack",
    label: "Keyword Hijack",
    copy: "Primary keyword openings by market.",
    icon: I.search,
  },
  {
    id: "expand_conquer",
    label: "Expand & Conquer",
    copy: "Expansion markets from cached signals.",
    icon: I.target,
  },
];

function normalizeNiche(value: string) {
  return value.trim().toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
}

function normalizeCustomIdPart(value: string) {
  return normalizeNiche(value).replace(/_+/g, "-") || "target";
}

function normalizeState(value: string) {
  return value.trim().toUpperCase().replace(/[^A-Z]/g, "").slice(0, 2);
}

function isTwoLetterState(value: string) {
  return /^[A-Za-z]{2}$/.test(value.trim());
}

function formatNumber(value: number) {
  return new Intl.NumberFormat("en-US").format(value);
}

function parsePopulationInput(value: string) {
  const normalized = value.trim();
  if (normalized.length === 0) return 0;
  if (!/^\d+$/.test(normalized)) return null;
  const parsed = Number(normalized);
  return Number.isSafeInteger(parsed) ? parsed : null;
}

function requestMessage(body: DiscoveryResponse | RunResponse, fallback: string) {
  return body.message ?? body.detail ?? body.code ?? fallback;
}

async function readJson<T>(response: Response): Promise<T> {
  try {
    return (await response.json()) as T;
  } catch {
    return {} as T;
  }
}

function uniqueTargets(targets: QueuedTarget[]) {
  const byKey = new Map<string, QueuedTarget>();
  for (const target of targets) {
    byKey.set(`${target.cbsa_code}:${target.niche_normalized}`, target);
  }
  return [...byKey.values()];
}

function hasCustomInput(row: CustomTargetRow) {
  return [row.city, row.state, row.service, row.primary_keyword].some(
    (value) => value.trim().length > 0,
  );
}

function customRowReady(row: CustomTargetRow) {
  return (
    row.city.trim().length >= 2 &&
    isTwoLetterState(row.state) &&
    normalizeNiche(row.service).length > 0
  );
}

function hasPrimaryKeyword(value: string) {
  return value.trim().length >= 2;
}

function customRowToTarget(row: CustomTargetRow, fallbackPrimaryKeyword: string): QueuedTarget {
  const state = normalizeState(row.state);
  const service = row.service.trim();
  const rowPrimaryKeyword = row.primary_keyword.trim();
  const primaryKeyword = rowPrimaryKeyword || fallbackPrimaryKeyword.trim();
  return {
    cbsa_code: `custom:${normalizeCustomIdPart(row.city)}:${state.toLowerCase() || "na"}`,
    city_name: row.city.trim(),
    state: state || null,
    population: null,
    niche_normalized: normalizeNiche(service),
    niche_keyword: service,
    primary_keyword: primaryKeyword || undefined,
    opportunity_score: null,
    rank: null,
    source: "custom",
  };
}

function isTierLimitResponse(body: RunResponse) {
  return body.code === "fresh_strategy_runs_not_included" || body.status === "tier_limit";
}

function isQuotaResponse(body: RunResponse) {
  return (
    body.code === "monthly_report_quota_exceeded" ||
    body.code === "quota_exceeded" ||
    body.status === "quota_exceeded"
  );
}

function Card({
  title,
  children,
  style,
}: {
  title: string;
  children: ReactNode;
  style?: CSSProperties;
}) {
  return (
    <section
      aria-labelledby={`${title.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-heading`}
      style={{
        background: "var(--card)",
        border: "1px solid var(--rule)",
        borderRadius: 8,
        padding: 18,
        boxShadow: "0 1px 0 rgba(47,38,20,0.03)",
        ...style,
      }}
    >
      <h2
        id={`${title.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-heading`}
        style={{
          margin: 0,
          color: "var(--ink)",
          fontFamily: "var(--serif)",
          fontSize: 20,
          fontWeight: 600,
        }}
      >
        {title}
      </h2>
      <div style={{ marginTop: 14 }}>{children}</div>
    </section>
  );
}

function Metric({
  label,
  value,
  emphasis = false,
}: {
  label: string;
  value: string | number;
  emphasis?: boolean;
}) {
  return (
    <div
      style={{
        minHeight: 82,
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        gap: 8,
        border: "1px solid var(--rule)",
        borderRadius: 8,
        background: emphasis ? "var(--accent-soft)" : "var(--paper)",
        padding: 12,
      }}
    >
      <span
        style={{
          color: emphasis ? "var(--accent-ink)" : "var(--ink-3)",
          fontSize: 11,
          fontWeight: 700,
          textTransform: "uppercase",
          letterSpacing: "0.06em",
        }}
      >
        {label}
      </span>
      <strong
        style={{
          color: emphasis ? "var(--accent-ink)" : "var(--ink)",
          fontFamily: "var(--mono)",
          fontSize: 22,
          fontWeight: 700,
        }}
      >
        {value}
      </strong>
    </div>
  );
}

function Row({
  label,
  value,
  emphasis = false,
}: {
  label: string;
  value: string;
  emphasis?: boolean;
}) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        gap: 16,
        borderBottom: "1px solid var(--rule)",
        padding: "10px 0",
        color: "var(--ink-2)",
        fontSize: 14,
      }}
    >
      <span>{label}</span>
      <strong
        style={{
          color: emphasis ? "var(--accent-ink)" : "var(--ink)",
          fontFamily: emphasis ? "var(--mono)" : "var(--sans)",
          textAlign: "right",
        }}
      >
        {value}
      </strong>
    </div>
  );
}

export default function AgencyPage() {
  const [step, setStep] = useState<Step>("configure");
  const [strategyLens, setStrategyLens] = useState<StrategyId>("easy_win");
  const [selectedStates, setSelectedStates] = useState<string[]>([]);
  const [selectedServiceIds, setSelectedServiceIds] = useState<string[]>([]);
  const [populationMin, setPopulationMin] = useState("50000");
  const [populationMax, setPopulationMax] = useState("750000");
  const [maxMarkets, setMaxMarkets] = useState(25);
  const [primaryKeyword, setPrimaryKeyword] = useState("");
  const [customRows, setCustomRows] = useState<CustomTargetRow[]>([]);
  const [targets, setTargets] = useState<QueuedTarget[]>([]);
  const [runResult, setRunResult] = useState<RunResponse | null>(null);
  const [isPreparing, setIsPreparing] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [discoveryEmpty, setDiscoveryEmpty] = useState(false);
  const [queueNotice, setQueueNotice] = useState<{
    kind: "upgrade" | "quota";
    title: string;
    message: string;
  } | null>(null);

  const selectedServices = useMemo(
    () => SERVICE_OPTIONS.filter((service) => selectedServiceIds.includes(service.id)),
    [selectedServiceIds],
  );
  const validCustomRows = useMemo(() => customRows.filter(customRowReady), [customRows]);
  const validCustomTargets = useMemo(
    () => validCustomRows.map((row) => customRowToTarget(row, primaryKeyword)),
    [validCustomRows, primaryKeyword],
  );
  const incompleteCustomRows = useMemo(
    () => customRows.filter((row) => hasCustomInput(row) && !customRowReady(row)),
    [customRows],
  );
  const maxTargetPairs = selectedServices.length * maxMarkets;
  const totalTargetPairs = maxTargetPairs + validCustomTargets.length;
  const populationMinValue = parsePopulationInput(populationMin);
  const populationMaxValue = parsePopulationInput(populationMax);
  const populationInvalid = populationMinValue === null || populationMaxValue === null;
  const rangeInvalid =
    !populationInvalid && populationMinValue > populationMaxValue;
  const cachedFiltersInvalid = selectedServices.length > 0 && populationInvalid;
  const cachedRangeInvalid = selectedServices.length > 0 && rangeInvalid;
  const globalPrimaryKeywordReady = hasPrimaryKeyword(primaryKeyword);
  const cachedKeywordRequired =
    strategyLens === "keyword_hijack" &&
    selectedServices.length > 0 &&
    !globalPrimaryKeywordReady;
  const customKeywordRequired =
    strategyLens === "keyword_hijack" &&
    validCustomRows.some(
      (row) => !globalPrimaryKeywordReady && !hasPrimaryKeyword(row.primary_keyword),
    );
  const keywordRequired = cachedKeywordRequired || customKeywordRequired;
  const targetCapExceeded = totalTargetPairs > TARGET_CAP;
  const prepareSnapshot = useMemo(
    () =>
      JSON.stringify({
        strategyLens,
        selectedStates,
        selectedServiceIds,
        populationMin,
        populationMax,
        maxMarkets,
        primaryKeyword,
        customRows,
      }),
    [
      strategyLens,
      selectedStates,
      selectedServiceIds,
      populationMin,
      populationMax,
      maxMarkets,
      primaryKeyword,
      customRows,
    ],
  );
  const latestPrepareSnapshotRef = useRef(prepareSnapshot);
  const prepareRequestIdRef = useRef(0);
  const customRowIdCounterRef = useRef(0);
  useEffect(() => {
    latestPrepareSnapshotRef.current = prepareSnapshot;
  }, [prepareSnapshot]);
  const readyToReview =
    (selectedServices.length > 0 || validCustomTargets.length > 0) &&
    !cachedFiltersInvalid &&
    !cachedRangeInvalid &&
    !keywordRequired &&
    !targetCapExceeded &&
    incompleteCustomRows.length === 0;

  function toggleService(id: string) {
    setDiscoveryEmpty(false);
    setSelectedServiceIds((current) =>
      current.includes(id)
        ? current.filter((serviceId) => serviceId !== id)
        : [...current, id],
    );
  }

  function addCustomRow() {
    setDiscoveryEmpty(false);
    customRowIdCounterRef.current += 1;
    const nextCustomRowId = customRowIdCounterRef.current;
    setCustomRows((current) => [
      ...current,
      {
        id: `custom-${nextCustomRowId}`,
        city: "",
        state: "",
        service: "",
        primary_keyword: "",
      },
    ]);
  }

  function updateCustomRow(id: string, field: keyof Omit<CustomTargetRow, "id">, value: string) {
    setDiscoveryEmpty(false);
    setCustomRows((current) =>
      current.map((row) => (row.id === id ? { ...row, [field]: value } : row)),
    );
  }

  function removeCustomRow(id: string) {
    setCustomRows((current) => current.filter((row) => row.id !== id));
  }

  async function prepareTargets() {
    if (
      !readyToReview ||
      (selectedServices.length > 0 && (populationMinValue === null || populationMaxValue === null))
    ) {
      return;
    }
    const requestId = prepareRequestIdRef.current + 1;
    prepareRequestIdRef.current = requestId;
    const requestSnapshot = latestPrepareSnapshotRef.current;
    const isLatestRequest = () => prepareRequestIdRef.current === requestId;
    const isCurrentSnapshot = () =>
      isLatestRequest() && latestPrepareSnapshotRef.current === requestSnapshot;
    setError(null);
    setRunResult(null);
    setQueueNotice(null);
    setDiscoveryEmpty(false);
    setIsPreparing(true);

    try {
      const discovered =
        selectedServices.length > 0
          ? await Promise.all(
              selectedServices.map(async (service) => {
                const cityFilters: Record<string, unknown>[] = [
                  { field: "population", operator: ">=", value: populationMinValue ?? 0 },
                  { field: "population", operator: "<=", value: populationMaxValue ?? 0 },
                ];
                if (selectedStates.length > 0) {
                  cityFilters.push({ field: "state", operator: "in", value: selectedStates });
                }

                const response = await fetch("/api/strategies/discover", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({
                    lens_id: strategyLens,
                    primary_keyword:
                      strategyLens === "keyword_hijack" && globalPrimaryKeywordReady
                        ? primaryKeyword.trim()
                        : undefined,
                    city_filters: cityFilters,
                    service_filters: [
                      { field: "name", operator: "like", value: service.label },
                    ],
                    limit: maxMarkets,
                  }),
                });
                const body = await readJson<DiscoveryResponse>(response);
                if (!response.ok) {
                  throw new Error(
                    requestMessage(body, `Could not discover targets for ${service.label}.`),
                  );
                }
                return (body.markets ?? []).map((market): QueuedTarget | null => {
                  const cbsaCode = market.city?.city_id?.trim();
                  const serviceName = market.service?.name || service.label;
                  if (!cbsaCode) return null;
                  return {
                    cbsa_code: cbsaCode,
                    city_name: market.city?.name || cbsaCode,
                    state: market.city?.state ?? null,
                    population: market.city?.population ?? null,
                    niche_normalized:
                      market.service?.service_id || service.id || normalizeNiche(serviceName),
                    niche_keyword: serviceName,
                    primary_keyword:
                      strategyLens === "keyword_hijack" ? primaryKeyword.trim() : undefined,
                    opportunity_score:
                      typeof market.opportunity_score === "number"
                        ? market.opportunity_score
                        : null,
                    rank: typeof market.rank === "number" ? market.rank : null,
                    source: "cached",
                  };
                });
              }),
            )
          : [];

      if (!isCurrentSnapshot()) return;

      const cachedTargets = discovered.flat().filter(Boolean) as QueuedTarget[];
      const nextTargets = uniqueTargets([...cachedTargets, ...validCustomTargets]);
      if (nextTargets.length === 0) {
        setDiscoveryEmpty(true);
        return;
      }
      if (nextTargets.length > TARGET_CAP) {
        setError(`This batch has ${nextTargets.length} targets. Keep it at ${TARGET_CAP} or fewer.`);
        return;
      }
      setTargets(nextTargets);
      setStep("confirm");
    } catch (err) {
      if (isCurrentSnapshot()) {
        setError(err instanceof Error ? err.message : "Multi-market target discovery failed.");
      }
    } finally {
      if (isLatestRequest()) {
        setIsPreparing(false);
      }
    }
  }

  async function queueRun() {
    if (targets.length === 0 || isSubmitting) return;
    setError(null);
    setQueueNotice(null);
    setIsSubmitting(true);

    try {
      const response = await fetch("/api/strategies/runs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mode: "fresh",
          strategy_id: strategyLens,
          primary_keyword:
            strategyLens === "keyword_hijack" && globalPrimaryKeywordReady
              ? primaryKeyword.trim()
              : undefined,
          targets: targets.map((target) => ({
            cbsa_code: target.cbsa_code,
            niche_normalized: target.niche_normalized,
            niche_keyword: target.niche_keyword,
            ...(target.primary_keyword ? { primary_keyword: target.primary_keyword } : {}),
          })),
        }),
      });
      const body = await readJson<RunResponse>(response);
      if (!response.ok) {
        if (isTierLimitResponse(body)) {
          setQueueNotice({
            kind: "upgrade",
            title: "Fresh multi-market scans are an upgrade path.",
            message:
              "Your current plan can browse cached research, but live batch runs require Plus or Pro.",
          });
          return;
        }
        if (isQuotaResponse(body)) {
          setQueueNotice({
            kind: "quota",
            title: "Monthly report quota reached.",
            message:
              "This batch needs one report credit. Review your plan or quota before queueing more live work.",
          });
          return;
        }
        throw new Error(requestMessage(body, "Multi-market run could not be queued."));
      }
      setRunResult(body);
      setStep("complete");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Multi-market run could not be queued.");
    } finally {
      setIsSubmitting(false);
    }
  }

  const statusMessage = (() => {
    if (incompleteCustomRows.length > 0) {
      return "Custom targets need a city, 2-letter state, and valid service.";
    }
    if (selectedServices.length === 0 && validCustomTargets.length === 0) {
      return "Select cached services or add a custom city-service target.";
    }
    if (cachedFiltersInvalid) return "Population filters need whole numbers only.";
    if (cachedRangeInvalid) return "Population minimum must be lower than the maximum.";
    if (cachedKeywordRequired) {
      return "Keyword Hijack needs a global primary keyword for cached discovery.";
    }
    if (customKeywordRequired) {
      return "Keyword Hijack needs a primary keyword on every custom target or in the global field.";
    }
    if (targetCapExceeded) {
      return `This configuration can queue up to ${totalTargetPairs} targets. Keep it at ${TARGET_CAP} or fewer.`;
    }
    return `${formatNumber(totalTargetPairs)} target pairs can be queued with the current cap.`;
  })();

  return (
    <main
      className="page"
      style={{
        width: "100%",
        maxWidth: 1280,
        margin: "0 auto",
        display: "flex",
        flexDirection: "column",
        gap: 20,
      }}
    >
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          gap: 16,
          flexWrap: "wrap",
        }}
      >
        <div style={{ maxWidth: 780 }}>
          <p className="field-label" style={{ margin: 0 }}>
            Multi-market scan
          </p>
          <h1 className="page-h1" style={{ margin: "4px 0 0" }}>
            Qualify territories in one batch.
          </h1>
          <p className="page-sub" style={{ marginBottom: 0 }}>
            Configure a strategy lens, market filters, service set, or custom/live rows, then queue up to 100 city-service targets for backend processing.
          </p>
        </div>
        <div
          aria-label="Scans available"
          style={{
            minWidth: 220,
            border: "1px solid var(--rule)",
            borderRadius: 8,
            background: "var(--card)",
            padding: 14,
          }}
        >
          <div className="field-label" style={{ margin: 0 }}>
            Batch cost
          </div>
          <div
            style={{
              marginTop: 6,
              display: "flex",
              alignItems: "baseline",
              gap: 8,
              color: "var(--ink)",
            }}
          >
            <strong style={{ fontFamily: "var(--mono)", fontSize: 24 }}>{SCAN_COST}</strong>
            <span style={{ color: "var(--ink-2)", fontSize: 13 }}>scan per queued batch</span>
          </div>
        </div>
      </header>

      <nav aria-label="Multi-market step" style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {(["configure", "confirm", "complete"] as Step[]).map((item, index) => (
          <span
            key={item}
            aria-current={step === item ? "step" : undefined}
            style={{
              minHeight: 34,
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              border: `1px solid ${step === item ? "var(--accent)" : "var(--rule)"}`,
              borderRadius: 999,
              background: step === item ? "var(--accent-soft)" : "var(--card)",
              color: step === item ? "var(--accent-ink)" : "var(--ink-2)",
              padding: "6px 11px",
              fontSize: 12,
              fontWeight: 700,
              textTransform: "capitalize",
            }}
          >
            <span style={{ fontFamily: "var(--mono)" }}>{index + 1}</span>
            {item}
          </span>
        ))}
      </nav>

      {error ? (
        <div
          role="alert"
          style={{
            border: "1px solid var(--danger)",
            borderRadius: 8,
            background: "var(--danger-soft)",
            color: "var(--danger)",
            padding: "10px 12px",
            fontSize: 13,
          }}
        >
          {error}
        </div>
      ) : null}

      {queueNotice ? (
        <div
          role="alert"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 12,
            flexWrap: "wrap",
            border: "1px solid var(--warn)",
            borderRadius: 8,
            background: "var(--warn-soft)",
            color: "var(--warn)",
            padding: "12px 14px",
            fontSize: 13,
          }}
        >
          <span>
            <strong style={{ display: "block", color: "var(--ink)", marginBottom: 3 }}>
              {queueNotice.title}
            </strong>
            {queueNotice.message}
          </span>
          <Link href="/settings" className="btn-primary" style={{ textDecoration: "none" }}>
            Open settings <Icon d={I.arrow} />
          </Link>
        </div>
      ) : null}

      {step === "configure" ? (
        <>
          <Card title="Pick a strategy lens">
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 10 }}>
              {STRATEGY_LENSES.map((strategy) => {
                const active = strategyLens === strategy.id;
                return (
                  <button
                    key={strategy.id}
                    type="button"
                    aria-pressed={active}
                    onClick={() => setStrategyLens(strategy.id)}
                    style={{
                      minHeight: 112,
                      display: "flex",
                      flexDirection: "column",
                      gap: 8,
                      alignItems: "flex-start",
                      textAlign: "left",
                      border: `1px solid ${active ? "var(--accent)" : "var(--rule)"}`,
                      borderRadius: 8,
                      background: active ? "var(--accent-soft)" : "var(--card)",
                      color: "var(--ink)",
                      padding: 14,
                    }}
                  >
                    <span
                      style={{
                        width: 30,
                        height: 30,
                        borderRadius: 8,
                        display: "grid",
                        placeItems: "center",
                        background: active ? "var(--accent)" : "var(--paper-alt)",
                        color: active ? "white" : "var(--ink-2)",
                      }}
                    >
                      <Icon d={strategy.icon} size={16} />
                    </span>
                    <strong style={{ fontFamily: "var(--serif)", fontSize: 18 }}>
                      {strategy.label}
                    </strong>
                    <span style={{ color: "var(--ink-2)", fontSize: 12, lineHeight: 1.4 }}>
                      {strategy.copy}
                    </span>
                  </button>
                );
              })}
            </div>
            {strategyLens === "keyword_hijack" ? (
              <label style={{ display: "block", marginTop: 14 }}>
                <span className="field-label">Primary keyword</span>
                <div className="input-wrap">
                  <Icon d={I.search} />
                  <input
                    value={primaryKeyword}
                    onChange={(event) => setPrimaryKeyword(event.target.value)}
                    placeholder="e.g. emergency plumber"
                  />
                </div>
              </label>
            ) : null}
          </Card>

          <Card title="Market criteria">
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", gap: 12, alignItems: "end" }}>
              <label>
                <span className="field-label">Population min</span>
                <div className="input-wrap">
                  <Icon d={I.filter} />
                  <input
                    aria-label="Minimum population"
                    aria-invalid={populationMinValue === null}
                    inputMode="numeric"
                    value={populationMin}
                    onChange={(event) => setPopulationMin(event.target.value)}
                  />
                </div>
              </label>
              <label>
                <span className="field-label">Population max</span>
                <div className="input-wrap">
                  <Icon d={I.filter} />
                  <input
                    aria-label="Maximum population"
                    aria-invalid={populationMaxValue === null}
                    inputMode="numeric"
                    value={populationMax}
                    onChange={(event) => setPopulationMax(event.target.value)}
                  />
                </div>
              </label>
              <StateMultiselect
                label="States"
                selected={selectedStates}
                onChange={setSelectedStates}
              />
              <label>
                <span className="field-label">Markets per service</span>
                <select
                  aria-label="Markets per service"
                  value={maxMarkets}
                  onChange={(event) => setMaxMarkets(Number(event.target.value))}
                  style={{
                    width: "100%",
                    minHeight: 42,
                    border: "1px solid var(--rule-strong)",
                    borderRadius: 8,
                    background: "var(--card)",
                    color: "var(--ink)",
                    padding: "0 12px",
                    fontSize: 13,
                  }}
                >
                  <option value={10}>10 markets</option>
                  <option value={25}>25 markets</option>
                  <option value={50}>50 markets</option>
                  <option value={100}>100 markets</option>
                </select>
              </label>
            </div>
          </Card>

          <Card title="Services to scan">
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))", gap: 10 }}>
              {SERVICE_OPTIONS.map((service) => {
                const active = selectedServiceIds.includes(service.id);
                return (
                  <button
                    key={service.id}
                    type="button"
                    aria-pressed={active}
                    onClick={() => toggleService(service.id)}
                    style={{
                      minHeight: 98,
                      textAlign: "left",
                      border: `1px solid ${active ? "var(--accent)" : "var(--rule)"}`,
                      borderRadius: 8,
                      background: active ? "var(--accent-soft)" : "var(--card)",
                      color: "var(--ink)",
                      padding: 14,
                    }}
                  >
                    <span style={{ display: "flex", gap: 8, alignItems: "center" }}>
                      <span
                        aria-hidden="true"
                        style={{
                          width: 16,
                          height: 16,
                          borderRadius: 4,
                          border: `1.5px solid ${active ? "var(--accent)" : "var(--rule-strong)"}`,
                          background: active ? "var(--accent)" : "var(--card)",
                          color: "white",
                          display: "grid",
                          placeItems: "center",
                        }}
                      >
                        {active ? <Icon d={I.check} size={10} sw={3} /> : null}
                      </span>
                      <strong style={{ fontFamily: "var(--serif)", fontSize: 17 }}>
                        {service.label}
                      </strong>
                    </span>
                    <span style={{ display: "block", marginTop: 8, color: "var(--ink-2)", fontSize: 12, lineHeight: 1.4 }}>
                      {service.note}
                    </span>
                  </button>
                );
              })}
            </div>
          </Card>

          <Card title="Custom city-service targets">
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
                gap: 12,
                flexWrap: "wrap",
              }}
            >
              <p style={{ margin: 0, color: "var(--ink-2)", fontSize: 13, lineHeight: 1.5 }}>
                Add city-service pairs when cached discovery is empty or the market you want is missing.
              </p>
              <button type="button" className="btn-ghost" onClick={addCustomRow}>
                <Icon d={I.plus} />
                Add custom target
              </button>
            </div>

            {customRows.length > 0 ? (
              <div style={{ display: "grid", gap: 10, marginTop: 14 }}>
                {customRows.map((row, index) => (
                  <div
                    key={row.id}
                    style={{
                      display: "grid",
                      gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
                      gap: 8,
                      alignItems: "end",
                    }}
                  >
                    <label>
                      <span className="field-label">City</span>
                      <div className="input-wrap">
                        <Icon d={I.mapPin} />
                        <input
                          aria-label={`Custom target ${index + 1} city`}
                          value={row.city}
                          onChange={(event) =>
                            updateCustomRow(row.id, "city", event.target.value)
                          }
                          placeholder="e.g. Boise"
                        />
                      </div>
                    </label>
                    <label>
                      <span className="field-label">State</span>
                      <div className="input-wrap">
                        <Icon d={I.mapPin} />
                        <input
                          aria-label={`Custom target ${index + 1} state`}
                          value={row.state}
                          onChange={(event) =>
                            updateCustomRow(row.id, "state", event.target.value)
                          }
                          placeholder="ID"
                          maxLength={2}
                        />
                      </div>
                    </label>
                    <label>
                      <span className="field-label">Service</span>
                      <div className="input-wrap">
                        <Icon d={I.search} />
                        <input
                          aria-label={`Custom target ${index + 1} service`}
                          value={row.service}
                          onChange={(event) =>
                            updateCustomRow(row.id, "service", event.target.value)
                          }
                          placeholder="e.g. Roofing"
                        />
                      </div>
                    </label>
                    <label>
                      <span className="field-label">Primary keyword</span>
                      <div className="input-wrap">
                        <Icon d={I.target} />
                        <input
                          aria-label={`Custom target ${index + 1} primary keyword`}
                          value={row.primary_keyword}
                          onChange={(event) =>
                            updateCustomRow(row.id, "primary_keyword", event.target.value)
                          }
                          placeholder="optional"
                        />
                      </div>
                    </label>
                    <button
                      type="button"
                      className="btn-ghost"
                      aria-label={`Remove custom target ${index + 1}`}
                      onClick={() => removeCustomRow(row.id)}
                      style={{ minHeight: 42 }}
                    >
                      <Icon d={I.x} />
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p style={{ margin: "14px 0 0", color: "var(--ink-3)", fontSize: 13 }}>
                No custom targets yet.
              </p>
            )}
          </Card>

          <Card title="Run summary">
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 10 }}>
              <Metric label="Services" value={selectedServices.length} />
              <Metric label="Custom" value={validCustomTargets.length} />
              <Metric label="Market cap" value={maxMarkets} />
              <Metric label="Max targets" value={formatNumber(totalTargetPairs)} />
              <Metric label="Batch cost" value={SCAN_COST} emphasis />
            </div>
            <div
              style={{
                marginTop: 16,
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 12,
                flexWrap: "wrap",
              }}
            >
              <p
                role={readyToReview ? "status" : "alert"}
                style={{
                  margin: 0,
                  color: readyToReview ? "var(--ink-2)" : "var(--danger)",
                  fontSize: 13,
                }}
              >
                {statusMessage}
              </p>
              <button
                type="button"
                className="btn-primary"
                disabled={!readyToReview || isPreparing}
                onClick={prepareTargets}
              >
                {isPreparing ? "Finding targets..." : "Review targets"}
                <Icon d={I.arrow} />
              </button>
            </div>
          </Card>

          {discoveryEmpty ? (
            <section
              role="status"
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 14,
                flexWrap: "wrap",
                border: "1px solid var(--rule)",
                borderRadius: 8,
                background: "var(--paper)",
                padding: 16,
              }}
            >
              <div style={{ maxWidth: 680 }}>
                <strong style={{ display: "block", color: "var(--ink)", fontFamily: "var(--serif)", fontSize: 20 }}>
                  No cached markets matched this configuration.
                </strong>
                <p style={{ margin: "6px 0 0", color: "var(--ink-2)", fontSize: 13, lineHeight: 1.5 }}>
                  Add custom city-service targets to queue live research, or widen filters and try cached discovery again.
                </p>
              </div>
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                <button type="button" className="btn-primary" onClick={addCustomRow}>
                  Add city-service targets <Icon d={I.plus} />
                </button>
                <button
                  type="button"
                  className="btn-ghost"
                  onClick={() => {
                    setSelectedStates([]);
                    setPopulationMin("0");
                    setPopulationMax("1000000");
                    setDiscoveryEmpty(false);
                  }}
                >
                  Widen filters
                </button>
              </div>
            </section>
          ) : null}
        </>
      ) : null}

      {step === "confirm" ? (
        <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1.1fr) minmax(280px, 0.9fr)", gap: 16 }}>
          <Card title="Confirm the batch">
            <Row label="Strategy lens" value={STRATEGY_LENSES.find((strategy) => strategy.id === strategyLens)?.label ?? strategyLens} />
            <Row label="States" value={selectedStates.length > 0 ? selectedStates.join(", ") : "All states"} />
            <Row label="Cached services" value={selectedServices.length > 0 ? selectedServices.map((service) => service.label).join(", ") : "None selected"} />
            <Row label="Custom targets" value={formatNumber(targets.filter((target) => target.source === "custom").length)} />
            <Row label="Queued targets" value={formatNumber(targets.length)} />
            <Row label="Cost" value={`${SCAN_COST} scan`} emphasis />
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 18, flexWrap: "wrap" }}>
              <button type="button" className="btn-ghost" onClick={() => setStep("configure")}>
                Back
              </button>
              <button
                type="button"
                className="btn-primary"
                disabled={isSubmitting || targets.length === 0}
                onClick={queueRun}
              >
                {isSubmitting ? "Queueing..." : "Queue batch"}
                <Icon d={I.arrow} />
              </button>
            </div>
          </Card>

          <Card title="Target preview">
            <div style={{ display: "grid", gap: 8 }}>
              {targets.slice(0, 8).map((target) => (
                <div
                  key={`${target.cbsa_code}:${target.niche_normalized}`}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "minmax(0, 1fr) auto",
                    gap: 8,
                    border: "1px solid var(--rule)",
                    borderRadius: 8,
                    background: "var(--paper)",
                    padding: "9px 10px",
                    fontSize: 13,
                  }}
                >
                  <div style={{ minWidth: 0 }}>
                    <strong style={{ display: "block", color: "var(--ink)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {target.city_name}{target.state ? `, ${target.state}` : ""}
                    </strong>
                    <span style={{ color: "var(--ink-2)" }}>{target.niche_keyword}</span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span
                      aria-label={`Source ${target.source === "cached" ? "cached" : "custom/live"}`}
                      style={{
                        border: "1px solid var(--rule)",
                        borderRadius: 999,
                        color: target.source === "cached" ? "var(--ink-2)" : "var(--accent-ink)",
                        background: target.source === "cached" ? "var(--card)" : "var(--accent-soft)",
                        padding: "3px 7px",
                        fontSize: 11,
                        fontWeight: 800,
                        textTransform: "uppercase",
                      }}
                    >
                      {target.source === "cached" ? "cached" : "custom/live"}
                    </span>
                    <span style={{ color: "var(--accent-ink)", fontFamily: "var(--mono)", fontWeight: 700 }}>
                      {target.opportunity_score == null ? "new" : Math.round(target.opportunity_score)}
                    </span>
                  </div>
                </div>
              ))}
              {targets.length > 8 ? (
                <p style={{ margin: "4px 0 0", color: "var(--ink-3)", fontSize: 12 }}>
                  +{formatNumber(targets.length - 8)} more targets queued in this batch.
                </p>
              ) : null}
            </div>
          </Card>
        </div>
      ) : null}

      {step === "complete" ? (
        <Card title="Scan queued" style={{ maxWidth: 720, margin: "0 auto", textAlign: "center" }}>
          <div
            aria-hidden="true"
            style={{
              width: 48,
              height: 48,
              borderRadius: "50%",
              display: "grid",
              placeItems: "center",
              margin: "0 auto 14px",
              background: "var(--accent-soft)",
              color: "var(--accent-ink)",
            }}
          >
            <Icon d={I.check} size={24} sw={2.4} />
          </div>
          <p style={{ margin: 0, color: "var(--ink-2)", lineHeight: 1.55 }}>
            {formatNumber(runResult?.target_count ?? targets.length)} city-service targets are queued for the scoring pipeline.
            {runResult?.run_id ? (
              <> Run id <span style={{ fontFamily: "var(--mono)", color: "var(--ink)" }}>{runResult.run_id}</span>.</>
            ) : null}
          </p>
          <div style={{ marginTop: 18, display: "flex", justifyContent: "center", gap: 10, flexWrap: "wrap" }}>
            <Link href="/" className="btn-primary" style={{ textDecoration: "none" }}>
              Dashboard <Icon d={I.home} />
            </Link>
            <Link href="/reports" className="btn-ghost" style={{ textDecoration: "none" }}>
              Reports
            </Link>
            <button
              type="button"
              className="btn-ghost"
              onClick={() => {
                setStep("configure");
                setTargets([]);
                setRunResult(null);
              }}
            >
              Configure another
            </button>
          </div>
        </Card>
      ) : null}
    </main>
  );
}
