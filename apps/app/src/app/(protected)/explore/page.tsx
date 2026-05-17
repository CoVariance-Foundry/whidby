import Link from "next/link";
import Sidebar from "@/components/Sidebar";
import Topbar from "@/components/Topbar";
import ExplorePageClient from "@/components/explore/ExplorePageClient";
import { Icon, I } from "@/lib/icons";
import { fromSearchParams, loadExploreData } from "@/lib/explore/load-explore-data";

export const dynamic = "force-dynamic";

function searchParamsKey(
  params: Record<string, string | string[] | undefined>,
): string {
  const keyParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (Array.isArray(value)) {
      value.forEach((item) => keyParams.append(key, item));
    } else if (value != null) {
      keyParams.set(key, value);
    }
  });
  keyParams.sort();
  return keyParams.toString();
}

export default async function ExplorePage({
  searchParams,
}: {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}) {
  const resolvedParams = searchParams ? await searchParams : {};
  const exploreKey = searchParamsKey(resolvedParams);
  const data = await loadExploreData(fromSearchParams(resolvedParams));

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
          <ExplorePageClient key={exploreKey} data={data} />
        </main>
      </div>
    </div>
  );
}
