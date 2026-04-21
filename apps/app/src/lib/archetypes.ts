export type ArchetypeId =
  | "AGG"
  | "PACK_FORT"
  | "PACK_EST"
  | "PACK_VULN"
  | "FRAG_WEAK"
  | "FRAG_COMP"
  | "BARREN"
  | "MIXED";

export interface Archetype {
  id: ArchetypeId;
  title: string;
  short: string;
  glyph: string;
  hint: string;
  strat: string;
}

export const ARCHETYPES: Archetype[] = [
  {
    id: "AGG",
    title: "Aggregator Dominated",
    short: "Aggregator‑dominated",
    glyph: "arch-agg",
    hint: "Yelp, HomeAdvisor own the SERP",
    strat: "Long‑tail first, skip head terms",
  },
  {
    id: "PACK_FORT",
    title: "Local Pack Fortified",
    short: "Pack, fortified",
    glyph: "arch-pack-fort",
    hint: "Strong GBP, actively reviewed",
    strat: "Adjacent sub‑niches, long horizon",
  },
  {
    id: "PACK_EST",
    title: "Local Pack Established",
    short: "Pack, established",
    glyph: "arch-pack-est",
    hint: "Moderate pack, reviews < 100",
    strat: "GBP‑first, 4‑8 month build",
  },
  {
    id: "PACK_VULN",
    title: "Local Pack Vulnerable",
    short: "Pack, vulnerable",
    glyph: "arch-pack-vuln",
    hint: "Weak pack, reviews ≤ 30",
    strat: "GBP + site combo, 2‑4 mo",
  },
  {
    id: "FRAG_WEAK",
    title: "Fragmented Weak",
    short: "Fragmented, weak",
    glyph: "arch-frag-weak",
    hint: "Many local sites, low DA",
    strat: "Classic rank‑and‑rent",
  },
  {
    id: "FRAG_COMP",
    title: "Fragmented Competitive",
    short: "Fragmented, comp.",
    glyph: "arch-frag-comp",
    hint: "Local sites with real authority",
    strat: "Link building + longer timeline",
  },
  {
    id: "BARREN",
    title: "Barren",
    short: "Barren",
    glyph: "arch-barren",
    hint: "Nobody competing for this SERP",
    strat: "Low‑hanging if demand exists",
  },
  {
    id: "MIXED",
    title: "Mixed Signals",
    short: "Mixed",
    glyph: "arch-mixed",
    hint: "No dominant SERP pattern",
    strat: "Inspect gaps in SERP manually",
  },
];
