from __future__ import annotations

from src.domain.entities import Market, ScoredMarket
from src.domain.lenses import ScoringLens


def score_market(market: Market, lens: ScoringLens) -> ScoredMarket:
    raise NotImplementedError(
        "score_market will be implemented in Phase 4 (lens-based scoring)"
    )
