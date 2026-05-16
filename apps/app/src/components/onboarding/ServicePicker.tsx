"use client";

import { useMemo, useState } from "react";

export interface OnboardingServiceChoice {
  id: string | null;
  label: string;
  is_custom: boolean;
}

const SERVICE_CATALOG = [
  { id: "plumbing", label: "Plumbing", note: "Emergency and repair demand" },
  { id: "hvac", label: "HVAC", note: "Seasonal replacement value" },
  { id: "roofing", label: "Roofing", note: "High-ticket local leads" },
  { id: "tree_service", label: "Tree service", note: "Fragmented local SERPs" },
  { id: "pest_control", label: "Pest control", note: "Recurring service intent" },
  { id: "water_damage", label: "Water damage", note: "Urgent restoration searches" },
] as const;

interface ServicePickerProps {
  value: OnboardingServiceChoice | null;
  onSelect: (service: OnboardingServiceChoice) => void;
  onBack: () => void;
}

export default function ServicePicker({ value, onSelect, onBack }: ServicePickerProps) {
  const [customService, setCustomService] = useState(
    value?.is_custom ? value.label : "",
  );

  const canUseCustom = customService.trim().length >= 2;
  const currentLabel = useMemo(() => value?.label ?? "", [value]);

  return (
    <section aria-labelledby="service-heading">
      <button type="button" className="btn-ghost" onClick={onBack}>
        Back
      </button>

      <div style={{ marginTop: 18 }}>
        <p className="field-label">Step 2 of 4</p>
        <h1 id="service-heading" className="page-h1" style={{ margin: 0 }}>
          Pick the service market.
        </h1>
        <p className="page-sub">
          Start with one rank-and-rent category. You can change the niche before
          the report starts.
        </p>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
          gap: 10,
          marginTop: 24,
        }}
      >
        {SERVICE_CATALOG.map((service) => {
          const active = currentLabel === service.label;
          return (
            <button
              key={service.id}
              type="button"
              aria-pressed={active}
              onClick={() =>
                onSelect({
                  id: service.id,
                  label: service.label,
                  is_custom: false,
                })
              }
              style={{
                textAlign: "left",
                minHeight: 106,
                padding: 14,
                borderRadius: 8,
                border: `1px solid ${active ? "var(--accent)" : "var(--rule)"}`,
                background: active ? "var(--accent-soft)" : "var(--card)",
                color: "var(--ink)",
              }}
            >
              <span
                style={{
                  display: "block",
                  fontFamily: "var(--serif)",
                  fontSize: 18,
                  fontWeight: 600,
                }}
              >
                {service.label}
              </span>
              <span
                style={{
                  display: "block",
                  marginTop: 8,
                  fontSize: 12,
                  lineHeight: 1.4,
                  color: "var(--ink-2)",
                }}
              >
                {service.note}
              </span>
            </button>
          );
        })}
      </div>

      <div
        style={{
          marginTop: 20,
          paddingTop: 20,
          borderTop: "1px solid var(--rule)",
        }}
      >
        <label htmlFor="custom-service" className="field-label">
          Or enter a custom service
        </label>
        <div style={{ display: "flex", gap: 10, alignItems: "stretch" }}>
          <div className="input-wrap" style={{ flex: 1 }}>
            <input
              id="custom-service"
              data-testid="custom-service-input"
              value={customService}
              onChange={(event) => setCustomService(event.target.value)}
              placeholder="e.g. locksmith, pool cleaning"
            />
          </div>
          <button
            type="button"
            className="btn-primary"
            disabled={!canUseCustom}
            onClick={() =>
              onSelect({
                id: null,
                label: customService.trim(),
                is_custom: true,
              })
            }
          >
            Continue
          </button>
        </div>
      </div>
    </section>
  );
}
