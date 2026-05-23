import { EntitlementError, resolveEntitlementContext } from "@/lib/account/entitlements";
import { loadAccountSummary } from "@/lib/account/summary";
import { createClient } from "@/lib/supabase/server";
import type { CompetitorIntelTarget } from "@/lib/competitor-intel/types";
import CompetitorIntelClient from "@/components/competitor-intel/CompetitorIntelClient";

export const dynamic = "force-dynamic";

type SearchParams =
  | Promise<Record<string, string | string[] | undefined>>
  | Record<string, string | string[] | undefined>;

function firstParam(
  params: Record<string, string | string[] | undefined>,
  key: keyof CompetitorIntelTarget,
): string | undefined {
  const value = params[key];
  if (Array.isArray(value)) return value[0];
  return value;
}

function parseTarget(params: Record<string, string | string[] | undefined>): CompetitorIntelTarget {
  const dfsCode = firstParam(params, "dataforseo_location_code");
  return {
    report_id: firstParam(params, "report_id"),
    city: firstParam(params, "city"),
    state: firstParam(params, "state"),
    service: firstParam(params, "service"),
    cbsa_code: firstParam(params, "cbsa_code"),
    place_id: firstParam(params, "place_id"),
    dataforseo_location_code:
      dfsCode && Number.isFinite(Number(dfsCode)) ? Number(dfsCode) : undefined,
  };
}

export default async function CompetitorIntelPage({
  searchParams,
}: {
  searchParams?: SearchParams;
}) {
  const resolvedSearchParams = searchParams ? await searchParams : {};
  const target = parseTarget(resolvedSearchParams);
  const supabase = await createClient();
  let summary: Awaited<ReturnType<typeof loadAccountSummary>> | null = null;
  let loadError: unknown = null;

  try {
    const { user, entitlement } = await resolveEntitlementContext(supabase);
    summary = await loadAccountSummary({ supabase, user, entitlement });
  } catch (error) {
    loadError = error;
  }

  if (!summary) {
    const message =
      loadError instanceof EntitlementError
        ? loadError.message
        : "Competitor Intel could not load account entitlement details.";
    return (
      <main className="page competitor-page">
        <section className="competitor-state-panel" role="alert">
          <div className="kicker">Account unavailable</div>
          <h1 className="page-h1">Competitor Intel is unavailable.</h1>
          <p>{message}</p>
        </section>
      </main>
    );
  }

  return (
    <main className="page competitor-page">
      <CompetitorIntelClient
        target={target}
        account={{
          plan_key: summary.plan_key,
          plan_label: summary.plan_label,
          monthly_report_limit: summary.monthly_report_limit,
          fresh_reports_remaining: summary.fresh_reports_remaining,
        }}
      />
    </main>
  );
}
