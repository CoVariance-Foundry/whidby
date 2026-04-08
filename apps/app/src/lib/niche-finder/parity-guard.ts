import type { ExplorationSurfaceResponse } from "@/lib/niche-finder/exploration-types";
import type { StandardSurfaceResponse } from "@/lib/niche-finder/types";

export interface ParityResult {
  isParity: boolean;
  delta: number;
}

export function compareScoreParity(
  standard: StandardSurfaceResponse | null,
  exploration: ExplorationSurfaceResponse | null
): ParityResult {
  if (!standard || !exploration) {
    return { isParity: true, delta: 0 };
  }

  const delta = Math.abs(
    standard.score_result.opportunity_score - exploration.score_result.opportunity_score
  );

  return {
    isParity: delta === 0,
    delta,
  };
}
