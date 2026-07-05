import Link from "next/link";
import { notFound } from "next/navigation";
import { Icon, I } from "@/lib/icons";
import { loadDashboard } from "@/lib/home/load-dashboard";
import { loadStrategy } from "@/lib/strategies/catalog";
import type { StrategyCatalogEntry } from "@/lib/strategies/types";
import StrategyPageClient from "./StrategyPageClient";

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

export default async function StrategyPage({ params }: { params: Promise<{ id: string }> | { id: string } }) {
  const resolvedParams = await params;
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
      <StrategyPageClient strategy={strategy} lockedReason={lockedReason} />
    </main>
  );
}
