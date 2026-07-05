import Link from "next/link";
import { notFound } from "next/navigation";
import { Icon, I } from "@/lib/icons";
import { loadDashboard } from "@/lib/home/load-dashboard";
import { loadStrategy } from "@/lib/strategies/catalog";
import type { StrategyCatalogEntry } from "@/lib/strategies/types";
import StrategyPageClient, { type StrategyInitialInputs } from "./StrategyPageClient";

export const dynamic = "force-dynamic";

function lockReasonForStrategy(
  strategy: StrategyCatalogEntry,
  unlockState: { has_completed_scan: boolean; has_ranked_site_declaration: boolean },
) {
  const requirementId = strategy.unlock_requirement?.requirement_id;
  if (requirementId === "scan_completed" && !unlockState.has_completed_scan) {
    return "Complete a scan before starting GBP Blitz.";
  }
  if (
    requirementId === "ranked_site_declaration" &&
    !unlockState.has_ranked_site_declaration
  ) {
    return "Declare a ranked site before starting Expand & Conquer.";
  }
  return null;
}

type StrategyPageSearchParams = Record<string, string | string[] | undefined>;

function firstSearchParam(
  params: StrategyPageSearchParams,
  key: keyof StrategyInitialInputs,
): string | undefined {
  const rawValue = params[key];
  const value = Array.isArray(rawValue) ? rawValue[0] : rawValue;
  const trimmed = value?.trim();
  return trimmed || undefined;
}

async function resolveSearchParams(
  searchParams: Promise<StrategyPageSearchParams> | StrategyPageSearchParams | undefined,
): Promise<StrategyPageSearchParams> {
  return searchParams ? searchParams : {};
}

function parseInitialInputs(searchParams: StrategyPageSearchParams): StrategyInitialInputs {
  const city = firstSearchParam(searchParams, "city");
  const cbsaCode = firstSearchParam(searchParams, "cbsa_code");
  const service = firstSearchParam(searchParams, "service");
  const primaryKeyword = firstSearchParam(searchParams, "primary_keyword");
  const referenceCityId = firstSearchParam(searchParams, "reference_city_id");
  return {
    ...(city ? { city } : {}),
    ...(cbsaCode ? { cbsa_code: cbsaCode } : {}),
    ...(service ? { service } : {}),
    ...(primaryKeyword ? { primary_keyword: primaryKeyword } : {}),
    ...(referenceCityId ? { reference_city_id: referenceCityId } : {}),
  };
}

export default async function StrategyPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }> | { id: string };
  searchParams?: Promise<StrategyPageSearchParams> | StrategyPageSearchParams;
}) {
  const resolvedParams = await params;
  const resolvedSearchParams = await resolveSearchParams(searchParams);
  const strategy = await loadStrategy(resolvedParams.id);

  if (!strategy) {
    notFound();
  }

  const dashboard = await loadDashboard();
  const lockedReason = lockReasonForStrategy(strategy, {
    has_completed_scan: dashboard.onboarding.has_completed_scan,
    has_ranked_site_declaration: dashboard.onboarding.has_ranked_site_declaration,
  });

  return (
    <main
      className="page"
      style={{
        maxWidth: 1180,
        margin: "0 auto",
        width: "100%",
      }}
    >
      <Link href="/strategies" className="btn-ghost" style={{ textDecoration: "none", marginBottom: 16 }}>
        <Icon d={I.arrow} style={{ transform: "rotate(180deg)" }} /> Back
      </Link>
      <StrategyPageClient
        strategy={strategy}
        lockedReason={lockedReason}
        initialInputs={parseInitialInputs(resolvedSearchParams)}
      />
    </main>
  );
}
