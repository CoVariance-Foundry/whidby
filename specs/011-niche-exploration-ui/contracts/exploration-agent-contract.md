# Contract: Exploration Assistant Tool-Use

**Date**: 2026-04-06

## Overview

This contract defines how the exploration assistant handles follow-up questions while using approved scoring/search plugin capabilities and preserving current niche query context.

## Input Contract

### Assistant Request

```json
{
  "session_id": "string (required)",
  "query_context": {
    "city": "string (required)",
    "service": "string (required)"
  },
  "question": "string (required)"
}
```

### Validation Rules

- Request must include active session and query context.
- `question` must be non-empty.
- Assistant must reject unsupported operations with a user-readable explanation.

## Tool Access Contract

- Assistant may invoke only approved existing scoring/search plugin capabilities.
- Tool executions must stay bound to active query context unless user explicitly requests a new context.
- Tool failure must not crash the session; response must degrade to `partial` or `unsupported`.

## Output Contract

```json
{
  "response_id": "string",
  "session_id": "string",
  "query_context": {
    "city": "string",
    "service": "string"
  },
  "answer": "string",
  "evidence_references": [
    {
      "category": "string",
      "reference_label": "string"
    }
  ],
  "status": "success | partial | unsupported"
}
```

## Behavioral Guarantees

- Responses must include at least one evidence reference when status is `success`.
- `partial` status must explain what evidence is missing.
- `unsupported` status must provide the next best actionable suggestion.
- Query context must remain unchanged after follow-up execution unless user intentionally changes city/service.

## Acceptance Checks

1. Ask a follow-up question after an exploration result and verify evidence-backed answer.
2. Force an unsupported question and verify actionable fallback guidance.
3. Compare query context before/after follow-up and verify it is preserved.
