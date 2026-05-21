import { loadStrategyCatalog } from "@/lib/strategies/catalog";
import StrategiesGalleryClient from "./StrategiesGalleryClient";

export const dynamic = "force-dynamic";

export default async function StrategiesPage() {
  const catalog = await loadStrategyCatalog();

  return (
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
  );
}
