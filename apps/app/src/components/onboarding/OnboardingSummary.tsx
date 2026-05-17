"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { OnboardingStrategyRouting } from "@/lib/onboarding/types";
import type { OnboardingServiceChoice } from "./ServicePicker";
import type { OnboardingTargetChoice } from "./TargetPicker";

interface OnboardingSummaryProps {
  service: OnboardingServiceChoice;
  target: OnboardingTargetChoice;
  routing: OnboardingStrategyRouting | null;
  ensureProfile: () => Promise<OnboardingStrategyRouting>;
  onBack: () => void;
}

type ApiJson = {
  status?: string;
  message?: string;
  code?: string;
  redirect_url?: string;
  target?: { id?: string };
};

async function readJson(res: Response): Promise<ApiJson> {
  try {
    return (await res.json()) as ApiJson;
  } catch {
    return {};
  }
}

export default function OnboardingSummary({
  service,
  target,
  routing,
  ensureProfile,
  onBack,
}: OnboardingSummaryProps) {
  const router = useRouter();
  const [status, setStatus] = useState<"idle" | "saving" | "message" | "error">("idle");
  const [message, setMessage] = useState<string | null>(null);

  const strategy = routing?.starter ?? "easy_win";
  const isBroad = target.geo_scope !== "city";

  const handleStart = async () => {
    setStatus("saving");
    setMessage(null);

    try {
      const activeRouting = routing ?? (await ensureProfile());
      const strategyId = activeRouting.starter;

      const targetRes = await fetch("/api/onboarding/target", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          strategy_id: strategyId,
          niche_keyword: service.label,
          service_category_id: service.id,
          geo_scope: target.geo_scope,
          city: target.city ?? null,
          state: target.state ?? null,
          cbsa_code: target.cbsa_code ?? null,
          place_id: target.place_id ?? null,
          dataforseo_location_code: target.dataforseo_location_code ?? null,
          resolved_label: target.resolved_label,
          metadata_source: target.metadata_source,
        }),
      });
      const targetJson = await readJson(targetRes);

      if (!targetRes.ok || targetJson.status !== "success") {
        throw new Error(targetJson.message ?? "Target could not be saved.");
      }

      const startRes = await fetch("/api/onboarding/start-report", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target_id: targetJson.target?.id,
          strategy_id: strategyId,
        }),
      });
      const startJson = await readJson(startRes);

      if (startJson.redirect_url) {
        router.push(startJson.redirect_url);
        return;
      }

      if (startJson.code === "fresh_reports_not_included" || startJson.status === "tier_limit") {
        setStatus("message");
        setMessage(
          startJson.message ??
            "Fresh reports are not included on your current plan. Browse cached opportunities instead.",
        );
        return;
      }

      if (!startRes.ok) {
        throw new Error(startJson.message ?? "Report could not be started.");
      }

      if (startJson.status === "cached_route_selected") {
        router.push("/explore");
        return;
      }

      setStatus("error");
      setMessage(startJson.message ?? "Report response was incomplete.");
    } catch (error) {
      setStatus("error");
      setMessage(error instanceof Error ? error.message : "Onboarding could not continue.");
    }
  };

  return (
    <section aria-labelledby="summary-heading">
      <button type="button" className="btn-ghost" onClick={onBack}>
        Back
      </button>

      <div style={{ marginTop: 18 }}>
        <p className="field-label">Step 4 of 4</p>
        <h1 id="summary-heading" className="page-h1" style={{ margin: 0 }}>
          Confirm the first report.
        </h1>
        <p className="page-sub">
          We will save this target, then route it through your current plan
          entitlements.
        </p>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
          gap: 12,
          marginTop: 24,
          padding: 16,
          border: "1px solid var(--rule)",
          borderRadius: 8,
          background: "var(--card)",
        }}
      >
        {[
          ["Service", service.label],
          ["Market", target.resolved_label],
          ["Strategy", strategy.replaceAll("_", " ")],
          ["Path", isBroad ? "Cached Explore" : "Fresh city report"],
        ].map(([label, value]) => (
          <div key={label}>
            <div className="field-label" style={{ marginBottom: 4 }}>
              {label}
            </div>
            <div style={{ fontSize: 14, fontWeight: 600, color: "var(--ink)" }}>
              {value}
            </div>
          </div>
        ))}
      </div>

      {message && (
        <div
          role={status === "error" ? "alert" : "status"}
          style={{
            marginTop: 16,
            padding: "11px 12px",
            borderRadius: 8,
            border: `1px solid ${status === "error" ? "var(--danger)" : "var(--warn)"}`,
            background: status === "error" ? "var(--danger-soft)" : "var(--warn-soft)",
            color: status === "error" ? "var(--danger)" : "var(--warn)",
            fontSize: 13,
            lineHeight: 1.45,
          }}
        >
          {message}
        </div>
      )}

      <button
        type="button"
        className="btn-primary"
        disabled={status === "saving"}
        onClick={handleStart}
        style={{ marginTop: 22 }}
      >
        {status === "saving"
          ? "Starting..."
          : isBroad
            ? "Continue to Explore"
            : "Start report"}
      </button>
    </section>
  );
}
