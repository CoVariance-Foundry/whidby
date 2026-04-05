# M07 Research Notes

## Rule Mapping (Algo Spec V1.1 §7)

| Rule | Module |
|------|--------|
| Demand percentile + CPC multiplier + breadth + intent | `src/scoring/demand_score.py` |
| Organic competition inversion | `src/scoring/organic_competition_score.py` |
| Local review barrier + no-local-pack default | `src/scoring/local_competition_score.py` |
| Monetization CPC/density/active-market | `src/scoring/monetization_score.py` |
| AI resilience with AIO safety and niche-type split | `src/scoring/ai_resilience_score.py` |
| Threshold gates + AI floor + profile-aware composition | `src/scoring/composite_score.py` |
| Confidence penalties and flags | `src/scoring/confidence_score.py` |
| Strategy profiles incl. `auto` resolution | `src/scoring/strategy_profiles.py` |
| Clamp/scale/inverse/percentile helpers | `src/scoring/normalization.py` |

## Determinism Decisions

- Score functions are pure and only read their arguments.
- Cohort-relative behavior is isolated to percentile helpers.
- Constants are centralized in `src/config/constants.py`.
- `auto` profile resolves deterministically from metro signals.
