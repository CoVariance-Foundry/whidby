# Contract: Niche Finder Dual-Surface UI

**Date**: 2026-04-06

## Overview

This contract defines the user-facing interaction and response expectations for:
1) Standard Niche Finder surface, and
2) Exploration surface with score evidence.

Both surfaces must operate on the same query normalization and scoring path for parity.

## Input Contract

### Query Submission

```json
{
  "city": "string (required)",
  "service": "string (required)"
}
```

### Validation Rules

- `city` and `service` are required and trimmed.
- Empty or whitespace-only values are rejected with corrective guidance.
- Normalized query values are used for both surfaces.

## Output Contract

### Standard Surface Response

```json
{
  "query": {
    "city": "string",
    "service": "string"
  },
  "score_result": {
    "opportunity_score": "number",
    "classification_label": "string"
  },
  "status": "success | validation_error | unavailable"
}
```

### Exploration Surface Response

```json
{
  "query": {
    "city": "string",
    "service": "string"
  },
  "score_result": {
    "opportunity_score": "number",
    "classification_label": "string"
  },
  "evidence": [
    {
      "category": "string",
      "label": "string",
      "value": "string | number | boolean",
      "source": "string",
      "is_available": "boolean"
    }
  ],
  "status": "success | partial_evidence | validation_error | unavailable"
}
```

## Behavioral Guarantees

- For equivalent normalized city/service inputs, `opportunity_score` must match between standard and exploration responses.
- Exploration responses must include evidence sections when evidence is available.
- Missing evidence must be explicitly marked (`is_available=false`) rather than silently omitted.
- Error states must return user-readable messages and next steps.

## Acceptance Checks

1. Submit valid input to both surfaces and verify score parity.
2. Submit invalid input and verify validation feedback appears on both surfaces.
3. Simulate partial evidence and verify exploration response includes explicit missing markers.
