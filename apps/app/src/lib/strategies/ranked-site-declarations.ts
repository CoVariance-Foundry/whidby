import type { StrategyUnlockRequirementId } from "@/lib/strategies/path-registry";

export const RANKED_SITE_UNLOCK_STRATEGY_ID = "expand_conquer";
export const RANKED_SITE_UNLOCK_REQUIREMENT_ID =
  "ranked_site_declaration" satisfies StrategyUnlockRequirementId;

export const RANKED_SITE_UNLOCK_PROOF_STATES = ["declared", "verified"] as const;
export const RANKED_SITE_PROOF_STATES = [
  "declared",
  "verified",
  "needs_review",
  "rejected",
] as const;

export type RankedSiteUnlockProofState =
  (typeof RANKED_SITE_UNLOCK_PROOF_STATES)[number];
export type RankedSiteProofState = (typeof RANKED_SITE_PROOF_STATES)[number];

export interface RankedSiteDeclaration {
  id?: string;
  account_id?: string;
  created_by_user_id?: string;
  site_name: string;
  site_url: string | null;
  site_domain: string;
  city: string;
  state: string;
  cbsa_code: string | null;
  niche_keyword: string;
  niche_normalized: string;
  proof_state: RankedSiteProofState;
  active: boolean;
  metadata?: Record<string, unknown>;
  updated_at?: string;
}

export interface RankedSiteUnlockState {
  requirement_id: typeof RANKED_SITE_UNLOCK_REQUIREMENT_ID;
  expand_conquer_unlocked: boolean;
  unlocked_strategy_ids: string[];
  active_declaration_id: string | null;
  active_declaration: RankedSiteDeclaration | null;
}

const UNLOCKING_PROOF_STATE_SET = new Set<string>(RANKED_SITE_UNLOCK_PROOF_STATES);

export function isRankedSiteProofState(value: unknown): value is RankedSiteProofState {
  return (
    typeof value === "string" &&
    RANKED_SITE_PROOF_STATES.includes(value as RankedSiteProofState)
  );
}

export function isRankedSiteDeclarationUnlocking(
  declaration: Pick<RankedSiteDeclaration, "active" | "proof_state">,
): boolean {
  return declaration.active === true && UNLOCKING_PROOF_STATE_SET.has(declaration.proof_state);
}

export function summarizeRankedSiteUnlock(
  declarations: readonly RankedSiteDeclaration[],
): RankedSiteUnlockState {
  const activeDeclaration =
    declarations.find((declaration) => isRankedSiteDeclarationUnlocking(declaration)) ?? null;

  return {
    requirement_id: RANKED_SITE_UNLOCK_REQUIREMENT_ID,
    expand_conquer_unlocked: activeDeclaration !== null,
    unlocked_strategy_ids: activeDeclaration ? [RANKED_SITE_UNLOCK_STRATEGY_ID] : [],
    active_declaration_id: activeDeclaration?.id ?? null,
    active_declaration: activeDeclaration,
  };
}

export function normalizeRankedSiteDomain(value: string): string | null {
  const trimmed = value.trim().toLowerCase();
  if (!trimmed) return null;

  try {
    const candidate = trimmed.includes("://") ? trimmed : `https://${trimmed}`;
    const hostname = new URL(candidate).hostname
      .replace(/^www\./, "")
      .replace(/\.$/, "")
      .toLowerCase();

    if (!hostname || !hostname.includes(".")) return null;
    if (hostname.includes("..")) return null;
    if (!/^[a-z0-9.-]+$/.test(hostname)) return null;

    return hostname;
  } catch {
    return null;
  }
}

export function normalizeRankedSiteNiche(value: string): string {
  const normalized = value
    .trim()
    .toLowerCase()
    .replace(/&/g, " and ")
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");

  return normalized || "unknown";
}
