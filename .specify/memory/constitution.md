# Widby Constitution

## Core Principles

### I. Spec-Driven, Test-Driven Development (NON-NEGOTIABLE)

Every module follows a strict lifecycle: read the spec slice, write the test file first (red), implement until tests pass (green), refactor without breaking tests. No code ships without a corresponding spec artifact and passing tests. Unit tests run without API keys or network access. Integration tests are tagged `@pytest.mark.integration` and skipped in CI by default.

### II. Module-First Architecture

The product is decomposed into buildable, testable modules (M0-M16) with clear boundaries, input/output contracts, and eval criteria. Each module has its own spec slice, test suite, and optional eval frontend surface. Modules compose into the full pipeline. Dependencies between modules follow the DAG defined in `docs/module_dependency.md`.

### III. No Framework for V1 (Plain Python + Claude API)

The pipeline is 80% deterministic data processing and 20% LLM calls. We use `anthropic` Python SDK directly, `asyncio` for concurrency, plain Python functions with explicit dependency ordering, and Supabase for state. No agent orchestration frameworks (LangGraph, CrewAI, Agent SDK) for the scoring/outreach pipeline. The Research Agent layer is the sole exception where LangChain/DeepAgents are used.

### IV. Code Quality Standards

- PEP 8 conventions enforced by `ruff` (line-length 100, target Python 3.11+)
- Type annotations required for all functions and methods
- Google-style docstrings with Args/Returns/Raises sections
- Import order: standard library, third-party, local modules
- PascalCase for classes, snake_case for everything else
- Specific exception handling with logging (`exc_info=True` for exceptions)
- ESLint for all TypeScript/Next.js code in `apps/`

### V. Documentation as Code

All code changes require documentation updates. Spec artifacts (`spec.md`, `plan.md`, `tasks.md`) are mandatory deliverables alongside implementation. Architecture docs (`product_breakdown.md`, `module_dependency.md`, `data_flow.md`) must be updated when module interfaces or data flows change. Every public function has at least one unit test. Every input/output contract from the spec has a corresponding test.

### VI. Simplicity and Determinism

Start simple, follow YAGNI. The LLM is a utility called at specific points, not the orchestrator. Pipeline execution order is fixed and defined by the spec. Temperature=0 for deterministic tasks, slight creativity only where explicitly specified. Prompt templates are versioned files, not hardcoded strings.

## Technology Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Backend | Python 3.11+ | `asyncio`, `pydantic>=2`, `httpx` |
| LLM | Anthropic Python SDK | `claude-sonnet-4-20250514` default, `claude-haiku-4-5-20251001` for classification |
| Data APIs | DataForSEO | Rate limited to 2000 calls/min client-side |
| Database | Supabase | PostgreSQL + RLS + Edge Functions |
| Frontend (marketing) | Next.js 16, Tailwind v4, Vercel | `apps/web` |
| Frontend (eval) | Next.js or plain HTML | `apps/app` or standalone |
| Monorepo | Turborepo | `npm` workspaces |
| Research Agent | LangChain + DeepAgents + NetworkX | Exception to "no framework" rule |

## Development Workflow (Spec-Kit Lifecycle)

Every remaining module (M4-M15, M16 pages) follows this mandatory sequence:

1. **`/speckit.specify`** -- Define what the module does, acceptance criteria, I/O contracts
2. **`/speckit.clarify`** -- Resolve ambiguity before planning
3. **`/speckit.plan`** -- Technical implementation plan with stack specifics
4. **`/speckit.tasks`** -- TDD-first task breakdown with dependency-safe parallelism
5. **Hard Gate: Spec and Plan review** -- Artifacts must pass integrity checks
6. **`/speckit.implement`** -- Execute tasks; tests must pass before considering complete
7. **Hard Gate: CI passes** -- `ruff`, `pytest`, `eslint`, docs-sync validation
8. **Merge** -- Update cross-module docs if contracts changed

## Quality Gates (Hard)

| Gate | Scope | Blocks Merge? |
|------|-------|---------------|
| Spec artifact presence | Feature branch touches module scope | Yes |
| `ruff check` | All Python files | Yes |
| `pytest tests/unit/` | All unit tests pass | Yes |
| `npm run lint` | All TypeScript/JS in affected workspaces | Yes |
| Docs-sync validation | Architecture docs updated when interfaces change | Yes |
| Integration tests | Real API calls (`@pytest.mark.integration`) | No (advisory) |

## Test Structure

```
tests/
  unit/
    test_{module}.py           # No external calls, use fixtures/mocks
  integration/
    test_{module}_integration.py  # Real API calls, tagged @pytest.mark.integration
  fixtures/
    {module}_fixtures.py       # Shared test data, mock responses
```

Rules:
- Every public function has at least one unit test
- Every I/O contract from the spec has a corresponding test
- Use `pytest` with `pytest-asyncio` for async code
- Use `pytest-mock` for mocking external dependencies
- Fixtures live alongside tests, not buried in conftest.py

## Governance

This constitution supersedes ad-hoc practices. Amendments require:
1. A documented rationale
2. Updates to affected spec artifacts
3. Review of downstream impact on in-flight modules

All PRs must verify compliance with these principles. The spec-kit workflow is the single path for delivering new module work. Skipping steps requires explicit justification documented in the PR.

**Version**: 1.0.0 | **Ratified**: 2026-04-04 | **Last Amended**: 2026-04-04
