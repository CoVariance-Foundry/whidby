import Link from "next/link";
import Sidebar from "@/components/Sidebar";
import Topbar from "@/components/Topbar";
import { Icon, I } from "@/lib/icons";
import { loadStrategyCatalog } from "@/lib/strategies/catalog";
import StrategiesGalleryClient from "./StrategiesGalleryClient";

export const dynamic = "force-dynamic";

export default async function StrategiesPage() {
  const catalog = await loadStrategyCatalog();

  return (
    <div className="app density-roomy">
      <Sidebar active="strategies" />
      <div className="main">
        <Topbar
          crumbs={["Strategies"]}
          actions={
            <Link href="/explore" className="btn-ghost" style={{ textDecoration: "none" }}>
              <Icon d={I.map} /> Explore data
            </Link>
          }
        />
        <main
          className="page"
          style={{
            maxWidth: 1280,
            margin: "0 auto",
            width: "100%",
          }}
        >
          <StrategiesGalleryClient catalog={catalog} />
        </main>
      </div>
    </div>
  );
}
