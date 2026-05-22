"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { ARCHETYPES } from "@/lib/archetypes";
import type {
  ExploreCitySummary,
  ExploreData,
  ExploreScanTarget,
} from "@/lib/explore/types";
import { normalizeExploreCity } from "@/lib/explore/normalize-explore-data";
import type {
  ExploreRefreshRunRequest,
  ExploreRefreshRunResponse,
  ExploreRefreshScope,
} from "@/lib/explore-refresh/types";
import type { StandardSurfaceResponse } from "@/lib/niche-finder/types";
import { Icon, I } from "@/lib/icons";
import CityDrawer from "./CityDrawer";
import ExploreFilters, { type ExploreFilterState } from "./ExploreFilters";
import ExploreTable, {
  type ExploreCityDetailState,
  type ExploreSortKey,
  type SortDirection,
} from "./ExploreTable";
import FreshScanConfirmation, {
  type FreshScanResult,
} from "./FreshScanConfirmation";
import RefreshControlPanel from "./RefreshControlPanel";
import RefreshRunStatus from "./RefreshRunStatus";

interface ExplorePageClientProps {
  data: ExploreData;
  dataQueryKey?: string;
  onRunFreshScan?: (
    city: ExploreCitySummary,
    targets: ExploreScanTarget[],
  ) => FreshScanResult[] | void | Promise<FreshScanResult[] | void>;
}

const DEFAULT_FILTERS: ExploreFilterState = {
  populationMin: "",
  populationMax: "",
  incomeMin: "",
  incomeMax: "",
  selectedStates: [],
  service: "",
  growingOnly: false,
};

const REFRESH_BATCH_CAP = 50;

function parseNumber(value: string): number | null {
  const cleaned = value.replace(/,/g, "").trim();
  if (!cleaned) return null;
  const parsed = Number(cleaned);
  return Number.isFinite(parsed) ? parsed : null;
}

function cityNameForScoring(city: ExploreCitySummary): string {
  const cityName = city.cbsa_name.trim();
  const state = city.state.trim();
  if (!state) return cityName;

  const stateSuffix = `, ${state}`;
  if (cityName.toLocaleLowerCase().endsWith(stateSuffix.toLocaleLowerCase())) {
    return cityName.slice(0, -stateSuffix.length).trim();
  }

  return cityName;
}

type SearchParamsLike = Pick<URLSearchParams, "get" | "getAll" | "toString">;

const FILTER_QUERY_KEYS = [
  "service",
  "state",
  "population_min",
  "population_max",
  "income_min",
  "income_max",
  "growing_only",
  "cursor",
];

function enabledParam(value: string | null): boolean {
  return value === "1" || value === "true";
}

function canonicalQueryString(query: string): string {
  const params = new URLSearchParams(query);
  params.sort();
  return params.toString();
}

function normalizedServiceLabel(value: string): string {
  return value.trim().toLocaleLowerCase().replace(/[_-]+/g, " ");
}

function catalogServiceLabel(value: string): string {
  return normalizedServiceLabel(value)
    .split(" ")
    .map((word) => {
      if (word === "hvac") return "HVAC";
      return word.charAt(0).toLocaleUpperCase() + word.slice(1);
    })
    .join(" ");
}

function uniqueServiceCatalog(services: string[]): string[] {
  const byKey = new Map<string, string>();
  services.forEach((service) => {
    const key = normalizedServiceLabel(service);
    if (!byKey.has(key)) byKey.set(key, catalogServiceLabel(service));
  });
  return [...byKey.values()].sort((a, b) => a.localeCompare(b));
}

type CityDetailCacheEntry =
  | { status: "loading" }
  | { status: "ready"; city: ExploreCitySummary }
  | { status: "error"; message: string };

function filtersFromSearchParams(searchParams: SearchParamsLike): ExploreFilterState {
  return {
    populationMin: searchParams.get("population_min") ?? "",
    populationMax: searchParams.get("population_max") ?? "",
    incomeMin: searchParams.get("income_min") ?? "",
    incomeMax: searchParams.get("income_max") ?? "",
    selectedStates: searchParams.getAll("state"),
    service: searchParams.get("service") ?? "",
    growingOnly: enabledParam(searchParams.get("growing_only")),
  };
}

function sortKeyFromSearchParams(searchParams: SearchParamsLike): ExploreSortKey {
  const raw = searchParams.get("sort");
  if (raw === "presentation_score") return "best_opportunity";
  if (
    raw === "city" ||
    raw === "population" ||
    raw === "income" ||
    raw === "business_density" ||
    raw === "growth" ||
    raw === "cached_services" ||
    raw === "best_opportunity"
  ) {
    return raw;
  }
  return "best_opportunity";
}

function sortDirectionFromSearchParams(searchParams: SearchParamsLike): SortDirection {
  return searchParams.get("direction") === "asc" ? "asc" : "desc";
}

function writeNumberParam(params: URLSearchParams, key: string, raw: string) {
  const value = parseNumber(raw);
  if (value == null) return;
  params.set(key, String(value));
}

function writeExploreFilters(params: URLSearchParams, filters: ExploreFilterState) {
  for (const key of FILTER_QUERY_KEYS) params.delete(key);
  if (filters.service) params.set("service", filters.service);
  for (const state of filters.selectedStates) params.append("state", state);
  writeNumberParam(params, "population_min", filters.populationMin);
  writeNumberParam(params, "population_max", filters.populationMax);
  writeNumberParam(params, "income_min", filters.incomeMin);
  writeNumberParam(params, "income_max", filters.incomeMax);
  if (filters.growingOnly) params.set("growing_only", "1");
}

function serializeFilters(filters: ExploreFilterState): Record<string, unknown> {
  return {
    population_min: parseNumber(filters.populationMin),
    population_max: parseNumber(filters.populationMax),
    income_min: parseNumber(filters.incomeMin),
    income_max: parseNumber(filters.incomeMax),
    selected_states: filters.selectedStates,
    service: filters.service,
    growing_only: filters.growingOnly,
  };
}

function uniqueTargetIds(items: Array<{ refresh_target_id?: string | null }>): string[] {
  return [
    ...new Set(
      items
        .map((item) => item.refresh_target_id)
        .filter((targetId): targetId is string => Boolean(targetId)),
    ),
  ];
}

async function readRefreshError(response: Response): Promise<string> {
  const fallback = `Refresh run unavailable (HTTP ${response.status}). Try again shortly.`;
  try {
    const json = (await response.clone().json()) as { message?: string; error?: string };
    return json.message ?? json.error ?? fallback;
  } catch {
    try {
      const text = await response.text();
      return text.trim() || fallback;
    } catch {
      return fallback;
    }
  }
}

async function runFreshScanForService(
  city: ExploreCitySummary,
  target: ExploreScanTarget,
): Promise<FreshScanResult> {
  const body: Record<string, string> = {
    city: cityNameForScoring(city),
    service: target.service,
    metadata_source: "fallback_cbsa",
  };
  if (city.state) {
    body.state = city.state;
  }

  try {
    const response = await fetch("/api/agent/scoring", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    let json: StandardSurfaceResponse | null = null;
    try {
      json = (await response.json()) as StandardSurfaceResponse;
    } catch {
      json = null;
    }

    if (!response.ok || !json || json.status !== "success") {
      return {
        service: target.service_label,
        status: "error",
        message:
          json?.message ??
          `Scoring unavailable (HTTP ${response.status}). Try again shortly.`,
      };
    }

    return {
      service: target.service_label,
      status: "success",
      report_id: json.report_id,
    };
  } catch (error) {
    return {
      service: target.service_label,
      status: "error",
      message: error instanceof Error ? error.message : "Failed to run fresh scan.",
    };
  }
}

export default function ExplorePageClient({
  data,
  dataQueryKey,
  onRunFreshScan,
}: ExplorePageClientProps) {
  const router = useRouter();
  const pathname = usePathname() || "/explore";
  const searchParams = useSearchParams();
  const queryRef = useRef(searchParams.toString());
  const loadedDataQueryKey = dataQueryKey ?? canonicalQueryString(searchParams.toString());
  const [currentQueryKey, setCurrentQueryKey] = useState(loadedDataQueryKey);
  const freshScanButtonRef = useRef<HTMLButtonElement>(null);
  const freshScanRequestIdRef = useRef(0);
  const freshScanInFlightRef = useRef(false);
  const refreshInFlightRef = useRef(false);
  const urlFilters = useMemo(
    () => filtersFromSearchParams(searchParams),
    [searchParams],
  );
  const urlSortKey = useMemo(
    () => sortKeyFromSearchParams(searchParams),
    [searchParams],
  );
  const urlSortDirection = useMemo(
    () => sortDirectionFromSearchParams(searchParams),
    [searchParams],
  );
  const growthAvailable =
    data.growth_available ?? data.cities.some((city) => city.growth_available);
  const hasUnavailableGrowthFilter =
    !growthAvailable && enabledParam(searchParams.get("growing_only"));
  const initialFilters = useMemo(
    () =>
      growthAvailable
        ? urlFilters
        : {
            ...urlFilters,
            growingOnly: false,
          },
    [growthAvailable, urlFilters],
  );
  const [filters, setFilters] = useState<ExploreFilterState>(initialFilters);
  const [sortKey, setSortKey] = useState<ExploreSortKey>(urlSortKey);
  const [sortDirection, setSortDirection] = useState<SortDirection>(urlSortDirection);
  const [filterResetVersion, setFilterResetVersion] = useState(0);
  const [openCity, setOpenCity] = useState<ExploreCitySummary | null>(null);
  const [selectedTargets, setSelectedTargets] = useState<ExploreScanTarget[]>([]);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [freshScanResults, setFreshScanResults] = useState<FreshScanResult[]>([]);
  const [isFreshScanRunning, setIsFreshScanRunning] = useState(false);
  const [refreshRun, setRefreshRun] = useState<ExploreRefreshRunResponse | null>(null);
  const [refreshError, setRefreshError] = useState<string | null>(null);
  const [isRefreshSubmitting, setIsRefreshSubmitting] = useState(false);
  const [cityDetailCache, setCityDetailCache] = useState<
    Record<string, CityDetailCacheEntry>
  >({});

  async function ensureCityDetail(city: ExploreCitySummary) {
    if (city.cached_services_count <= city.cached_scores.length) return;
    const current = cityDetailCache[city.cbsa_code];
    if (current?.status === "loading" || current?.status === "ready") return;

    setCityDetailCache((cache) => ({
      ...cache,
      [city.cbsa_code]: { status: "loading" },
    }));

    try {
      const response = await fetch(
        `/api/explore/cities/${encodeURIComponent(city.cbsa_code)}`,
        { cache: "no-store" },
      );
      if (!response.ok) {
        throw new Error(`Service detail unavailable (HTTP ${response.status}).`);
      }
      const detail = normalizeExploreCity(await response.json());
      setCityDetailCache((cache) => ({
        ...cache,
        [city.cbsa_code]: { status: "ready", city: detail },
      }));
    } catch (error) {
      setCityDetailCache((cache) => ({
        ...cache,
        [city.cbsa_code]: {
          status: "error",
          message:
            error instanceof Error
              ? error.message
              : "Service detail unavailable.",
        },
      }));
    }
  }

  const visibleCities = useMemo(
    () =>
      data.cities.map((city) => {
        const entry = cityDetailCache[city.cbsa_code];
        return entry?.status === "ready" ? entry.city : city;
      }),
    [cityDetailCache, data.cities],
  );
  const openCityWithDetail = useMemo(() => {
    if (!openCity) return null;
    const entry = cityDetailCache[openCity.cbsa_code];
    return entry?.status === "ready" ? entry.city : openCity;
  }, [cityDetailCache, openCity]);

  const services = useMemo(
    () =>
      [
        ...new Set(
          visibleCities.flatMap((city) => city.cached_scores.map((score) => score.service)),
        ),
      ].sort((a, b) => a.localeCompare(b)),
    [visibleCities],
  );
  const catalogServices = useMemo(
    () => uniqueServiceCatalog(services),
    [services],
  );

  const detailStates = useMemo(() => {
    const statesByCity: Record<string, ExploreCityDetailState> = {};
    for (const [cbsaCode, entry] of Object.entries(cityDetailCache)) {
      if (entry.status === "loading") {
        statesByCity[cbsaCode] = { status: "loading" };
      } else if (entry.status === "error") {
        statesByCity[cbsaCode] = {
          status: "error",
          message: entry.message,
        };
      }
    }
    return statesByCity;
  }, [cityDetailCache]);
  const visibleScores = useMemo(
    () => visibleCities.flatMap((city) => city.cached_scores),
    [visibleCities],
  );
  const selectedRefreshableScores = useMemo(
    () =>
      selectedTargets.filter(
        (target) => target.source === "cached" && target.refresh_target_id,
      ),
    [selectedTargets],
  );
  const staleRefreshableScores = useMemo(
    () => visibleScores.filter((score) => score.is_stale && score.refresh_target_id),
    [visibleScores],
  );
  const visibleRefreshableScores = useMemo(
    () => visibleScores.filter((score) => score.refresh_target_id),
    [visibleScores],
  );
  const refreshDataCurrent =
    currentQueryKey === loadedDataQueryKey && !hasUnavailableGrowthFilter;

  useEffect(() => {
    if (!hasUnavailableGrowthFilter) return;

    const params = new URLSearchParams(searchParams.toString());
    params.delete("growing_only");
    params.delete("cursor");
    const query = params.toString();
    queryRef.current = query;
    router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
  }, [hasUnavailableGrowthFilter, pathname, router, searchParams]);

  function currentParams() {
    return new URLSearchParams(queryRef.current);
  }

  function replaceWithParams(params: URLSearchParams) {
    const query = params.toString();
    queryRef.current = query;
    setCurrentQueryKey(canonicalQueryString(query));
    router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
  }

  function applyFilters(nextFilters: ExploreFilterState) {
    const nextParams = currentParams();
    const normalizedFilters = growthAvailable
      ? nextFilters
      : { ...nextFilters, growingOnly: false };
    writeExploreFilters(nextParams, normalizedFilters);
    setFilters(normalizedFilters);
    replaceWithParams(nextParams);
  }

  function resetFilters() {
    const nextParams = currentParams();
    for (const key of FILTER_QUERY_KEYS) nextParams.delete(key);
    setFilters(DEFAULT_FILTERS);
    setFilterResetVersion((version) => version + 1);
    replaceWithParams(nextParams);
  }

  function changeSort(nextKey: ExploreSortKey) {
    const nextParams = currentParams();
    nextParams.delete("cursor");
    const nextDirection =
      nextKey === sortKey
        ? sortDirection === "asc"
          ? "desc"
          : "asc"
        : nextKey === "city"
          ? "asc"
          : "desc";
    setSortKey(nextKey);
    setSortDirection(nextDirection);
    nextParams.set("sort", nextKey);
    nextParams.set("direction", nextDirection);
    replaceWithParams(nextParams);
  }

  function invalidateFreshScanRequest() {
    freshScanRequestIdRef.current += 1;
    freshScanInFlightRef.current = false;
    setIsFreshScanRunning(false);
    setFreshScanResults([]);
  }

  function openDrawer(city: ExploreCitySummary) {
    invalidateFreshScanRequest();
    setOpenCity(city);
    setSelectedTargets([]);
    setConfirmOpen(false);
    void ensureCityDetail(city);
  }

  function closeDrawer() {
    invalidateFreshScanRequest();
    setOpenCity(null);
    setSelectedTargets([]);
    setConfirmOpen(false);
  }

  function scanTargetKey(target: ExploreScanTarget): string {
    return target.report_id ?? `${target.source}:${normalizedServiceLabel(target.service)}`;
  }

  function toggleTarget(target: ExploreScanTarget) {
    setFreshScanResults([]);
    setSelectedTargets((current) => {
      const key = scanTargetKey(target);
      if (current.some((item) => scanTargetKey(item) === key)) {
        return current.filter((item) => scanTargetKey(item) !== key);
      }
      return [...current, target];
    });
  }

  async function startRefreshRun(scope: ExploreRefreshScope) {
    if (refreshInFlightRef.current || !refreshDataCurrent) return;

    const scores =
      scope === "selected"
        ? selectedRefreshableScores
        : scope === "stale"
          ? staleRefreshableScores
          : visibleRefreshableScores;
    const targetIds = uniqueTargetIds(scores);
    if (targetIds.length === 0) return;
    refreshInFlightRef.current = true;

    const body: ExploreRefreshRunRequest = {
      scope,
      target_ids: targetIds,
      filters: serializeFilters(filters),
      flags: {
        force: false,
        dry_run: false,
        strategy_profile: "balanced",
        max_items: scope === "selected" ? scores.length : REFRESH_BATCH_CAP,
        concurrency: 2,
      },
    };

    setIsRefreshSubmitting(true);
    setRefreshRun(null);
    setRefreshError(null);

    try {
      const response = await fetch("/api/explore/refresh/runs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        throw new Error(await readRefreshError(response));
      }

      const json = (await response.json()) as ExploreRefreshRunResponse;
      setRefreshRun(json);
    } catch (error) {
      setRefreshError(
        error instanceof Error ? error.message : "Failed to start refresh run.",
      );
    } finally {
      refreshInFlightRef.current = false;
      setIsRefreshSubmitting(false);
    }
  }

  function openFreshScanConfirmation() {
    setFreshScanResults([]);
    setConfirmOpen(true);
  }

  function closeFreshScanConfirmation() {
    invalidateFreshScanRequest();
    setConfirmOpen(false);
  }

  async function confirmFreshScan(targetsToScan: ExploreScanTarget[]) {
    if (!openCityWithDetail || freshScanInFlightRef.current || targetsToScan.length === 0) {
      return;
    }

    const requestId = freshScanRequestIdRef.current + 1;
    freshScanRequestIdRef.current = requestId;
    freshScanInFlightRef.current = true;
    setIsFreshScanRunning(true);
    setFreshScanResults([]);
    const cityToScan = openCityWithDetail;
    const isCurrentRequest = () =>
      freshScanRequestIdRef.current === requestId && freshScanInFlightRef.current;

    try {
      const results = onRunFreshScan
        ? await onRunFreshScan(cityToScan, targetsToScan)
        : await Promise.all(
            targetsToScan.map((target) => runFreshScanForService(cityToScan, target)),
          );
      if (isCurrentRequest()) {
        setFreshScanResults(results ?? []);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to run fresh scan.";
      if (isCurrentRequest()) {
        setFreshScanResults(
          targetsToScan.map((target) => ({
            service: target.service_label,
            status: "error",
            message,
          })),
        );
      }
    } finally {
      if (isCurrentRequest()) {
        freshScanInFlightRef.current = false;
        setIsFreshScanRunning(false);
      }
    }
  }

  return (
    <>
      <div
        style={{
          display: "grid",
          gap: 18,
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-end",
            gap: 18,
            flexWrap: "wrap",
          }}
        >
          <div>
            <div className="kicker">Explore</div>
            <h1 className="page-h1" style={{ margin: "4px 0 0" }}>
              Cities & service data
            </h1>
            <p className="page-sub">
              Browse the data layer for free. Narrow down by demographics, then spend scans on the ones you want fresh numbers for.
            </p>
            <div
              style={{
                marginTop: 10,
                color: "var(--ink-2)",
                fontSize: 13,
              }}
            >
              Know what you want?{" "}
              <Link
                href="/strategies"
                className="settings-link"
                style={{ display: "inline-flex", alignItems: "center", gap: 5 }}
              >
                Jump to a strategy <Icon d={I.arrow} />
              </Link>
            </div>
          </div>
          <div
            style={{
              display: "flex",
              gap: 8,
              flexWrap: "wrap",
              justifyContent: "flex-end",
            }}
            aria-label="Explore summary"
          >
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 7,
                minHeight: 34,
                padding: "6px 11px",
                borderRadius: 999,
                background: "var(--accent-soft)",
                color: "var(--accent-ink)",
                fontFamily: "var(--sans)",
                fontSize: 12,
                fontWeight: 650,
              }}
            >
              <Icon d={I.mapPin} />
              {visibleCities.length} cities
            </span>
            <span
              className={ARCHETYPES[3]?.glyph ?? "arch-pack-vuln"}
              style={{
                display: "inline-flex",
                alignItems: "center",
                minHeight: 34,
                padding: "6px 11px",
                borderRadius: 999,
                fontFamily: "var(--sans)",
                fontSize: 12,
                fontWeight: 650,
              }}
            >
              {services.length} services
            </span>
          </div>
        </div>

        <ExploreFilters
          key={`${filterResetVersion}:${filters.populationMin}|${filters.populationMax}|${filters.incomeMin}|${filters.incomeMax}`}
          filters={filters}
          services={services}
          growthAvailable={growthAvailable}
          onChange={applyFilters}
          onReset={resetFilters}
        />

        <RefreshControlPanel
          batchCap={REFRESH_BATCH_CAP}
          selectedCount={selectedRefreshableScores.length}
          staleCount={staleRefreshableScores.length}
          visibleCount={visibleRefreshableScores.length}
          isSubmitting={isRefreshSubmitting}
          disabled={!refreshDataCurrent}
          onRefreshSelected={() => void startRefreshRun("selected")}
          onRefreshStale={() => void startRefreshRun("stale")}
          onRefreshVisible={() => void startRefreshRun("visible")}
        />

        <RefreshRunStatus run={refreshRun} error={refreshError} />

        <ExploreTable
          cities={visibleCities}
          sortKey={sortKey}
          sortDirection={sortDirection}
          activeService={filters.service}
          detailStates={detailStates}
          onCityExpand={(city) => void ensureCityDetail(city)}
          onSortChange={changeSort}
          onCityOpen={openDrawer}
          onReset={resetFilters}
        />
      </div>

      <CityDrawer
        city={openCityWithDetail}
        catalogServices={catalogServices}
        selectedTargets={selectedTargets}
        isTopLayer={!confirmOpen}
        freshScanButtonRef={freshScanButtonRef}
        isRefreshSubmitting={isRefreshSubmitting}
        refreshDisabled={!refreshDataCurrent}
        selectedRefreshableCount={selectedRefreshableScores.length}
        onClose={closeDrawer}
        onToggleTarget={toggleTarget}
        onOpenConfirmation={openFreshScanConfirmation}
        onRefreshSelected={() => void startRefreshRun("selected")}
      />

      <FreshScanConfirmation
        cityName={openCityWithDetail?.cbsa_name ?? ""}
        targets={selectedTargets}
        results={freshScanResults}
        isOpen={confirmOpen}
        isSubmitting={isFreshScanRunning}
        restoreFocusRef={freshScanButtonRef}
        onCancel={closeFreshScanConfirmation}
        onConfirm={confirmFreshScan}
      />
    </>
  );
}
