import type { SupabaseClient } from "@supabase/supabase-js";
import { resolveEntitlementContext } from "@/lib/account/entitlements";
import { RANKED_SITE_UNLOCK_PROOF_STATES } from "@/lib/strategies/ranked-site-declarations";
import { createClient } from "@/lib/supabase/server";

export interface ProductUnlockState {
  has_completed_scan: boolean;
  has_ranked_site_declaration: boolean;
}

interface RankedSiteDeclarationProbeRow {
  id: string;
}

interface AccountOwnedReportProbeRow {
  id: string;
}

async function hasActiveRankedSiteDeclaration(
  supabase: SupabaseClient,
  accountId: string,
): Promise<boolean> {
  const { data, error } = await supabase
    .from("ranked_site_declarations")
    .select("id")
    .eq("account_id", accountId)
    .eq("active", true)
    .in("proof_state", [...RANKED_SITE_UNLOCK_PROOF_STATES])
    .limit(1)
    .maybeSingle();

  if (error) {
    console.warn("[unlocks] ranked-site declaration probe failed", {
      message: error.message,
    });
    return false;
  }

  return Boolean(data as RankedSiteDeclarationProbeRow | null);
}

async function hasAccountOwnedReport(
  supabase: SupabaseClient,
  accountId: string,
): Promise<boolean> {
  const { data, error } = await supabase
    .from("reports")
    .select("id")
    .eq("owner_account_id", accountId)
    .limit(1)
    .maybeSingle();

  if (error) {
    console.warn("[unlocks] account-owned report probe failed", {
      message: error.message,
    });
    return false;
  }

  return Boolean(data as AccountOwnedReportProbeRow | null);
}

export async function loadProductUnlockState(
  supabase: SupabaseClient,
  accountId: string,
): Promise<ProductUnlockState> {
  const [hasCompletedScan, hasRankedSiteDeclaration] = await Promise.all([
    hasAccountOwnedReport(supabase, accountId),
    hasActiveRankedSiteDeclaration(supabase, accountId),
  ]);

  return {
    has_completed_scan: hasCompletedScan,
    has_ranked_site_declaration: hasRankedSiteDeclaration,
  };
}

export async function loadCurrentProductUnlockState(): Promise<ProductUnlockState> {
  const supabase = await createClient();
  const { entitlement } = await resolveEntitlementContext(supabase);
  return loadProductUnlockState(supabase, entitlement.account_id);
}
