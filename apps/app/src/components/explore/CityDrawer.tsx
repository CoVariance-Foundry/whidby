"use client";

import { type RefObject, useRef } from "react";
import { Icon, I } from "@/lib/icons";
import type { ExploreCachedScore, ExploreCitySummary } from "@/lib/explore/types";
import {
  formatCurrency,
  formatDate,
  formatDecimal,
  formatInteger,
  formatPercent,
  humanize,
} from "./format";
import ServiceScoreRow from "./ServiceScoreRow";
import { useModalAccessibility } from "./useModalAccessibility";

interface CityDrawerProps {
  city: ExploreCitySummary | null;
  selectedServices: ExploreCachedScore[];
  isTopLayer?: boolean;
  freshScanButtonRef?: RefObject<HTMLButtonElement | null>;
  isRefreshSubmitting?: boolean;
  refreshDisabled?: boolean;
  selectedRefreshableCount?: number;
  onClose: () => void;
  onToggleService: (score: ExploreCachedScore) => void;
  onOpenConfirmation: () => void;
  onRefreshSelected: () => void;
}

function Stat({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div
      style={{
        minWidth: 0,
        padding: "10px 0",
        borderBottom: "1px solid var(--rule)",
      }}
    >
      <div className="field-label" style={{ marginBottom: 3 }}>
        {label}
      </div>
      <div
        style={{
          fontFamily: "var(--sans)",
          fontSize: 14,
          fontWeight: 650,
          color: "var(--ink)",
          overflowWrap: "anywhere",
        }}
      >
        {value}
      </div>
    </div>
  );
}

function verifiedStats(city: ExploreCitySummary): Array<{ label: string; value: string }> {
  const stats = [
    { label: "Population", value: formatInteger(city.population), show: city.population != null },
    {
      label: "Median income",
      value: formatCurrency(city.median_household_income_usd),
      show: city.median_household_income_usd != null,
    },
    {
      label: "Owner occupancy",
      value: formatPercent(city.owner_occupancy_rate),
      show: city.owner_occupancy_rate != null,
    },
    {
      label: "Median age",
      value: formatDecimal(city.median_age_years),
      show: city.median_age_years != null,
    },
    {
      label: "Population class",
      value: city.population_class ? humanize(city.population_class) : "-",
      show: city.population_class != null,
    },
    {
      label: "Business density",
      value: formatDecimal(city.business_density_per_1k),
      show: city.business_density_per_1k != null,
    },
    {
      label: "Establishment growth",
      value: formatPercent(city.establishment_growth_yoy),
      show: city.establishment_growth_yoy != null,
    },
  ];

  return stats.filter((stat) => stat.show).map(({ label, value }) => ({ label, value }));
}

function freshnessDetails(score: ExploreCachedScore): string[] {
  const details = [];
  if (score.last_refreshed_at) {
    details.push(`Last refreshed ${formatDate(score.last_refreshed_at)}`);
  }
  if (score.next_refresh_at) {
    details.push(`Next refresh ${formatDate(score.next_refresh_at)}`);
  }
  return details;
}

export default function CityDrawer({
  city,
  selectedServices,
  isTopLayer = true,
  freshScanButtonRef,
  isRefreshSubmitting = false,
  refreshDisabled = false,
  selectedRefreshableCount = 0,
  onClose,
  onToggleService,
  onOpenConfirmation,
  onRefreshSelected,
}: CityDrawerProps) {
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  useModalAccessibility({
    isOpen: city !== null,
    isTopLayer,
    onClose,
    focusRef: closeButtonRef,
  });

  if (!city) return null;

  const selectedIds = new Set(selectedServices.map((service) => service.report_id));
  const stats = verifiedStats(city);

  return (
    <div
      role="presentation"
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 50,
        background: "rgba(31, 27, 22, 0.18)",
        display: "flex",
        justifyContent: "flex-end",
      }}
      onClick={onClose}
    >
      <aside
        role="dialog"
        aria-modal={isTopLayer}
        aria-labelledby="city-drawer-title"
        onClick={(event) => event.stopPropagation()}
        style={{
          width: "min(560px, 100%)",
          height: "100%",
          background: "var(--card)",
          borderLeft: "1px solid var(--rule-strong)",
          boxShadow: "-18px 0 60px rgba(31, 27, 22, 0.13)",
          overflowY: "auto",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <header
          style={{
            padding: "20px 22px 16px",
            borderBottom: "1px solid var(--rule)",
            background: "var(--paper)",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "flex-start",
              justifyContent: "space-between",
              gap: 16,
            }}
          >
            <div style={{ minWidth: 0 }}>
              <div className="kicker">Metro explorer</div>
              <h2
                id="city-drawer-title"
                style={{
                  margin: "5px 0 0",
                  fontFamily: "var(--serif)",
                  fontSize: 25,
                  fontWeight: 600,
                  lineHeight: 1.1,
                  color: "var(--ink)",
                }}
              >
                {city.cbsa_name}
              </h2>
            </div>
            <button
              ref={closeButtonRef}
              type="button"
              className="icon-btn"
              aria-label="Close city drawer"
              onClick={onClose}
            >
              <Icon d={I.x} />
            </button>
          </div>
        </header>

        <div style={{ padding: "16px 22px 22px", display: "grid", gap: 18 }}>
          <section aria-label="City demographics">
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
                gap: "0 18px",
              }}
            >
              {stats.map((stat) => (
                <Stat key={stat.label} label={stat.label} value={stat.value} />
              ))}
            </div>
          </section>

          <section aria-labelledby="cached-services-title">
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 12,
                flexWrap: "wrap",
                marginBottom: 2,
              }}
            >
              <h3
                id="cached-services-title"
                style={{
                  margin: 0,
                  fontFamily: "var(--serif)",
                  fontSize: 18,
                  fontWeight: 600,
                  color: "var(--ink)",
                }}
              >
                Cached service scores
              </h3>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                <button
                  type="button"
                  className="btn-ghost"
                  onClick={onRefreshSelected}
                  disabled={
                    refreshDisabled ||
                    isRefreshSubmitting ||
                    selectedRefreshableCount === 0
                  }
                >
                  <Icon d={I.clock} />
                  Refresh selected
                </button>
                <button
                  ref={freshScanButtonRef}
                  type="button"
                  className="btn-primary"
                  aria-label={`Open fresh scan confirmation for ${selectedServices.length} selected services`}
                  onClick={onOpenConfirmation}
                  disabled={selectedServices.length === 0}
                >
                  <Icon d={I.sparkle} />
                  Fresh scan
                </button>
              </div>
            </div>

            {city.cached_scores.length === 0 ? (
              <p
                role="status"
                style={{
                  margin: "14px 0 0",
                  padding: 14,
                  border: "1px solid var(--rule)",
                  borderRadius: 8,
                  background: "var(--paper)",
                  color: "var(--ink-2)",
                  fontFamily: "var(--sans)",
                  fontSize: 13,
                }}
              >
                No cached service scores for this city.
              </p>
            ) : (
              <div role="list" aria-label="Cached service scores">
                {city.cached_scores.map((score) => {
                  const details = freshnessDetails(score);
                  return (
                    <div key={score.report_id}>
                      <ServiceScoreRow
                        score={score}
                        selected={selectedIds.has(score.report_id)}
                        onToggle={onToggleService}
                      />
                      {details.length > 0 && (
                        <div
                          style={{
                            marginTop: -5,
                            paddingBottom: 10,
                            display: "flex",
                            gap: 10,
                            flexWrap: "wrap",
                            fontFamily: "var(--sans)",
                            fontSize: 12,
                            color: "var(--ink-3)",
                          }}
                        >
                          {details.map((detail) => (
                            <span key={detail}>{detail}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </section>
        </div>
      </aside>
    </div>
  );
}
