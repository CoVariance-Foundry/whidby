# Quickstart: Niche Finder Exploration Interface

## Goal

Validate that the dual-surface niche finder planning artifacts map cleanly to implementation and test flows before `/speckit.tasks`.

## Prerequisites

- Repository dependencies installed for Python and Node workspaces
- Environment variables configured for existing scoring and agent services
- Active branch: `011-niche-exploration-ui`

## 1) Review Planning Artifacts

1. Read `specs/011-niche-exploration-ui/spec.md`
2. Read `specs/011-niche-exploration-ui/plan.md`
3. Read `specs/011-niche-exploration-ui/research.md`
4. Read `specs/011-niche-exploration-ui/data-model.md`
5. Read both contracts under `specs/011-niche-exploration-ui/contracts/`

## 2) Confirm Implementation Surfaces

1. Confirm standard surface location in `apps/app/src/app/(protected)/page.tsx`
2. Confirm exploration flow integration points in `apps/app/src/app/api/agent/`
3. Confirm scoring and plugin capabilities in:
   - `src/scoring/engine.py`
   - `src/research_agent/plugins/scoring_plugin.py`
   - `src/research_agent/plugins/dataforseo_plugin.py`
   - `src/research_agent/agent/claude_agent.py`

## 3) Pre-Implementation Validation

Run quality gates relevant to touched code during implementation:

```bash
ruff check src tests
pytest tests/unit/ -v
npm run lint
```

## 4) Scenario Verification Targets

When implementation is complete, verify:

1. Standard surface: valid city/service -> score result
2. Exploration surface: same input -> same score + evidence sections
3. Assistant follow-up: context-preserving response with evidence references
4. Partial/unsupported handling: clear guidance without flow break

## 5) Next Step

Generate executable implementation tasks with `/speckit.tasks`.

## 6) Implementation Baseline Checklist

- [x] Shared niche-finder type contracts created
- [x] Shared request validation and query normalization utilities created
- [x] Standard scoring and exploration API proxy routes created
- [x] Standard and exploration UI entry surfaces wired
- [x] Exploration assistant follow-up route and client service wired
- [x] Exploration agent/plugin extensions added for evidence and SERP snapshot queries

## 7) Validation Run Results

- `ruff check src tests`: fails due pre-existing unrelated lint issues in untouched files; focused lint passes for changed backend files:
  - `src/research_agent/agent/claude_agent.py`
  - `src/research_agent/plugins/scoring_plugin.py`
  - `src/research_agent/plugins/dataforseo_plugin.py`
- `pytest tests/unit/test_scoring_plugin.py tests/unit/test_claude_agent.py -v`: 12 passed
- `npm run lint`: fails due pre-existing error in `apps/app/src/app/(protected)/experiments/page.tsx` (`react-hooks/set-state-in-effect`), not introduced by this feature
