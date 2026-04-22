import Sidebar from "@/components/Sidebar";
import Topbar from "@/components/Topbar";
import NicheFinderClient from "./NicheFinderClient";

export default async function NicheFinderPage() {
  return (
    <div className="app density-roomy">
      <Sidebar active="finder" />
      <div className="main">
        <Topbar crumbs={["Niche finder"]} />
        <NicheFinderClient />
      </div>
    </div>
  );
}
