import type { ArchetypeId } from "@/lib/archetypes";

export function deriveArchetype(row: {
  opportunity_score: number | null;
}): ArchetypeId {
  const s = row.opportunity_score;
  if (s === null || s === undefined) return "MIXED";
  if (s >= 75) return "PACK_VULN";
  if (s >= 60) return "FRAG_WEAK";
  if (s >= 45) return "PACK_EST";
  if (s >= 30) return "FRAG_COMP";
  return "BARREN";
}
