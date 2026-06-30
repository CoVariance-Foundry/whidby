export const GLOSSARY_TERM_KEYS = [
  "ai_resilience",
  "archetype",
  "hide_flagged",
  "keyword_difficulty",
  "map_pack",
  "feasibility",
  "lookalike",
  "ranked_site",
  "portfolio_builder",
] as const;

export type GlossaryTermKey = (typeof GLOSSARY_TERM_KEYS)[number];

export interface GlossaryTerm {
  key: GlossaryTermKey;
  label: string;
  aliases: readonly string[];
  definition: string;
  context?: string;
}

export interface ResolvedGlossaryTerm {
  key: GlossaryTermKey | "fallback";
  label: string;
  definition: string;
  context?: string;
  isFallback: boolean;
}

export const GLOSSARY_TERMS = [
  {
    key: "ai_resilience",
    label: "AI Resilience",
    aliases: ["ai resilience", "ai_resilience"],
    definition:
      "How protected a niche is from AI answer surfaces and AI-driven traffic loss.",
    context:
      "Local, hands-on services usually score higher because the work cannot be completed by an answer box.",
  },
  {
    key: "archetype",
    label: "Archetype",
    aliases: ["serp archetype", "market archetype"],
    definition:
      "A short label for the search-result pattern Widby sees in a market.",
    context:
      "Archetypes help compare markets quickly without replacing the underlying score breakdown.",
  },
  {
    key: "hide_flagged",
    label: "Hide flagged",
    aliases: ["hide flagged", "flagged", "hide_flagged"],
    definition:
      "A view control that removes risky or unsuitable rows from the current list.",
    context:
      "The result is hidden from view, not deleted from the saved report or run history.",
  },
  {
    key: "keyword_difficulty",
    label: "Keyword Difficulty / KD",
    aliases: ["keyword difficulty", "kd", "keyword difficulty / kd", "difficulty"],
    definition:
      "A compact read on how hard it should be to rank for the target query or market.",
    context: "Lower difficulty means easier entry; Widby still weighs demand and monetization separately.",
  },
  {
    key: "map_pack",
    label: "Map Pack",
    aliases: ["map pack", "local pack", "google maps pack"],
    definition:
      "Google's local results block with map pins and Google Business Profile listings.",
    context:
      "Map Pack strength depends on reviews, profile completeness, proximity signals, and local intent.",
  },
  {
    key: "feasibility",
    label: "Feasibility",
    aliases: ["feasibility", "feasibility preflight", "preflight"],
    definition:
      "A preflight check that confirms a strategy can run before quota, spend, or deeper analysis is used.",
  },
  {
    key: "lookalike",
    label: "Lookalike",
    aliases: ["lookalike", "lookalike city", "lookalike market"],
    definition:
      "A market that resembles a known ranked or promising city closely enough to test as an expansion move.",
  },
  {
    key: "ranked_site",
    label: "Ranked site",
    aliases: ["ranked site", "ranked-site declaration", "ranked site declaration"],
    definition:
      "A site the operator already controls or can verify as ranking for a relevant market.",
    context:
      "Widby uses this proof point to unlock expansion guidance without inferring ownership from a typed URL alone.",
  },
  {
    key: "portfolio_builder",
    label: "Portfolio Builder",
    aliases: ["portfolio builder", "portfolio_builder"],
    definition:
      "A locked future path for planning multiple adjacent market moves from saved context and ranked assets.",
  },
] as const satisfies readonly GlossaryTerm[];

function normalizeGlossaryLookup(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[_-]+/g, " ")
    .replace(/\s*\/\s*/g, " / ")
    .replace(/\s+/g, " ");
}

const glossaryByLookup = new Map<string, GlossaryTerm>();

for (const term of GLOSSARY_TERMS) {
  glossaryByLookup.set(normalizeGlossaryLookup(term.key), term);
  glossaryByLookup.set(normalizeGlossaryLookup(term.label), term);
  for (const alias of term.aliases) {
    glossaryByLookup.set(normalizeGlossaryLookup(alias), term);
  }
}

function fallbackLabelFor(value: string): string {
  const normalized = value.trim().replace(/[_-]+/g, " ");
  if (!normalized) return "Term";
  return normalized.replace(/\b\w/g, (char) => char.toUpperCase());
}

export function getGlossaryTerm(value: string): GlossaryTerm | undefined {
  return glossaryByLookup.get(normalizeGlossaryLookup(value));
}

export function resolveGlossaryTerm(
  value: string,
  fallback?: {
    label?: string;
    definition?: string;
    context?: string;
  },
): ResolvedGlossaryTerm {
  const term = getGlossaryTerm(value);
  if (term) {
    return {
      key: term.key,
      label: term.label,
      definition: term.definition,
      context: term.context,
      isFallback: false,
    };
  }

  return {
    key: "fallback",
    label: fallback?.label ?? fallbackLabelFor(value),
    definition: fallback?.definition ?? "No glossary definition is available yet.",
    context: fallback?.context,
    isFallback: true,
  };
}
