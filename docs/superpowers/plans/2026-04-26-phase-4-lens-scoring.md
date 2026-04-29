# Phase 4: Lens-Based Scoring — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the scoring engine to accept weight configurations from `ScoringLens` objects instead of hardcoded `FIXED_WEIGHTS` + `STRATEGY_PROFILES`, making 4 core lenses (BALANCED, EASY_WIN, GBP_BLITZ, AI_PROOF) functional with existing pipeline data.

**Architecture:** The refactor has three layers: (1) `compute_opportunity_score()` accepts a generic `weights` dict instead of named params; (2) `compute_scores()` in `engine.py` gains an optional `weights` param so callers can pass lens weights directly; (3) `src/domain/scoring.py` bridges domain `Market` + `ScoringLens` to the refactored engine for higher-level consumers. BALANCED lens must produce scores identical to the current `balanced` strategy profile — this is enforced by a regression test locked before any changes.

**Tech Stack:** Python 3.11+, pytest, existing M7 scoring modules (`src/scoring/`), domain layer (`src/domain/`)

**Phase 3 Status:** Phase 3 (MarketService) is complete ([PR #31](https://github.com/CoVariance-Foundry/whidby/pull/31)). `MarketService.score()` currently passes `strategy_profile` as a string to the pipeline. This plan includes wiring it to resolve a `ScoringLens` and pass `lens.weights` instead.

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `src/scoring/composite_score.py` | Accept `component_scores` dict + `weights` dict instead of named params |
| Modify | `src/scoring/engine.py` | Build weights from profile OR accept pre-built weights; compute gbp component |
| Create | `src/scoring/gbp_score.py` | GBP weakness component scorer (derivative from existing GBP signals) |
| Modify | `src/domain/lenses.py` | BALANCED weights match current balanced profile exactly |
| Modify | `src/domain/scoring.py` | Replace NotImplementedError stub with full `score_market()` implementation |
| Modify | `src/domain/__init__.py` | Export `ScoredMarket`, scoring error types |
| Create | `tests/scoring/test_backward_compat.py` | Regression: BALANCED lens = current balanced profile output |
| Create | `tests/domain/test_scoring.py` | Domain scoring unit tests |
| Modify | `tests/domain/test_lenses.py` | Relax weight-sum assertion for BALANCED |
| Modify | `tests/unit/test_m07_competition_inversion_us1.py` | Update to new composite signature |
| Modify | `tests/unit/test_m07_rule_gates_us3.py` | Update to new composite signature |

---

### Task 1: Capture Regression Baseline

**Files:**
- Create: `tests/scoring/test_backward_compat.py`

Lock the current scoring output before changing anything. This test captures exact `compute_scores()` output for the standard fixture with the `"balanced"` profile.

- [ ] **Step 1: Create tests/scoring/ directory and write baseline capture script**

```python
# tests/scoring/__init__.py
# (empty)
```

```python
# tests/scoring/test_backward_compat.py
"""Regression: BALANCED lens must produce identical scores to current balanced profile."""

from src.scoring.engine import compute_scores
from tests.fixtures.m07_scoring_fixtures import metro_cohort


def test_balanced_profile_golden_baseline():
    """Lock current balanced-profile output for BASE_METRO_SIGNAL.

    Run this BEFORE refactoring to capture values, then keep as regression gate.
    """
    cohort = metro_cohort()
    metro = cohort[2]  # 1200-volume entry = BASE_METRO_SIGNAL defaults
    result = compute_scores(
        metro_signals=metro,
        all_metro_signals=cohort,
        strategy_profile="balanced",
    )

    # --- golden values (filled in Step 2 after first run) ---
    assert isinstance(result["opportunity"], float)
    assert isinstance(result["demand"], float)
    assert isinstance(result["organic_competition"], float)
    assert isinstance(result["local_competition"], float)
    assert isinstance(result["monetization"], float)
    assert isinstance(result["ai_resilience"], float)
    assert result["resolved_weights"] == {"organic": 0.15, "local": 0.20}
```

- [ ] **Step 2: Run the test to capture golden values**

Run: `python -m pytest tests/scoring/test_backward_compat.py -v -s`

The test passes (assertions are type-only). Now add a small script to print exact values:

```bash
python -c "
from src.scoring.engine import compute_scores
from tests.fixtures.m07_scoring_fixtures import metro_cohort
cohort = metro_cohort()
metro = cohort[2]
r = compute_scores(metro_signals=metro, all_metro_signals=cohort, strategy_profile='balanced')
for k in ['demand','organic_competition','local_competition','monetization','ai_resilience','opportunity']:
    print(f'{k}: {r[k]!r}')
print(f'resolved_weights: {r[\"resolved_weights\"]!r}')
print(f'confidence_score: {r[\"confidence\"][\"score\"]!r}')
"
```

Record the output. These become the golden values.

- [ ] **Step 3: Update test with exact golden values**

Replace the type-only assertions with exact float comparisons:

```python
def test_balanced_profile_golden_baseline():
    cohort = metro_cohort()
    metro = cohort[2]
    result = compute_scores(
        metro_signals=metro,
        all_metro_signals=cohort,
        strategy_profile="balanced",
    )
    # Replace GOLDEN_XXX with actual values from Step 2
    assert abs(result["demand"] - GOLDEN_DEMAND) < 0.001
    assert abs(result["organic_competition"] - GOLDEN_ORGANIC) < 0.001
    assert abs(result["local_competition"] - GOLDEN_LOCAL) < 0.001
    assert abs(result["monetization"] - GOLDEN_MONETIZATION) < 0.001
    assert abs(result["ai_resilience"] - GOLDEN_AI) < 0.001
    assert abs(result["opportunity"] - GOLDEN_OPPORTUNITY) < 0.001
    assert result["resolved_weights"] == {"organic": 0.15, "local": 0.20}
```

- [ ] **Step 4: Run test to verify golden values pass**

Run: `python -m pytest tests/scoring/test_backward_compat.py::test_balanced_profile_golden_baseline -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/scoring/__init__.py tests/scoring/test_backward_compat.py
git commit -m "test: lock balanced-profile golden baseline before Phase 4 refactor"
```

---

### Task 2: Refactor compute_opportunity_score() Signature

**Files:**
- Modify: `src/scoring/composite_score.py`
- Modify: `tests/unit/test_m07_competition_inversion_us1.py`
- Modify: `tests/unit/test_m07_rule_gates_us3.py`

Change `compute_opportunity_score()` from named params to dict-based params. Gates still apply to the 5 base components only.

- [ ] **Step 1: Refactor composite_score.py**

Replace the full function in `src/scoring/composite_score.py`:

```python
"""Composite opportunity score implementation."""

from __future__ import annotations

from typing import Any

from src.config.constants import (
    M7_AI_FLOOR_COMPONENT_THRESHOLD,
    M7_AI_FLOOR_COMPOSITE_CAP,
    M7_THRESHOLD_GATE_HARD_CAP,
    M7_THRESHOLD_GATE_HARD_MIN_COMPONENT,
    M7_THRESHOLD_GATE_SOFT_CAP,
    M7_THRESHOLD_GATE_SOFT_MIN_COMPONENT,
)

from .normalization import clamp

_BASE_GATE_COMPONENTS = frozenset({
    "demand", "organic_competition", "local_competition",
    "monetization", "ai_resilience",
})


def compute_opportunity_score(
    *,
    component_scores: dict[str, float],
    weights: dict[str, float],
) -> float:
    """Compute composite opportunity score with gates and floors.

    Args:
        component_scores: Component name -> 0-100 score (e.g. demand, organic_competition).
        weights: Component name -> weight (e.g. {"demand": 0.25, ...}).
            Only components present in both dicts contribute to the sum.
            Gates apply only to the 5 base components regardless of extra lens dimensions.
    """
    raw = sum(
        component_scores.get(name, 0.0) * weight
        for name, weight in weights.items()
    )

    gate_values = [
        component_scores[k]
        for k in _BASE_GATE_COMPONENTS
        if k in component_scores
    ]
    if gate_values:
        min_component = min(gate_values)
        if min_component < M7_THRESHOLD_GATE_HARD_MIN_COMPONENT:
            raw = min(raw, M7_THRESHOLD_GATE_HARD_CAP)
        elif min_component < M7_THRESHOLD_GATE_SOFT_MIN_COMPONENT:
            raw = min(raw, M7_THRESHOLD_GATE_SOFT_CAP)

    if component_scores.get("ai_resilience", 100.0) < M7_AI_FLOOR_COMPONENT_THRESHOLD:
        raw = min(raw, M7_AI_FLOOR_COMPOSITE_CAP)

    return clamp(raw)
```

- [ ] **Step 2: Update engine.py to use new signature**

In `src/scoring/engine.py`, find the call to `compute_opportunity_score()` inside `compute_scores()` and replace with the new dict-based call. The function already computes individual component scores and resolves strategy weights. Build dicts from those:

```python
# Inside compute_scores(), after computing individual scores and resolving weights:

component_scores = {
    "demand": demand,
    "organic_competition": organic_competition,
    "local_competition": local_competition,
    "monetization": monetization,
    "ai_resilience": ai_resilience,
}

resolved = resolve_strategy_weights(strategy_profile, flat)
composite_weights = {
    "demand": FIXED_WEIGHTS["demand"],
    "organic_competition": resolved["organic"],
    "local_competition": resolved["local"],
    "monetization": FIXED_WEIGHTS["monetization"],
    "ai_resilience": FIXED_WEIGHTS["ai_resilience"],
}

opportunity = compute_opportunity_score(
    component_scores=component_scores,
    weights=composite_weights,
)
```

Keep the return dict structure unchanged — callers still get `{"demand": float, "organic_competition": float, ..., "opportunity": float, "resolved_weights": dict, "confidence": dict}`.

- [ ] **Step 3: Update test_m07_competition_inversion_us1.py**

Replace direct `compute_opportunity_score()` calls with the new signature:

```python
# tests/unit/test_m07_competition_inversion_us1.py
"""US1 tests for competition inversion behavior."""

from src.scoring.composite_score import compute_opportunity_score
from src.scoring.organic_competition_score import compute_organic_competition_score
from src.scoring.strategy_profiles import resolve_strategy_weights
from tests.fixtures.m07_scoring_fixtures import metro_signal


def test_lower_da_competitor_gets_higher_organic_competition_score() -> None:
    weak_competitors = metro_signal(avg_top5_da=18.0, aggregator_count=0.0)
    strong_competitors = metro_signal(avg_top5_da=55.0, aggregator_count=3.0)
    weak_score = compute_organic_competition_score(weak_competitors)
    strong_score = compute_organic_competition_score(strong_competitors)
    assert weak_score > strong_score


def test_higher_competition_does_not_inflate_opportunity() -> None:
    weights = resolve_strategy_weights("balanced", metro_signal())
    composite_weights = {
        "demand": 0.25,
        "organic_competition": weights["organic"],
        "local_competition": weights["local"],
        "monetization": 0.20,
        "ai_resilience": 0.15,
    }
    easier = compute_opportunity_score(
        component_scores={
            "demand": 70.0,
            "organic_competition": 75.0,
            "local_competition": 72.0,
            "monetization": 65.0,
            "ai_resilience": 70.0,
        },
        weights=composite_weights,
    )
    harder = compute_opportunity_score(
        component_scores={
            "demand": 70.0,
            "organic_competition": 30.0,
            "local_competition": 25.0,
            "monetization": 65.0,
            "ai_resilience": 70.0,
        },
        weights=composite_weights,
    )
    assert easier > harder
```

- [ ] **Step 4: Update test_m07_rule_gates_us3.py**

```python
# tests/unit/test_m07_rule_gates_us3.py
"""US3 tests for threshold gates and local-pack defaults."""

from src.scoring.composite_score import compute_opportunity_score
from src.scoring.local_competition_score import compute_local_competition_score
from tests.fixtures.m07_scoring_fixtures import metro_signal

_BALANCED_WEIGHTS = {
    "demand": 0.25,
    "organic_competition": 0.15,
    "local_competition": 0.20,
    "monetization": 0.20,
    "ai_resilience": 0.15,
}


def test_no_local_pack_returns_default_score() -> None:
    score = compute_local_competition_score(metro_signal(local_pack_present=False))
    assert score == 75.0


def test_threshold_gate_caps_composite_when_component_below_5() -> None:
    score = compute_opportunity_score(
        component_scores={
            "demand": 4.0,
            "organic_competition": 80.0,
            "local_competition": 80.0,
            "monetization": 80.0,
            "ai_resilience": 80.0,
        },
        weights=_BALANCED_WEIGHTS,
    )
    assert score <= 20.0


def test_ai_floor_caps_composite_when_ai_resilience_is_low() -> None:
    score = compute_opportunity_score(
        component_scores={
            "demand": 90.0,
            "organic_competition": 90.0,
            "local_competition": 90.0,
            "monetization": 90.0,
            "ai_resilience": 10.0,
        },
        weights=_BALANCED_WEIGHTS,
    )
    assert score <= 50.0
```

- [ ] **Step 5: Run all scoring tests**

Run: `python -m pytest tests/unit/test_m07_competition_inversion_us1.py tests/unit/test_m07_rule_gates_us3.py tests/unit/test_m07_composite_profiles_us2.py tests/scoring/test_backward_compat.py -v`

Expected: ALL PASS. The golden baseline test is the critical one — if it passes, the refactor is behavior-preserving.

- [ ] **Step 6: Run full M7 test suite**

Run: `python -m pytest tests/unit/ -k "m07" -v`

Expected: ALL PASS.

- [ ] **Step 7: Commit**

```bash
git add src/scoring/composite_score.py src/scoring/engine.py \
  tests/unit/test_m07_competition_inversion_us1.py \
  tests/unit/test_m07_rule_gates_us3.py
git commit -m "refactor(scoring): compute_opportunity_score accepts weights dict

Replace named params (demand, organic_weight, etc.) with
component_scores + weights dicts. Gates still apply to the
5 base components. All existing tests pass unchanged."
```

---

### Task 3: Update BALANCED Lens to Match Current Weights

**Files:**
- Modify: `src/domain/lenses.py`
- Modify: `tests/domain/test_lenses.py`

The Phase 1 BALANCED lens has `organic: 0.175, local: 0.175, gbp: 0.05` (sum 1.0). Current balanced profile uses `organic: 0.15, local: 0.20` (sum 0.95, no gbp). Must match for backward compat.

- [ ] **Step 1: Write a failing test for the corrected BALANCED weights**

Add to `tests/domain/test_lenses.py`:

```python
def test_balanced_lens_matches_legacy_profile_exactly():
    """BALANCED lens weights must produce identical scores to legacy balanced profile."""
    assert BALANCED.weights == {
        "demand": 0.25,
        "organic_competition": 0.15,
        "local_competition": 0.20,
        "monetization": 0.20,
        "ai_resilience": 0.15,
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/domain/test_lenses.py::test_balanced_lens_matches_legacy_profile_exactly -v`

Expected: FAIL — current BALANCED has different organic/local split and includes gbp.

- [ ] **Step 3: Update BALANCED lens in lenses.py**

In `src/domain/lenses.py`, replace the BALANCED definition:

```python
BALANCED = ScoringLens(
    lens_id="balanced",
    name="Balanced",
    description="Default balanced scoring across all signal dimensions.",
    weights={
        "demand": 0.25,
        "organic_competition": 0.15,
        "local_competition": 0.20,
        "monetization": 0.20,
        "ai_resilience": 0.15,
    },
    required_signals=frozenset({"demand", "organic_competition"}),
)
```

- [ ] **Step 4: Update test_all_lens_weights_sum_to_one**

The BALANCED weights now sum to 0.95 (matching legacy behavior). Relax the assertion:

```python
def test_all_lens_weights_sum_is_valid():
    for lens in ALL_LENSES:
        total = sum(lens.weights.values())
        assert 0.90 <= total <= 1.01, (
            f"Lens '{lens.lens_id}' weights sum to {total}, expected 0.90-1.0"
        )
```

- [ ] **Step 5: Run lens tests**

Run: `python -m pytest tests/domain/test_lenses.py -v`

Expected: ALL PASS

- [ ] **Step 6: Run backward compat regression**

Run: `python -m pytest tests/scoring/test_backward_compat.py -v`

Expected: PASS (BALANCED weights now match legacy profile)

- [ ] **Step 7: Commit**

```bash
git add src/domain/lenses.py tests/domain/test_lenses.py
git commit -m "fix(domain): BALANCED lens weights match legacy balanced profile

Drop gbp weight, restore organic=0.15/local=0.20 split (sum 0.95).
Ensures BALANCED lens produces identical scores to current pipeline."
```

---

### Task 4: Add GBP Component Scorer

**Files:**
- Create: `src/scoring/gbp_score.py`
- Create: `tests/unit/test_gbp_score.py`
- Modify: `src/scoring/engine.py` (register in component computation)

GBP_BLITZ has `required_signals={"local_competition", "gbp"}` and `gbp` weight of 0.30. Without a GBP component scorer, GBP_BLITZ can't function. The scorer extracts GBP weakness from existing pipeline signals (`gbp_completeness_avg`, `gbp_photo_count_avg`, `gbp_posting_activity`).

- [ ] **Step 1: Write failing tests for GBP scorer**

```python
# tests/unit/test_gbp_score.py
"""Tests for GBP weakness component scorer."""

from src.scoring.gbp_score import compute_gbp_score
from tests.fixtures.m07_scoring_fixtures import metro_signal


def test_weak_gbp_produces_high_score() -> None:
    """Weak GBP profiles = high opportunity score."""
    signals = metro_signal(
        gbp_completeness_avg=0.20,
        gbp_photo_count_avg=2.0,
        gbp_posting_activity=0.10,
    )
    score = compute_gbp_score(signals)
    assert score > 70.0


def test_strong_gbp_produces_low_score() -> None:
    """Strong GBP profiles = low opportunity score."""
    signals = metro_signal(
        gbp_completeness_avg=0.95,
        gbp_photo_count_avg=45.0,
        gbp_posting_activity=0.90,
    )
    score = compute_gbp_score(signals)
    assert score < 20.0


def test_gbp_score_in_valid_range() -> None:
    score = compute_gbp_score(metro_signal())
    assert 0.0 <= score <= 100.0


def test_gbp_missing_signals_uses_defaults() -> None:
    """Missing GBP signals fall back to neutral defaults."""
    score = compute_gbp_score({})
    assert 0.0 <= score <= 100.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/test_gbp_score.py -v`

Expected: FAIL — `ImportError: cannot import name 'compute_gbp_score'`

- [ ] **Step 3: Implement GBP scorer**

```python
# src/scoring/gbp_score.py
"""GBP weakness component scorer.

Measures Google Business Profile weakness — higher score means weaker
competitor GBP profiles (= more opportunity for GBP Blitz strategy).
"""

from __future__ import annotations

from typing import Any, Mapping

from src.config.constants import M7_PHOTO_COUNT_CEILING

from .normalization import clamp, inverse_scale


def compute_gbp_score(signals: Mapping[str, Any]) -> float:
    """Compute GBP weakness score in [0, 100]. Higher = weaker competitor GBP."""
    completeness = float(signals.get("gbp_completeness_avg", 0.5))
    photo_count = float(signals.get("gbp_photo_count_avg", 25.0))
    posting = float(signals.get("gbp_posting_activity", 0.5))

    completeness_weakness = (1.0 - completeness) * 100.0
    photo_weakness = inverse_scale(photo_count, floor=0.0, ceiling=M7_PHOTO_COUNT_CEILING)
    posting_weakness = (1.0 - posting) * 100.0

    raw = (
        completeness_weakness * 0.40
        + photo_weakness * 0.30
        + posting_weakness * 0.30
    )
    return clamp(raw)
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/unit/test_gbp_score.py -v`

Expected: ALL PASS

- [ ] **Step 5: Register GBP scorer in engine.py**

In `src/scoring/engine.py`, import `compute_gbp_score` and add it to the component computation inside `compute_scores()`. Add `"gbp"` to the `component_scores` dict:

```python
from src.scoring.gbp_score import compute_gbp_score

# Inside compute_scores(), after computing the 5 base components:
gbp = compute_gbp_score(flat)

component_scores = {
    "demand": demand,
    "organic_competition": organic_competition,
    "local_competition": local_competition,
    "monetization": monetization,
    "ai_resilience": ai_resilience,
    "gbp": gbp,
}
```

Also add `"gbp"` to the return dict so callers can access it.

- [ ] **Step 6: Run regression baseline**

Run: `python -m pytest tests/scoring/test_backward_compat.py -v`

Expected: PASS — the `gbp` component is computed but the balanced weights don't include it, so the composite score is unchanged.

- [ ] **Step 7: Commit**

```bash
git add src/scoring/gbp_score.py tests/unit/test_gbp_score.py src/scoring/engine.py
git commit -m "feat(scoring): add GBP weakness component scorer

Extracts GBP opportunity from gbp_completeness_avg, gbp_photo_count_avg,
and gbp_posting_activity. Registered in engine.py for lens-based scoring.
Does not affect composite score unless lens weights include gbp."
```

---

### Task 5: Add Optional weights Param to compute_scores()

**Files:**
- Modify: `src/scoring/engine.py`
- Create: `tests/scoring/test_lens_weights_passthrough.py`

Allow callers to pass pre-built weights (from a lens) instead of a strategy_profile string. This is the bridge that lets the orchestrator use lens-based scoring.

- [ ] **Step 1: Write test for weights passthrough**

```python
# tests/scoring/test_lens_weights_passthrough.py
"""Test that compute_scores accepts pre-built weights from a lens."""

from src.scoring.engine import compute_scores
from tests.fixtures.m07_scoring_fixtures import metro_cohort


def test_explicit_weights_override_strategy_profile():
    """When weights are provided, strategy_profile is ignored."""
    cohort = metro_cohort()
    metro = cohort[2]

    # Use explicit weights matching balanced profile
    balanced_weights = {
        "demand": 0.25,
        "organic_competition": 0.15,
        "local_competition": 0.20,
        "monetization": 0.20,
        "ai_resilience": 0.15,
    }
    explicit = compute_scores(
        metro_signals=metro,
        all_metro_signals=cohort,
        weights=balanced_weights,
    )
    from_profile = compute_scores(
        metro_signals=metro,
        all_metro_signals=cohort,
        strategy_profile="balanced",
    )
    assert abs(explicit["opportunity"] - from_profile["opportunity"]) < 0.001


def test_lens_weights_with_gbp_produce_different_score():
    """Lens weights that include gbp produce different composite than balanced."""
    cohort = metro_cohort()
    metro = cohort[2]

    gbp_blitz_weights = {
        "demand": 0.15,
        "organic_competition": 0.10,
        "local_competition": 0.30,
        "monetization": 0.10,
        "ai_resilience": 0.05,
        "gbp": 0.30,
    }
    result = compute_scores(
        metro_signals=metro,
        all_metro_signals=cohort,
        weights=gbp_blitz_weights,
    )
    balanced = compute_scores(
        metro_signals=metro,
        all_metro_signals=cohort,
        strategy_profile="balanced",
    )
    assert result["opportunity"] != balanced["opportunity"]
    assert "gbp" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/scoring/test_lens_weights_passthrough.py -v`

Expected: FAIL — `compute_scores()` doesn't accept `weights` param yet.

- [ ] **Step 3: Add optional weights param to compute_scores()**

In `src/scoring/engine.py`, modify `compute_scores()`:

```python
def compute_scores(
    *,
    metro_signals: Mapping[str, Any],
    all_metro_signals: Sequence[Mapping[str, Any]],
    strategy_profile: str = "balanced",
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Compute all M7 scores for a single metro.

    If weights is provided, it is used directly for the composite score
    and strategy_profile is ignored. Otherwise weights are derived from
    strategy_profile via resolve_strategy_weights().
    """
    flat = _flatten_signal_shape(metro_signals)

    demand = compute_demand_score(flat, [_flatten_signal_shape(m) for m in all_metro_signals])
    organic_competition = compute_organic_competition_score(flat)
    local_competition = compute_local_competition_score(flat)
    monetization = compute_monetization_score(flat)
    ai_resilience = compute_ai_resilience_score(flat)
    gbp = compute_gbp_score(flat)

    component_scores = {
        "demand": demand,
        "organic_competition": organic_competition,
        "local_competition": local_competition,
        "monetization": monetization,
        "ai_resilience": ai_resilience,
        "gbp": gbp,
    }

    if weights is not None:
        composite_weights = weights
        resolved = None
    else:
        resolved = resolve_strategy_weights(strategy_profile, flat)
        composite_weights = {
            "demand": FIXED_WEIGHTS["demand"],
            "organic_competition": resolved["organic"],
            "local_competition": resolved["local"],
            "monetization": FIXED_WEIGHTS["monetization"],
            "ai_resilience": FIXED_WEIGHTS["ai_resilience"],
        }

    opportunity = compute_opportunity_score(
        component_scores=component_scores,
        weights=composite_weights,
    )

    confidence = compute_confidence(flat)

    return {
        **component_scores,
        "opportunity": opportunity,
        "confidence": confidence,
        "resolved_weights": resolved,
    }
```

Note: when using explicit weights, `resolved_weights` is `None` — callers should handle this.

Also update `compute_batch_scores()` to pass through the optional weights param:

```python
def compute_batch_scores(
    metros: Sequence[Mapping[str, Any]],
    strategy_profile: str = "balanced",
    weights: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    """Compute M7 scores for a metro batch using shared cohort context."""
    flattened = [_flatten_signal_shape(m) for m in metros]
    return [
        compute_scores(
            metro_signals=m,
            all_metro_signals=metros,
            strategy_profile=strategy_profile,
            weights=weights,
        )
        for m in metros
    ]
```

- [ ] **Step 4: Run passthrough tests**

Run: `python -m pytest tests/scoring/test_lens_weights_passthrough.py -v`

Expected: PASS

- [ ] **Step 5: Run full regression**

Run: `python -m pytest tests/scoring/test_backward_compat.py tests/unit/ -k "m07" -v`

Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add src/scoring/engine.py tests/scoring/test_lens_weights_passthrough.py
git commit -m "feat(scoring): compute_scores accepts optional weights dict

When weights is provided, the composite score uses those weights
directly instead of deriving them from strategy_profile. This is
the bridge for lens-based scoring through the existing engine."
```

---

### Task 6: Implement score_market() Domain Scoring (TDD)

**Files:**
- Modify: `src/domain/scoring.py` (replace NotImplementedError stub)
- Create: `tests/domain/test_scoring.py`
- Modify: `src/domain/__init__.py` (export new types)

This is the domain-level scoring function that bridges `Market` + `ScoringLens` to the refactored engine.

- [ ] **Step 1: Write failing domain scoring tests**

```python
# tests/domain/test_scoring.py
"""Tests for lens-based domain scoring."""

import pytest
from src.domain.entities import City, Service, Market, ScoredMarket
from src.domain.lenses import BALANCED, EASY_WIN, GBP_BLITZ, AI_PROOF
from src.domain.scoring import (
    score_market,
    score_markets_batch,
    MissingSignalsError,
    FilterNotMetError,
)


def _make_market(**score_overrides: float) -> Market:
    """Create a Market with pre-computed component scores."""
    base_scores = {
        "demand": 75.0,
        "organic_competition": 68.0,
        "local_competition": 55.0,
        "monetization": 60.0,
        "ai_resilience": 80.0,
        "gbp": 45.0,
    }
    base_scores.update(score_overrides)
    signals = {name: {"score": score} for name, score in base_scores.items()}
    return Market(
        city=City(city_id="boise-id", name="Boise", state="ID"),
        service=Service(service_id="plumbing", name="Plumbing"),
        signals=signals,
    )


def test_score_market_returns_scored_market():
    market = _make_market()
    result = score_market(market, BALANCED)
    assert isinstance(result, ScoredMarket)
    assert result.lens_id == "balanced"
    assert result.opportunity_score > 0
    assert len(result.score_breakdown) > 0


def test_score_market_balanced_breakdown_matches_weights():
    market = _make_market()
    result = score_market(market, BALANCED)
    for name, weight in BALANCED.weights.items():
        expected = market.signals.get(name, {}).get("score", 0.0) * weight
        assert abs(result.score_breakdown[name] - expected) < 0.01


def test_score_market_missing_required_signals():
    signals = {"monetization": {"score": 60.0}}
    market = Market(
        city=City(city_id="boise-id", name="Boise", state="ID"),
        service=Service(service_id="plumbing", name="Plumbing"),
        signals=signals,
    )
    with pytest.raises(MissingSignalsError):
        score_market(market, BALANCED)


def test_score_market_filter_not_met():
    market = _make_market()
    # GBP_BLITZ filter: avg_reviews < 30
    # Add avg_reviews=50 which FAILS the filter
    market_signals = dict(market.signals)
    market_signals["local_competition"] = {"score": 55.0, "avg_reviews": 50.0}
    market_with_filter = Market(
        city=market.city,
        service=market.service,
        signals=market_signals,
    )
    with pytest.raises(FilterNotMetError):
        score_market(market_with_filter, GBP_BLITZ)


def test_score_market_filter_passes():
    market = _make_market()
    market_signals = dict(market.signals)
    market_signals["local_competition"] = {"score": 55.0, "avg_reviews": 15.0}
    market_ok = Market(
        city=market.city,
        service=market.service,
        signals=market_signals,
    )
    result = score_market(market_ok, GBP_BLITZ)
    assert result.lens_id == "gbp_blitz"


def test_balanced_score_in_valid_range():
    market = _make_market()
    result = score_market(market, BALANCED)
    assert 0 <= result.opportunity_score <= 100


def test_different_lenses_produce_different_scores():
    market = _make_market()
    balanced = score_market(market, BALANCED)
    ai_proof = score_market(market, AI_PROOF)
    assert balanced.opportunity_score != ai_proof.opportunity_score


def test_batch_scoring_sorts_by_opportunity():
    markets = [
        _make_market(demand=50.0),
        _make_market(demand=90.0),
        _make_market(demand=70.0),
    ]
    results = score_markets_batch(markets, BALANCED)
    scores = [r.opportunity_score for r in results]
    assert scores == sorted(scores, reverse=True)


def test_batch_scoring_assigns_ranks():
    markets = [_make_market(demand=d) for d in [90.0, 70.0, 50.0]]
    results = score_markets_batch(markets, BALANCED)
    ranks = [r.rank for r in results]
    assert ranks == [1, 2, 3]


def test_batch_scoring_skips_ineligible():
    ok_market = _make_market()
    bad_market = Market(
        city=City(city_id="x", name="X", state="XX"),
        service=Service(service_id="x", name="X"),
        signals={"monetization": {"score": 60.0}},
    )
    results = score_markets_batch([ok_market, bad_market, ok_market], BALANCED)
    assert len(results) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/domain/test_scoring.py -v`

Expected: FAIL — `ImportError: cannot import name 'MissingSignalsError'`

- [ ] **Step 3: Implement score_market()**

Replace `src/domain/scoring.py` entirely:

```python
"""Score computation: apply a ScoringLens to a Market's pre-computed signals.

Bridges the domain model (Market, ScoringLens) to the scoring engine in
src/scoring/composite_score.py. Component scores must be pre-computed and
stored in Market.signals as {component_name: {"score": float, ...}}.
"""

from __future__ import annotations

from typing import Any

from src.domain.entities import Market, ScoredMarket
from src.domain.lenses import ScoringLens
from src.scoring.composite_score import compute_opportunity_score


class MissingSignalsError(Exception):
    """Market doesn't have the signals required by this lens."""


class FilterNotMetError(Exception):
    """Market doesn't meet a lens's filter pre-conditions."""


def score_market(market: Market, lens: ScoringLens) -> ScoredMarket:
    """Apply a ScoringLens to a Market's pre-computed component scores.

    Market.signals must contain {component_name: {"score": float}} entries
    for each component the lens references. Components not present in
    signals contribute 0 to the weighted sum.
    """
    component_scores = _extract_component_scores(market.signals, lens)

    missing = lens.required_signals - set(component_scores.keys())
    if missing:
        raise MissingSignalsError(
            f"Lens '{lens.lens_id}' requires {missing} "
            f"but market only has {set(component_scores.keys())}"
        )

    _check_filters(market, lens)

    opportunity = compute_opportunity_score(
        component_scores=component_scores,
        weights=lens.weights,
    )

    score_breakdown = {
        name: component_scores.get(name, 0.0) * weight
        for name, weight in lens.weights.items()
    }

    return ScoredMarket(
        market=market,
        opportunity_score=opportunity,
        lens_id=lens.lens_id,
        score_breakdown=score_breakdown,
    )


def score_markets_batch(
    markets: list[Market],
    lens: ScoringLens,
) -> list[ScoredMarket]:
    """Score multiple markets, sort by opportunity, assign ranks."""
    scored: list[ScoredMarket] = []
    for market in markets:
        try:
            result = score_market(market, lens)
            scored.append(result)
        except (MissingSignalsError, FilterNotMetError):
            continue

    scored.sort(key=lambda s: s.opportunity_score, reverse=lens.sort_descending)

    return [
        ScoredMarket(
            market=s.market,
            opportunity_score=s.opportunity_score,
            lens_id=s.lens_id,
            rank=i + 1,
            score_breakdown=s.score_breakdown,
        )
        for i, s in enumerate(scored)
    ]


def _extract_component_scores(
    signals: dict[str, dict[str, Any]],
    lens: ScoringLens,
) -> dict[str, float]:
    """Extract component scores from Market.signals for all lens-referenced keys."""
    all_keys = set(lens.weights.keys()) | lens.required_signals
    scores: dict[str, float] = {}
    for key in all_keys:
        bundle = signals.get(key)
        if bundle is None:
            continue
        if isinstance(bundle, dict):
            score = bundle.get("score")
            if score is not None:
                scores[key] = float(score)
        elif isinstance(bundle, (int, float)):
            scores[key] = float(bundle)
    return scores


def _check_filters(market: Market, lens: ScoringLens) -> None:
    """Evaluate all lens filters against the market's signals and attributes."""
    for f in lens.filters:
        value = _extract_filter_value(market, f.signal)
        if value is None:
            continue
        if not _evaluate_filter(value, f.operator, f.value):
            raise FilterNotMetError(
                f"Lens '{lens.lens_id}' filter failed: "
                f"{f.signal} {f.operator} {f.value} (actual: {value})"
            )


def _extract_filter_value(market: Market, signal_name: str) -> float | None:
    """Search market signals and attributes for a filter value."""
    for bundle in market.signals.values():
        if isinstance(bundle, dict) and signal_name in bundle:
            val = bundle[signal_name]
            if isinstance(val, (int, float)):
                return float(val)

    if hasattr(market.service, signal_name):
        val = getattr(market.service, signal_name)
        if val is not None:
            return float(val)

    direct = market.signals.get(signal_name)
    if isinstance(direct, (int, float)):
        return float(direct)
    if isinstance(direct, dict) and "value" in direct:
        return float(direct["value"])

    return None


def _evaluate_filter(value: float, operator: str, threshold: Any) -> bool:
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
```

- [ ] **Step 4: Update src/domain/__init__.py**

Add `ScoredMarket` and scoring error exports:

```python
from src.domain.entities import City, Service, Market, ScoredMarket
from src.domain.signals import SignalType
from src.domain.lenses import ScoringLens
from src.domain.queries import MarketQuery, CityFilter, ServiceFilter
from src.domain.scoring import MissingSignalsError, FilterNotMetError

__all__ = [
    "City",
    "Service",
    "Market",
    "ScoredMarket",
    "SignalType",
    "ScoringLens",
    "MarketQuery",
    "CityFilter",
    "ServiceFilter",
    "MissingSignalsError",
    "FilterNotMetError",
]
```

- [ ] **Step 5: Run domain scoring tests**

Run: `python -m pytest tests/domain/test_scoring.py -v`

Expected: ALL PASS

- [ ] **Step 6: Run full test suite**

Run: `python -m pytest tests/ -v`

Expected: ALL PASS (no regressions)

- [ ] **Step 7: Commit**

```bash
git add src/domain/scoring.py src/domain/__init__.py tests/domain/test_scoring.py
git commit -m "feat(domain): implement score_market with lens-based scoring

Replace NotImplementedError stub with full implementation:
- score_market: Market + ScoringLens -> ScoredMarket
- score_markets_batch: batch scoring with sort and ranking
- Filter validation and required_signals checking
- MissingSignalsError, FilterNotMetError for lens gating"
```

---

### Task 7: Add Legacy Profile-to-Lens Mapping

**Files:**
- Create: `src/domain/lens_compat.py`
- Create: `tests/domain/test_lens_compat.py`

Map legacy `strategy_profile` strings to lens IDs for API backward compatibility.

- [ ] **Step 1: Write failing tests**

```python
# tests/domain/test_lens_compat.py
"""Tests for legacy strategy_profile -> lens mapping."""

from src.domain.lens_compat import resolve_lens_id, resolve_lens
from src.domain.lenses import BALANCED, EASY_WIN, GBP_BLITZ, AI_PROOF


def test_balanced_maps_to_balanced():
    assert resolve_lens_id("balanced") == "balanced"


def test_organic_first_maps_to_easy_win():
    assert resolve_lens_id("organic_first") == "easy_win"


def test_local_dominant_maps_to_gbp_blitz():
    assert resolve_lens_id("local_dominant") == "gbp_blitz"


def test_unknown_profile_passes_through():
    assert resolve_lens_id("ai_proof") == "ai_proof"


def test_resolve_lens_returns_lens_object():
    lens = resolve_lens("balanced")
    assert lens.lens_id == "balanced"


def test_resolve_lens_with_legacy_name():
    lens = resolve_lens("organic_first")
    assert lens.lens_id == "easy_win"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/domain/test_lens_compat.py -v`

Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement lens_compat.py**

```python
# src/domain/lens_compat.py
"""Map legacy strategy_profile names to ScoringLens objects."""

from __future__ import annotations

from src.domain.lenses import ScoringLens, get_lens

LEGACY_PROFILE_TO_LENS: dict[str, str] = {
    "balanced": "balanced",
    "organic_first": "easy_win",
    "local_dominant": "gbp_blitz",
}


def resolve_lens_id(strategy_profile: str) -> str:
    """Map a legacy strategy_profile name to a lens_id."""
    return LEGACY_PROFILE_TO_LENS.get(strategy_profile, strategy_profile)


def resolve_lens(strategy_profile: str) -> ScoringLens:
    """Resolve a strategy_profile string to a ScoringLens object."""
    return get_lens(resolve_lens_id(strategy_profile))
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/domain/test_lens_compat.py -v`

Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/domain/lens_compat.py tests/domain/test_lens_compat.py
git commit -m "feat(domain): add legacy strategy_profile to lens mapping

Maps balanced->balanced, organic_first->easy_win,
local_dominant->gbp_blitz. Unknown profiles pass through as lens_id."
```

---

### Task 8: Full Validation and Regression Gate

**Files:**
- Modify: `tests/scoring/test_backward_compat.py` (add lens-vs-legacy comparison)

Final validation that everything works together.

- [ ] **Step 1: Add lens-vs-legacy regression test**

Add to `tests/scoring/test_backward_compat.py`:

```python
from src.domain.lenses import BALANCED


def test_balanced_lens_weights_match_engine_legacy_path():
    """BALANCED lens through compute_scores(weights=...) matches strategy_profile='balanced'."""
    cohort = metro_cohort()
    metro = cohort[2]

    from_profile = compute_scores(
        metro_signals=metro,
        all_metro_signals=cohort,
        strategy_profile="balanced",
    )
    from_lens = compute_scores(
        metro_signals=metro,
        all_metro_signals=cohort,
        weights=BALANCED.weights,
    )
    assert abs(from_profile["opportunity"] - from_lens["opportunity"]) < 0.001
```

- [ ] **Step 2: Run the full test**

Run: `python -m pytest tests/scoring/test_backward_compat.py -v`

Expected: ALL PASS

- [ ] **Step 3: Run all Phase 4 tests together**

Run: `python -m pytest tests/domain/test_scoring.py tests/domain/test_lenses.py tests/domain/test_lens_compat.py tests/scoring/ tests/unit/ -v`

Expected: ALL PASS

- [ ] **Step 4: Run ruff lint**

Run: `ruff check src/scoring/ src/domain/ tests/`

Expected: Clean (zero errors)

- [ ] **Step 5: Verify 4 lenses produce valid scores**

```bash
python -c "
from src.domain.lenses import BALANCED, EASY_WIN, GBP_BLITZ, AI_PROOF
for lens in [BALANCED, EASY_WIN, GBP_BLITZ, AI_PROOF]:
    total = sum(lens.weights.values())
    print(f'{lens.lens_id}: weights sum = {total:.3f}')
    assert 0.90 <= total <= 1.01, f'{lens.lens_id} weights out of range'
print('All 4 functional lens weights valid.')
"
```

- [ ] **Step 6: Verify scoring function accepts weights dict**

```bash
grep -n "def compute_opportunity_score" src/scoring/composite_score.py
# Should show: component_scores: dict[str, float], weights: dict[str, float]

grep -n "def compute_scores" src/scoring/engine.py
# Should show: weights: dict[str, float] | None = None
```

- [ ] **Step 7: Commit final regression test**

```bash
git add tests/scoring/test_backward_compat.py
git commit -m "test: add lens-vs-legacy backward compatibility regression gate

Verifies BALANCED lens weights through compute_scores(weights=...)
produces identical composite score to strategy_profile='balanced'."
```

---

## Done Criteria Checklist

- [ ] `compute_opportunity_score()` accepts `component_scores: dict` + `weights: dict` (no more named params)
- [ ] `compute_scores()` accepts optional `weights: dict` (bypasses strategy_profile resolution)
- [ ] BALANCED lens produces scores identical to current `balanced` profile (regression test passes)
- [ ] 4 lenses functional with existing data: BALANCED, EASY_WIN, GBP_BLITZ, AI_PROOF
- [ ] Remaining 5 lenses (Cash Cow, Blue Ocean, Portfolio Builder, Expand & Conquer, Seasonal Arbitrage) are defined but not yet functional (reference signals from Phase 7)
- [ ] Legacy `strategy_profile` strings map to lenses via `resolve_lens()`
- [ ] `score_market()` bridges domain Market + ScoringLens to engine
- [ ] All tests pass, ruff clean
- [ ] API contract unchanged (orchestrator still accepts strategy_profile)

## Phase 3 Integration (after merging PR #31)

Once PR #31 is merged into `dev`, two additional wiring changes enable the full lens flow through the API:

1. **MarketService.score()** — resolve `strategy_profile` to a `ScoringLens` via `resolve_lens()`, pass `lens.weights` to the pipeline instead of `strategy_profile` string
2. **Orchestrator `score_niche_for_metro()`** — accept optional `weights: dict` param, pass through to `compute_scores(weights=...)`

These are 1-task additions once the Phase 3 branch is in the dev base. The core Phase 4 work (Tasks 1-8 above) is independent and can execute on the current dev branch.
