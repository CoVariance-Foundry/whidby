# Phase 4: Lens-Based Scoring

**Objective:** Refactor the scoring engine to accept weight configurations from `ScoringLens` objects instead of reading `FIXED_WEIGHTS` + `STRATEGY_PROFILES` directly. Define the 4 lenses that work with existing data. The `strategy_profile` request parameter now maps to a lens lookup.

**Risk:** Low-medium. Scoring math changes, but the BALANCED lens must produce identical results to current behavior.
**Depends on:** Phase 1 (lenses defined), Phase 3 (MarketService wired).
**Blocks:** Phase 5 (DiscoveryService uses lens-scored markets).

---

## Agent Instructions

### Step 0: Read existing scoring code

```bash
# Understand current scoring math
cat src/scoring/engine.py
cat src/scoring/composite_score.py  # if it exists

# Understand current weight definitions
cat src/config/constants.py
# Look for: FIXED_WEIGHTS, STRATEGY_PROFILES, M7_DA_CEILING, etc.

# Understand how orchestrator calls scoring
cat src/pipeline/orchestrator.py
# Look for: where compute_opportunity_score or equivalent is called,
# and how strategy_profile is passed through

# Understand current strategy profiles
cat src/scoring/strategy_profiles.py  # if it exists
```

**Map the scoring flow:**
1. Where are weights defined? (`constants.py` → `FIXED_WEIGHTS`, `STRATEGY_PROFILES`)
2. How does `strategy_profile` parameter reach the scoring function?
3. What does `compute_opportunity_score` (or equivalent) accept and return?
4. Which signals feed into the score calculation?
5. Are there any signal-specific ceiling/floor constants? (e.g., `M7_DA_CEILING`)

### Step 1: Implement `src/domain/scoring.py`

This bridges domain lenses to the existing scoring engine.

```python
"""
Score computation: apply a ScoringLens to a Market's signals.

This module bridges the domain model to the scoring math in src/scoring/engine.py.
The scoring engine stays pure — this module translates between domain types
and the engine's input/output formats.
"""
from __future__ import annotations

from typing import Any

from src.domain.entities import Market, ScoredMarket
from src.domain.lenses import ScoringLens, BALANCED


def score_market(market: Market, lens: ScoringLens) -> ScoredMarket:
    """
    Apply a ScoringLens to a Market's signal bundles.

    1. Extract raw signal values from market.signals
    2. Check that lens.required_signals are present
    3. Check lens.filters (pre-conditions)
    4. Apply lens.weights to compute weighted score
    5. Return ScoredMarket with breakdown

    The agent should read engine.py to understand the current scoring math
    and replicate it here using the lens's weight dict instead of FIXED_WEIGHTS.
    """
    # Validate required signals
    missing = lens.required_signals - set(market.signals.keys())
    if missing:
        raise MissingSignalsError(
            f"Lens '{lens.lens_id}' requires signals {missing} "
            f"but market only has {set(market.signals.keys())}"
        )

    # Check filters
    for f in lens.filters:
        signal_value = _extract_signal_value(market.signals, f.signal)
        if signal_value is None:
            continue  # Missing signal — filter doesn't apply
        if not _evaluate_filter(signal_value, f.operator, f.value):
            raise FilterNotMetError(
                f"Lens '{lens.lens_id}' filter failed: "
                f"{f.signal} {f.operator} {f.value} (actual: {signal_value})"
            )

    # Compute weighted score
    score_breakdown = {}
    for signal_name, weight in lens.weights.items():
        raw_value = _extract_signal_value(market.signals, signal_name)
        if raw_value is not None:
            # Normalize signal to 0-100 range
            # The agent should check engine.py for the normalization logic
            normalized = _normalize_signal(signal_name, raw_value)
            score_breakdown[signal_name] = normalized * weight
        else:
            score_breakdown[signal_name] = 0.0

    opportunity_score = sum(score_breakdown.values())

    return ScoredMarket(
        market=market,
        opportunity_score=opportunity_score,
        lens_id=lens.lens_id,
        score_breakdown=score_breakdown,
    )


def score_markets_batch(
    markets: list[Market],
    lens: ScoringLens,
) -> list[ScoredMarket]:
    """Score multiple markets and return sorted by opportunity score."""
    scored = []
    for market in markets:
        try:
            result = score_market(market, lens)
            scored.append(result)
        except (MissingSignalsError, FilterNotMetError):
            continue  # Skip markets that don't meet lens requirements
    scored.sort(key=lambda s: s.opportunity_score, reverse=lens.sort_descending)
    for i, s in enumerate(scored):
        # ScoredMarket is frozen, so create new instance with rank
        scored[i] = ScoredMarket(
            market=s.market,
            opportunity_score=s.opportunity_score,
            lens_id=s.lens_id,
            rank=i + 1,
            score_breakdown=s.score_breakdown,
        )
    return scored


def _extract_signal_value(
    signals: dict[str, dict[str, Any]], signal_name: str
) -> float | None:
    """
    Extract a scalar signal value from the nested signal bundles.

    The agent must map signal names used in lenses (e.g., "demand",
    "organic_competition") to the actual keys in the M6 signal output.
    Read signal_extraction.py and engine.py to understand the structure.
    """
    # Example mapping — adjust based on actual signal structure:
    # signals = {
    #   "demand": {"volume": 1200, "trend": 0.05, "score": 72},
    #   "organic_competition": {"avg_da": 25, "weak_ratio": 0.6, "score": 68},
    #   ...
    # }
    # Return the "score" sub-key for the signal category
    bundle = signals.get(signal_name)
    if bundle is None:
        return None
    if isinstance(bundle, dict):
        return bundle.get("score")
    if isinstance(bundle, (int, float)):
        return float(bundle)
    return None


def _normalize_signal(signal_name: str, value: float) -> float:
    """
    Normalize a signal value to 0-100 scale.

    The agent should check engine.py for existing normalization:
    - DA ceiling constants
    - Volume log scaling
    - Competition inversion (lower DA = higher opportunity)
    - etc.

    If engine.py already returns normalized scores, this may be identity.
    """
    # If the scoring engine already outputs 0-100 scores, just clamp:
    return max(0.0, min(100.0, value))


def _evaluate_filter(value: float, operator: str, threshold: Any) -> bool:
    """Evaluate a filter predicate."""
    ops = {
        ">": lambda v, t: v > t,
        "<": lambda v, t: v < t,
        ">=": lambda v, t: v >= t,
        "<=": lambda v, t: v <= t,
        "=": lambda v, t: v == t,
        "!=": lambda v, t: v != t,
    }
    op_fn = ops.get(operator)
    if op_fn is None:
        raise ValueError(f"Unknown filter operator: {operator}")
    return op_fn(value, threshold)


class MissingSignalsError(Exception):
    """Market doesn't have the signals required by this lens."""
    pass


class FilterNotMetError(Exception):
    """Market doesn't meet a lens's filter pre-conditions."""
    pass
```

### Step 2: Refactor `src/scoring/composite_score.py` (or equivalent)

The key change: `compute_opportunity_score` (or whatever the main scoring function is called) should accept a `weights: dict[str, float]` parameter instead of reading from `FIXED_WEIGHTS` + `STRATEGY_PROFILES`.

```python
# BEFORE (current):
def compute_opportunity_score(signals: dict, strategy_profile: str = "balanced") -> dict:
    weights = FIXED_WEIGHTS.copy()
    profile = STRATEGY_PROFILES[strategy_profile]
    weights["organic_competition"] = profile["organic_weight"]
    weights["local_competition"] = profile["local_weight"]
    # ... compute score using weights

# AFTER (refactored):
def compute_opportunity_score(
    signals: dict,
    weights: dict[str, float] | None = None,
) -> dict:
    """
    Compute opportunity score using provided weights.

    If weights is None, falls back to BALANCED lens weights for backward compat.
    """
    if weights is None:
        # Backward compat: use existing FIXED_WEIGHTS + balanced profile
        weights = {
            "demand": 0.25,
            "organic_competition": 0.175,
            "local_competition": 0.175,
            "monetization": 0.20,
            "ai_resilience": 0.15,
            "gbp": 0.05,
        }
    # ... compute score using weights dict
```

**Critical constraint:** The BALANCED lens weights MUST produce scores identical to the current `balanced` strategy profile. Write a regression test that compares old vs. new output on the same input signals.

### Step 3: Update MarketService to use lens-based scoring

In `src/domain/services/market_service.py`, the `score()` method should pass `lens.weights` to the pipeline/scoring function instead of passing `strategy_profile` as a string.

```python
# In MarketService.score():

# BEFORE:
# pipeline_result = await score_niche_for_metro(
#     ..., strategy_profile=request.strategy_profile, ...
# )

# AFTER:
# pipeline_result = await score_niche_for_metro(
#     ..., weights=lens.weights, ...
# )
```

### Step 4: Map `strategy_profile` request param to lens lookup

In the API handler, the existing `strategy_profile` parameter ("balanced", "organic_first", "local_dominant") should map to lens IDs. Add backward-compat aliases:

```python
# In api.py or in a mapping module:

LEGACY_PROFILE_TO_LENS = {
    "balanced": "balanced",
    "organic_first": "easy_win",      # closest match
    "local_dominant": "gbp_blitz",    # closest match
}

def resolve_lens_id(strategy_profile: str) -> str:
    """Map legacy strategy_profile names to lens IDs."""
    return LEGACY_PROFILE_TO_LENS.get(strategy_profile, strategy_profile)
```

### Step 5: Write tests

**`tests/domain/test_scoring.py`:**

```python
"""Tests for lens-based scoring."""
import pytest
from src.domain.entities import City, Service, Market, ScoredMarket
from src.domain.lenses import BALANCED, EASY_WIN, CASH_COW, GBP_BLITZ, AI_PROOF
from src.domain.scoring import (
    score_market,
    score_markets_batch,
    MissingSignalsError,
    FilterNotMetError,
    _evaluate_filter,
)


def _make_market(signals: dict) -> Market:
    """Helper to create a Market with given signals."""
    return Market(
        city=City(city_id="boise-id", name="Boise", state="ID"),
        service=Service(service_id="plumbing", name="Plumbing"),
        signals=signals,
    )


FULL_SIGNALS = {
    "demand": {"score": 75.0},
    "organic_competition": {"score": 68.0},
    "local_competition": {"score": 55.0},
    "monetization": {"score": 60.0},
    "ai_resilience": {"score": 80.0},
    "gbp": {"score": 45.0},
    "site_quality_gap": {"score": 70.0},
}


def test_score_market_returns_scored_market():
    """Scoring produces a ScoredMarket with breakdown."""
    market = _make_market(FULL_SIGNALS)
    result = score_market(market, BALANCED)
    assert isinstance(result, ScoredMarket)
    assert result.lens_id == "balanced"
    assert result.opportunity_score > 0
    assert len(result.score_breakdown) > 0


def test_score_market_missing_required_signals():
    """Scoring raises when required signals are missing."""
    market = _make_market({"monetization": {"score": 60.0}})
    with pytest.raises(MissingSignalsError):
        score_market(market, BALANCED)  # requires demand, organic_competition


def test_score_market_filter_not_met():
    """Scoring raises when a filter pre-condition fails."""
    signals = {**FULL_SIGNALS, "acv_estimate": {"score": 1500}}
    market = _make_market(signals)
    with pytest.raises(FilterNotMetError):
        score_market(market, CASH_COW)  # requires acv > 3000


def test_balanced_lens_produces_expected_range():
    """BALANCED lens produces a score in reasonable range."""
    market = _make_market(FULL_SIGNALS)
    result = score_market(market, BALANCED)
    assert 0 <= result.opportunity_score <= 100


def test_different_lenses_produce_different_scores():
    """Different lenses weight signals differently."""
    market = _make_market(FULL_SIGNALS)
    balanced = score_market(market, BALANCED)
    easy_win = score_market(market, EASY_WIN)
    assert balanced.opportunity_score != easy_win.opportunity_score


def test_batch_scoring_sorts_by_opportunity():
    """Batch scoring returns markets sorted by score."""
    markets = [
        _make_market({**FULL_SIGNALS, "demand": {"score": 50.0}}),
        _make_market({**FULL_SIGNALS, "demand": {"score": 90.0}}),
        _make_market({**FULL_SIGNALS, "demand": {"score": 70.0}}),
    ]
    results = score_markets_batch(markets, BALANCED)
    scores = [r.opportunity_score for r in results]
    assert scores == sorted(scores, reverse=True)


def test_batch_scoring_assigns_ranks():
    """Batch scoring assigns sequential ranks."""
    markets = [_make_market(FULL_SIGNALS) for _ in range(3)]
    results = score_markets_batch(markets, BALANCED)
    ranks = [r.rank for r in results]
    assert ranks == [1, 2, 3]


def test_batch_scoring_skips_ineligible():
    """Markets missing required signals are excluded from batch results."""
    markets = [
        _make_market(FULL_SIGNALS),
        _make_market({"monetization": {"score": 60.0}}),  # missing demand
        _make_market(FULL_SIGNALS),
    ]
    results = score_markets_batch(markets, BALANCED)
    assert len(results) == 2


def test_evaluate_filter_operators():
    """All filter operators work correctly."""
    assert _evaluate_filter(10, ">", 5) is True
    assert _evaluate_filter(10, "<", 5) is False
    assert _evaluate_filter(10, ">=", 10) is True
    assert _evaluate_filter(10, "<=", 9) is False
    assert _evaluate_filter(10, "=", 10) is True
    assert _evaluate_filter(10, "!=", 10) is False
```

**`tests/scoring/test_backward_compat.py`:**

```python
"""
Regression test: BALANCED lens MUST produce identical scores
to the current balanced strategy profile.

Run this BEFORE and AFTER the refactor to confirm no drift.
"""
import pytest


def test_balanced_lens_matches_legacy_balanced():
    """
    The agent should:
    1. Read the current scoring function and FIXED_WEIGHTS/STRATEGY_PROFILES
    2. Compute a score using the OLD method with a known signal set
    3. Compute a score using the NEW lens-based method with the same signals
    4. Assert they're identical (within floating point tolerance)

    This is the most important test in Phase 4.
    """
    # Example structure — agent fills in with actual constants:
    #
    # known_signals = {
    #     "demand": 75,
    #     "organic_competition": 68,
    #     "local_competition": 55,
    #     "monetization": 60,
    #     "ai_resilience": 80,
    # }
    #
    # old_score = compute_opportunity_score_legacy(known_signals, "balanced")
    # new_score = compute_opportunity_score(known_signals, weights=BALANCED.weights)
    #
    # assert abs(old_score["opportunity"] - new_score["opportunity"]) < 0.01
    pass  # Agent implements this after reading the actual scoring code
```

### Step 6: Validate

```bash
# Run all scoring tests
python -m pytest tests/domain/test_scoring.py -v
python -m pytest tests/scoring/test_backward_compat.py -v

# Run full test suite — no regressions
python -m pytest tests/ -v

# Verify all 4 shippable lenses produce valid scores
python -c "
from src.domain.lenses import BALANCED, EASY_WIN, GBP_BLITZ, AI_PROOF
for lens in [BALANCED, EASY_WIN, GBP_BLITZ, AI_PROOF]:
    total = sum(lens.weights.values())
    print(f'{lens.lens_id}: weights sum = {total:.3f}')
    assert abs(total - 1.0) < 0.01, f'{lens.lens_id} weights do not sum to 1.0'
print('All lens weights valid.')
"

# Verify the scoring function accepts weights dict
grep -n "def compute_opportunity_score" src/scoring/*.py
# Should show the new signature with weights parameter

# Verify old strategy_profile strings still work through the API
curl -X POST http://localhost:8000/api/niches/score \
  -H "Content-Type: application/json" \
  -d '{"niche_keyword":"plumbing","city":"Boise","state":"ID","strategy_profile":"balanced"}'
```

**Done criteria:**
- `compute_opportunity_score` (or equivalent) accepts a `weights: dict[str, float]` parameter
- BALANCED lens produces scores identical to the current `balanced` profile (regression test passes)
- 4 lenses work with existing data: BALANCED, EASY_WIN, GBP_BLITZ, AI_PROOF
- Legacy `strategy_profile` strings ("balanced", "organic_first", "local_dominant") map to lenses
- The remaining 4 lenses (Blue Ocean, Portfolio Builder, Expand & Conquer, Seasonal Arbitrage) are defined but not yet functional (they reference signals from Phase 7 providers)
- All tests pass
- API contract unchanged
