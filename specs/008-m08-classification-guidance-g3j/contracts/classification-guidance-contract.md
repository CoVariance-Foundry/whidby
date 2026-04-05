# Contract: M8 Classification + Guidance Interface

## Purpose

Define the interface between M6/M7 outputs and M9/reporting consumers for M8 classification and guidance.

## Input Contract

### `classify_and_generate_guidance(classification_input, llm_client)`

#### Required Inputs

- `classification_input`:
  - one metro classification envelope with niche and metro context
  - M6-derived signal fields required by Algo §8.1 and §8.2
  - M7-derived competition scores required by Algo §8.3
  - `strategy_profile` for consistent difficulty weighting
- `llm_client`:
  - existing M3-compatible client interface used for bounded guidance generation

#### Validation Requirements

- fail fast on missing required top-level input structures
- fail fast on missing required numeric fields for archetype/exposure/tier logic
- coerce/normalize known nullable optional context fields used by templates

## Output Contract

Returns one `ClassificationGuidanceBundle` with this shape:

```text
{
  "serp_archetype": "AGGREGATOR_DOMINATED|LOCAL_PACK_FORTIFIED|LOCAL_PACK_ESTABLISHED|LOCAL_PACK_VULNERABLE|FRAGMENTED_WEAK|FRAGMENTED_COMPETITIVE|BARREN|MIXED",
  "ai_exposure": "AI_SHIELDED|AI_MINIMAL|AI_MODERATE|AI_EXPOSED",
  "difficulty_tier": "EASY|MODERATE|HARD|VERY_HARD",
  "guidance": {
    "headline": "<string>",
    "strategy": "<string>",
    "priority_actions": ["<string>", "<string>", "..."],
    "ai_resilience_note": "<string|null>",
    "guidance_status": "generated|fallback_template"
  },
  "metadata": {
    "serp_rule_id": "<string>",
    "difficulty_inputs": {
      "organic_competition": "<number>",
      "local_competition": "<number>",
      "resolved_weights": {"organic": "<number>", "local": "<number>"}
    },
    "guidance_fallback_reason": "<string|null>"
  }
}
```

## Behavioral Guarantees

- exactly one valid enum is emitted for archetype, exposure, and difficulty tier
- deterministic classifications from identical inputs produce identical enum outputs
- difficulty tier derives from M7 competition values using strategy-profile-consistent weighting
- guidance content remains aligned with classification outputs
- guidance object is always present, even when LLM generation fails

## Error Handling Contract

- invalid or incomplete classification inputs raise structured validation errors
- LLM timeout/failure does not block classification output; function emits `guidance_status=fallback_template`
- no score recomputation occurs inside M8; M6/M7 values are treated as authoritative inputs
