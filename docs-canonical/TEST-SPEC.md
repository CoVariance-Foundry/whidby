# Test Specification

<!-- docguard:version 1.0.0 -->
<!-- docguard:status approved -->
<!-- docguard:last-reviewed 2026-04-05 -->
<!-- docguard:owner @widby-team -->

> **Canonical document** — Design intent. This file declares what tests MUST exist.

---

## Test Categories

| Category | Required | Applies To | Tools |
|----------|----------|-----------|-------|
| Unit | Yes | All pipeline/scoring/client modules | pytest, pytest-asyncio, pytest-mock |
| Integration | Yes (advisory, not CI-blocking) | Live API calls | pytest with `@pytest.mark.integration` |
| E2E | Optional | Full pipeline runs | Custom scripts |
| Contract | Yes | Module I/O boundaries | pytest (schema validation) |

## Coverage Rules

| Source Pattern | Required Test Pattern | Category |
|---------------|----------------------|----------|
| `src/clients/**/*.py` | `tests/unit/test_*.py` | Unit |
| `src/pipeline/**/*.py` | `tests/unit/test_*.py` | Unit |
| `src/scoring/**/*.py` | `tests/unit/test_*.py` | Unit |
| `src/classification/**/*.py` | `tests/unit/test_*.py` | Unit |
| `src/experiment/**/*.py` | `tests/unit/test_*.py` | Unit |
| `src/research_agent/**/*.py` | `tests/unit/test_*.py` | Unit |

## Test Rules (Constitution-Mandated)

1. Unit tests run without API keys or network access (use fixtures/mocks).
2. Integration tests are tagged `@pytest.mark.integration` and skipped in CI by default.
3. Every public function has at least one unit test.
4. Every I/O contract from the spec has a corresponding test.
5. Use `pytest` with `pytest-asyncio` for async code.
6. Use `pytest-mock` for mocking external dependencies.
7. Fixtures live alongside tests in `tests/fixtures/`, not in `conftest.py`.

## Test Structure

```
tests/
  unit/
    test_{module}.py              # No external calls, use fixtures/mocks
  integration/
    test_{module}_integration.py  # Real API calls, tagged @pytest.mark.integration
  fixtures/
    {module}_fixtures.py          # Shared test data, mock responses
```

## Service-to-Test Map

| Source File | Unit Test | Integration Test | Status |
|------------|-----------|-----------------|--------|
| `src/clients/dataforseo/client.py` | `tests/unit/test_dataforseo_client.py` | — | ✅ |
| `src/clients/llm/client.py` | `tests/unit/test_llm_client.py` | — | ✅ |
| `src/data/metro_db.py` | `tests/unit/test_metro_db.py` | — | ✅ |
| `supabase/migrations/` | `tests/unit/test_supabase_schema.py` | — | ✅ |
| `src/pipeline/keyword_expansion.py` | `tests/unit/test_keyword_expansion.py` | `tests/integration/test_keyword_expansion_integration.py` | ✅ |
| `src/pipeline/intent_classifier.py` | `tests/unit/test_intent_classifier.py` | — | ✅ |
| `src/pipeline/keyword_deduplication.py` | `tests/unit/test_keyword_deduplication.py` | — | ✅ |
| `src/research_agent/` | `tests/unit/test_research_agent_loop.py` | — | ✅ |

## Unit Test Obligations (Algo Spec §12.1)

| Test | Input | Expected |
|------|-------|----------|
| Keyword expansion produces Tier 1 terms | "plumber" | Contains "plumber near me" |
| Intent classification: transactional | "emergency plumber near me" | intent = "transactional" |
| Intent classification: informational | "how to fix a leaky faucet" | intent = "informational", excluded from SERP |
| AIO volume discount (transactional) | volume=1000, intent=transactional | effective ≈ 988 |
| AIO volume discount (informational) | volume=1000, intent=informational | effective ≈ 743 |
| Aggregator detection | SERP with yelp.com at #1 | `aggregator_count >= 1` |
| Cross-metro dedup | Same domain in 10/20 metros | Domain in `DETECTED_NATIONAL` |
| Review velocity calculation | 12 reviews in 6 months | velocity = 2.0 reviews/month |
| GBP completeness: full | All 7 signals present | score = 1.0 |
| GBP completeness: minimal | Only phone + category | score = 0.29 |
| Confidence penalty: missing review data | Metro with 0 review results | Confidence <= 90 |
| Confidence penalty: high AIO | aio_trigger_rate = 0.35 | Confidence <= 90 |
| Opportunity cap: weak component | Any score < 5 | Opportunity <= 20 |
| AI resilience hard floor | ai_resilience < 20 | Opportunity <= 50 |
| Feedback log created | Any report generation | Non-null log_id in meta |

## Integration Tests (Known Markets, Algo Spec §12.2)

| Test Case | Niche | Metro | Expected Outcome |
|-----------|-------|-------|------------------|
| Known easy market | "plumber" | Small city with weak SERPs | Opportunity > 70, Difficulty EASY |
| Known hard market | "plumber" | NYC/LA | Opportunity < 40, Difficulty HARD/VERY_HARD |
| Known aggregator market | "lawyer" | Any major metro | Archetype = AGGREGATOR_DOMINATED |
| Niche niche | "septic tank pumping" | Rural MSA | Low volume but low competition |
| AI-exposed niche | "how to" heavy niche | Any metro | AI exposure = AI_MODERATE or AI_EXPOSED |
| Review fortress | Niche with 200+ review incumbents | Major metro | Local competition score < 30 |
| GBP desert | Niche with incomplete GBP profiles | Smaller metro | Local competition score > 70 |

## Quality Gates (CI)

| Gate | Scope | Blocks Merge? |
|------|-------|---------------|
| `ruff check` | All Python files | Yes |
| `pytest tests/unit/` | All unit tests pass | Yes |
| `npm run lint` | All TypeScript/JS in affected workspaces | Yes |
| Spec artifact presence | Feature branch touches module scope | Yes |
| Docs-sync validation | Architecture docs updated when interfaces change | Yes |
| Integration tests | Real API calls (`@pytest.mark.integration`) | No (advisory) |

## Validation Commands

```bash
ruff check src tests
python -m pytest tests/unit/ -v
python -m pytest tests/unit/ --cov=src --cov-report=term-missing
python -m pytest tests/integration/ -v -m integration
npm run lint
```

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1.0 | 2026-04-05 | DocGuard Init | Initial template |
| 1.0.0 | 2026-04-05 | Migration | Populated from `docs/algo_spec_v1_1.md` §12, `docs/product_breakdown.md`, `.specify/memory/constitution.md` |
