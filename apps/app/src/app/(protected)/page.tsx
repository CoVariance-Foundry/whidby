import DashboardHome from "@/components/home/DashboardHome";
import { loadDashboard } from "@/lib/home/load-dashboard";

export default async function HomePage() {
  const dashboard = await loadDashboard();

  return <DashboardHome dashboard={dashboard} />;
}
