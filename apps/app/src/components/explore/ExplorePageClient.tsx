"use client";

import { useMemo, useRef, useState } from "react";
import { ARCHETYPES } from "@/lib/archetypes";
import type {
  ExploreCachedScore,
  ExploreCitySummary,
  ExploreData,
} from "@/lib/explore/types";
import type {
  ExploreRefreshRunRequest,
  ExploreRefreshRunResponse,
  ExploreRefreshScope,
} from "@/lib/explore-refresh/types";
import type { StandardSurfaceResponse } from "@/lib/niche-finder/types";
import { Icon, I } from "@/lib/icons";
import CityDrawer from "./CityDrawer";
import ExploreFilters, { type ExploreFilterState } from "./ExploreFilters";
import ExploreTable, { type ExploreSortKey, type SortDirection } from "./ExploreTable";
import FreshScanConfirmation, {
  type FreshScanResult,
} from "./FreshScanConfirmation";
import RefreshControlPanel from "./RefreshControlPanel";
import RefreshRunStatus from "./RefreshRunStatus";

interface ExplorePageClientProps {
  data: ExploreData;
  onRunFreshScan?: (
    city: ExploreCitySummary,
    services: ExploreCachedScore[],
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

const NUMERIC_SORTS: Record<ExploreSortKey, (city: ExploreCitySummary) => number | null> = {
  city: () => null,
  population: (city) => city.population,
  income: (city) => city.median_household_income_usd,
  business_density: (city) => city.business_density_per_1k,
  growth: (city) => city.establishment_growth_yoy,
  cached_services: (city) => city.cached_services_count,
  best_opportunity: (city) => city.best_opportunity_score,
};

function parseNumber(value: string): number | null {
  const cleaned = value.replace(/,/g, "").trim();
  if (!cleaned) return null;
  const parsed = Number(cleaned);
  return Number.isFinite(parsed) ? parsed : null;
}

function passesRange(value: number | null, min: number | null, max: number | null): boolean {
  if (min == null && max == null) return true;
  if (value == null) return false;
  if (min != null && value < min) return false;
  if (max != null && value > max) return false;
  return true;
}

function sortCities(
  cities: ExploreCitySummary[],
  sortKey: ExploreSortKey,
  direction: SortDirection,
): ExploreCitySummary[] {
  const multiplier = direction === "asc" ? 1 : -1;
  return [...cities].sort((a, b) => {
    if (sortKey === "city") {
      return a.cbsa_name.localeCompare(b.cbsa_name) * multiplier;
    }

    const getter = NUMERIC_SORTS[sortKey];
    const aValue = getter(a);
    const bValue = getter(b);
    if (aValue == null && bValue == null) {
      return a.cbsa_name.localeCompare(b.cbsa_name);
    }
    if (aValue == null) return 1;
    if (bValue == null) return -1;
    if (aValue === bValue) return a.cbsa_name.localeCompare(b.cbsa_name);
    return (aValue - bValue) * multiplier;
  });
}

function filterCities(
  cities: ExploreCitySummary[],
  filters: ExploreFilterState,
): ExploreCitySummary[] {
  const populationMin = parseNumber(filters.populationMin);
  const populationMax = parseNumber(filters.populationMax);
  const incomeMin = parseNumber(filters.incomeMin);
  const incomeMax = parseNumber(filters.incomeMax);

  return cities.filter((city) => {
    if (!passesRange(city.population, populationMin, populationMax)) return false;
    if (!passesRange(city.median_household_income_usd, incomeMin, incomeMax)) return false;
    if (filters.selectedStates.length > 0 && !filters.selectedStates.includes(city.state)) {
      return false;
    }
    if (
      filters.service &&
      !city.cached_scores.some((score) => score.service === filters.service)
    ) {
      return false;
    }
    if (
      filters.growingOnly &&
      (city.establishment_growth_yoy == null || city.establishment_growth_yoy < 3)
    ) {
      return false;
    }
    return true;
  });
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

function uniqueTargetIds(scores: ExploreCachedScore[]): string[] {
  return [
    ...new Set(
      scores
        .map((score) => score.refresh_target_id)
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
  service: ExploreCachedScore,
): Promise<FreshScanResult> {
  const body: Record<string, string> = {
    city: cityNameForScoring(city),
    service: service.service,
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
        service: service.service,
        status: "error",
        message:
          json?.message ??
          `Scoring unavailable (HTTP ${response.status}). Try again shortly.`,
      };
    }

    return {
      service: service.service,
      status: "success",
      report_id: json.report_id,
    };
  } catch (error) {
    return {
      service: service.service,
      status: "error",
      message: error instanceof Error ? error.message : "Failed to run fresh scan.",
    };
  }
}

export default function ExplorePageClient({
  data,
  onRunFreshScan,
}: ExplorePageClientProps) {
  const freshScanButtonRef = useRef<HTMLButtonElement>(null);
  const freshScanRequestIdRef = useRef(0);
  const freshScanInFlightRef = useRef(false);
  const refreshInFlightRef = useRef(false);
  const [filters, setFilters] = useState<ExploreFilterState>(DEFAULT_FILTERS);
  const [sortKey, setSortKey] = useState<ExploreSortKey>("best_opportunity");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");
  const [openCity, setOpenCity] = useState<ExploreCitySummary | null>(null);
  const [selectedScores, setSelectedScores] = useState<ExploreCachedScore[]>([]);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [freshScanResults, setFreshScanResults] = useState<FreshScanResult[]>([]);
  const [isFreshScanRunning, setIsFreshScanRunning] = useState(false);
  const [refreshRun, setRefreshRun] = useState<ExploreRefreshRunResponse | null>(null);
  const [refreshError, setRefreshError] = useState<string | null>(null);
  const [isRefreshSubmitting, setIsRefreshSubmitting] = useState(false);

  const states = useMemo(
    () => [...new Set(data.cities.map((city) => city.state).filter(Boolean))].sort(),
    [data.cities],
  );
  const services = useMemo(
    () =>
      [
        ...new Set(
          data.cities.flatMap((city) => city.cached_scores.map((score) => score.service)),
        ),
      ].sort((a, b) => a.localeCompare(b)),
    [data.cities],
  );

  const visibleCities = useMemo(
    () => sortCities(filterCities(data.cities, filters), sortKey, sortDirection),
    [data.cities, filters, sortDirection, sortKey],
  );
  const visibleScores = useMemo(
    () => visibleCities.flatMap((city) => city.cached_scores),
    [visibleCities],
  );
  const selectedRefreshableScores = useMemo(
    () => selectedScores.filter((score) => score.refresh_target_id),
    [selectedScores],
  );
  const staleRefreshableScores = useMemo(
    () => visibleScores.filter((score) => score.is_stale && score.refresh_target_id),
    [visibleScores],
  );
  const visibleRefreshableScores = useMemo(
    () => visibleScores.filter((score) => score.refresh_target_id),
    [visibleScores],
  );

  function resetFilters() {
    setFilters(DEFAULT_FILTERS);
  }

  function changeSort(nextKey: ExploreSortKey) {
    if (nextKey === sortKey) {
      setSortDirection((current) => (current === "asc" ? "desc" : "asc"));
      return;
    }
    setSortKey(nextKey);
    setSortDirection(nextKey === "city" ? "asc" : "desc");
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
    setSelectedScores([]);
    setConfirmOpen(false);
  }

  function closeDrawer() {
    invalidateFreshScanRequest();
    setOpenCity(null);
    setSelectedScores([]);
    setConfirmOpen(false);
  }

  function toggleService(score: ExploreCachedScore) {
    setFreshScanResults([]);
    setSelectedScores((current) => {
      if (current.some((item) => item.report_id === score.report_id)) {
        return current.filter((item) => item.report_id !== score.report_id);
      }
      return [...current, score];
    });
  }

  async function startRefreshRun(scope: ExploreRefreshScope) {
    if (refreshInFlightRef.current) return;

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

  async function confirmFreshScan(servicesToScan: ExploreCachedScore[]) {
    if (!openCity || freshScanInFlightRef.current || servicesToScan.length === 0) {
      return;
    }

    const requestId = freshScanRequestIdRef.current + 1;
    freshScanRequestIdRef.current = requestId;
    freshScanInFlightRef.current = true;
    setIsFreshScanRunning(true);
    setFreshScanResults([]);
    const cityToScan = openCity;
    const isCurrentRequest = () =>
      freshScanRequestIdRef.current === requestId && freshScanInFlightRef.current;

    try {
      const results = onRunFreshScan
        ? await onRunFreshScan(cityToScan, servicesToScan)
        : await Promise.all(
            servicesToScan.map((service) => runFreshScanForService(cityToScan, service)),
          );
      if (isCurrentRequest()) {
        setFreshScanResults(results ?? []);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to run fresh scan.";
      if (isCurrentRequest()) {
        setFreshScanResults(
          servicesToScan.map((service) => ({
            service: service.service,
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
            <div className="kicker">Consumer explore</div>
            <h1 className="page-h1" style={{ margin: "4px 0 0" }}>
              Explore cities
            </h1>
            <p className="page-sub">
              Compare cached market signals and open city-level service scores.
            </p>
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
          filters={filters}
          states={states}
          services={services}
          onChange={setFilters}
          onReset={resetFilters}
        />

        <RefreshControlPanel
          batchCap={REFRESH_BATCH_CAP}
          selectedCount={selectedRefreshableScores.length}
          staleCount={staleRefreshableScores.length}
          visibleCount={visibleRefreshableScores.length}
          isSubmitting={isRefreshSubmitting}
          onRefreshSelected={() => void startRefreshRun("selected")}
          onRefreshStale={() => void startRefreshRun("stale")}
          onRefreshVisible={() => void startRefreshRun("visible")}
        />

        <RefreshRunStatus run={refreshRun} error={refreshError} />

        <ExploreTable
          cities={visibleCities}
          sortKey={sortKey}
          sortDirection={sortDirection}
          onSortChange={changeSort}
          onCityOpen={openDrawer}
          onReset={resetFilters}
        />
      </div>

      <CityDrawer
        city={openCity}
        selectedServices={selectedScores}
        isTopLayer={!confirmOpen}
        freshScanButtonRef={freshScanButtonRef}
        isRefreshSubmitting={isRefreshSubmitting}
        selectedRefreshableCount={selectedRefreshableScores.length}
        onClose={closeDrawer}
        onToggleService={toggleService}
        onOpenConfirmation={openFreshScanConfirmation}
        onRefreshSelected={() => void startRefreshRun("selected")}
      />

      <FreshScanConfirmation
        cityName={openCity?.cbsa_name ?? ""}
        services={selectedScores}
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
