import { loadDashboard } from "@/lib/home/load-dashboard";
import StrategiesGalleryClient from "./StrategiesGalleryClient";

export const dynamic = "force-dynamic";

export default async function StrategiesPage() {
  const dashboard = await loadDashboard();

  return (
    <main
      className="page"
      style={{
        maxWidth: 1280,
        margin: "0 auto",
        width: "100%",
      }}
    >
      <StrategiesGalleryClient
        catalog={dashboard.strategies.catalog}
        unlockState={{
          has_completed_scan: dashboard.onboarding.has_completed_scan,
          has_ranked_site_declaration: dashboard.onboarding.has_ranked_site_declaration,
        }}
      />
    </main>
  );
}
