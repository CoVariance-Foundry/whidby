# Research: Niche Finder Exploration Interface

**Date**: 2026-04-06  
**Branch**: `011-niche-exploration-ui`

## Research Questions

### RQ1: How should score parity be enforced between standard and exploration surfaces?

**Decision**: Both surfaces use the same normalized city/service query payload and same scoring pathway, with parity checks as a contract requirement.

**Rationale**: The feature requires users to trust that the exploration view explains the same score, not a different score. Shared normalization plus parity validation eliminates drift caused by formatting differences.

**Alternatives considered**:

- Compute scores independently per surface. Rejected: introduces score drift and erodes user trust.
- Cache and reuse only previously generated standard scores in exploration. Rejected: limits exploration flexibility and complicates stale data handling.

### RQ2: What is the minimum evidence model needed for human score validation?

**Decision**: Expose evidence in labeled categories aligned to the score dimensions and include per-response references to those categories in assistant explanations.

**Rationale**: Users need traceable rationale, not raw unstructured payload dumps. Category-level attribution balances transparency with readability.

**Alternatives considered**:

- Show full raw source payloads only. Rejected: too noisy and difficult to interpret quickly.
- Show only a narrative explanation without evidence references. Rejected: does not satisfy transparency requirements.

### RQ3: How should the exploration assistant access SERP exploration safely?

**Decision**: The assistant is constrained to existing approved scoring/search plugin capabilities and must preserve active city/service context on every follow-up query.

**Rationale**: Reusing current plugins avoids introducing new framework risk and keeps behavior aligned with existing research-agent governance and cost controls.

**Alternatives considered**:

- Introduce a new standalone exploration agent stack. Rejected: unnecessary complexity and higher maintenance.
- Allow unrestricted tool access outside scoring/search plugins. Rejected: weakens guardrails and auditability.

### RQ4: What should happen when evidence is partial or unavailable?

**Decision**: Return score when possible, clearly mark missing evidence sections, and provide actionable next-step suggestions in assistant responses.

**Rationale**: This preserves task continuity and gives users explicit awareness of confidence limitations.

**Alternatives considered**:

- Hard-fail entire exploration flow if any evidence section is missing. Rejected: overly rigid and harms usability.
- Silently hide missing evidence. Rejected: obscures limitations and undermines trust.