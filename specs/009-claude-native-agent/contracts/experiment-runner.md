# Contract: Experiment Runner

**Date**: 2026-04-04

## Overview

The experiment runner is a callable that the Ralph loop invokes for each hypothesis. This contract defines the input/output interface that the new Claude-native runner must satisfy.

## Type Signature

```python
ExperimentRunner = Callable[[dict[str, Any], FilesystemStore], dict[str, Any]]
```

The loop calls `experiment_runner(hypothesis, filesystem_store)` and expects a result dict.

## Input: hypothesis

Shape from `hypothesis/generator.py`:

```python
{
    "id": str,                    # 8-char UUID
    "title": str,                 # e.g. "Improve demand via keyword_expansion_tuning"
    "description": str,           # human-readable description
    "target_proxy": str,          # "demand" | "organic_competition" | "local_competition" | "monetization" | "ai_resilience" | "composite"
    "target_signals": list[str],  # signal keys this hypothesis affects
    "expected_direction": str,    # "increase" | "decrease"
    "priority": int,              # 1-5, higher = more important
    "status": str,                # "pending" | "in_progress" | "validated" | "invalidated" | "failed"
    "spec_section": str,          # algo spec reference
    "approach": str,              # e.g. "keyword_expansion_tuning", "da_ceiling_adjustment"
}
```

## Input: filesystem_store

Instance of `FilesystemStore` with methods:
- `save_experiment_result(experiment_id, result)` -> Path
- `save_snapshot(name, data)` -> Path
- `load_snapshot(name)` -> dict | None
- `save_tool_output(step, tool_name, output)` -> Path
- `append_progress(entry)` -> None

## Output: experiment result dict

**Required fields** (consumed by the loop and evaluator):

```python
{
    "experiment_id": str,         # unique identifier
    "cost_usd": float,            # total API cost (0.0 for parameter-only)
    "modifications": list[dict],  # from experiment_planner
    "candidate_scores": {
        "metros": [
            {
                "scores": {
                    "demand": float,                # 0-100
                    "organic_competition": float,   # 0-100
                    "local_competition": float,     # 0-100
                    "monetization": float,           # 0-100
                    "ai_resilience": float,          # 0-100
                    "opportunity": float,            # 0-100 (composite)
                },
                "cbsa_code": str,   # optional, for tracking
            },
            ...
        ]
    },
}
```

**Optional fields** (for auditability):

```python
{
    "plan": dict,                   # experiment plan from experiment_planner
    "tool_calls": list[dict],       # audit log of tool invocations
    "mode": str,                    # "fast" | "full"
}
```

## Evaluator Consumption

The evaluator (`evaluation/evaluator.py`) reads candidate scores via:

```python
def _extract_composites(snapshot):
    metros = snapshot.get("metros",
        snapshot.get("candidate_scores", {}).get("metros", []))
    return [m.get("scores", {}).get("opportunity", ...) for m in metros]
```

The per-proxy comparison reads `scores.demand`, `scores.organic_competition`, etc. from both baseline and candidate metro entries.

## Baseline Snapshot Shape

The runner should load baseline data via `fs.load_snapshot("baseline")`. This returns:

```python
{
    "metros": [
        {
            "cbsa_code": str,
            "cbsa_name": str,
            "scores": {"demand": float, "organic_competition": float, ...},
            "signals": {"effective_search_volume": float, ...},  # optional
        },
        ...
    ]
}
```

## Error Handling

If the experiment runner raises an exception, the loop catches it, marks the hypothesis as `"failed"`, logs the error with `exc_info=True`, appends a progress entry, and continues to the next hypothesis. The runner should only raise for unrecoverable errors; partial results should be returned with whatever data was gathered.
