import Link from "next/link";
import Sidebar from "@/components/Sidebar";
import Topbar from "@/components/Topbar";
import ExplorePageClient from "@/components/explore/ExplorePageClient";
import { Icon, I } from "@/lib/icons";
import { loadExploreData } from "@/lib/explore/load-explore-data";
import { createClient } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";

export default async function ExplorePage() {
  const supabase = await createClient();
  const data = await loadExploreData(supabase);

  return (
    <div className="app density-roomy">
      <Sidebar active="explore" />
      <div className="main">
        <Topbar
          crumbs={["Explore"]}
          actions={
            <Link href="/niche-finder" className="btn-primary" style={{ textDecoration: "none", display: "inline-flex" }}>
              <Icon d={I.plus} /> New report
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
          <ExplorePageClient data={data} />
        </main>
      </div>
    </div>
  );
}
