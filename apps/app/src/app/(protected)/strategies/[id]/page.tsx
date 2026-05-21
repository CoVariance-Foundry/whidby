import Link from "next/link";
import { notFound } from "next/navigation";
import { Icon, I } from "@/lib/icons";
import { loadStrategy } from "@/lib/strategies/catalog";
import StrategyPageClient from "./StrategyPageClient";

export const dynamic = "force-dynamic";

export default async function StrategyPage({ params }: { params: Promise<{ id: string }> | { id: string } }) {
  const resolvedParams = await params;
  const strategy = await loadStrategy(resolvedParams.id);

  if (!strategy) {
    notFound();
  }

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
      <StrategyPageClient strategy={strategy} />
    </main>
  );
}
