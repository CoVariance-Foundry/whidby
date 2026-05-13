# Cursor Agent Instructions

## Documentation Lookup Order

1. **Canonical docs** (`docs-canonical/`) — architecture, requirements, data model, test spec, environment
2. **Spec-Kit artifacts** (`specs/`, `.specify/`) — per-feature spec/plan/tasks
3. **Detailed reference docs** (`docs/`) — algo spec, product breakdown, data flow, experiment spec
4. **Constitution** (`.specify/memory/constitution.md`) — non-negotiable engineering principles

## Spec-Kit Workflow

All remaining module work (M4-M15, M16 page increments) MUST use the spec-kit lifecycle. Use the slash commands in `.cursor/commands/speckit.*.md`.

### Before Writing Code

1. Read `docs-canonical/ARCHITECTURE.md` for module boundaries and dependencies
2. Read `docs-canonical/REQUIREMENTS.md` for requirements relevant to the module
3. Read the detailed module spec in `docs/product_breakdown.md` for I/O contracts
4. Check `docs-canonical/ARCHITECTURE.md` dependency matrix to verify prerequisites are complete
5. Run `/speckit.specify` to create the feature spec artifact
6. Run `/speckit.clarify` to resolve ambiguities
7. Run `/speckit.plan` to create the technical plan
8. Run `/speckit.tasks` to generate the task breakdown

### When Writing Code

1. Implement first, then add boundary tests for module entry points and targeted tests for complex pure logic
2. Boundary and unit tests go in `tests/unit/test_{module}.py` (no network, no API keys)
3. Integration tests go in `tests/integration/test_{module}_integration.py` with `@pytest.mark.integration`
4. All Python code must pass `ruff check`
5. All TypeScript/JS must pass `npm run lint`
6. Type annotations required on all functions
7. Google-style docstrings on all public functions

### After Writing Code

1. Run `pytest tests/unit/ -v` and verify all pass
2. Run `ruff check src/ tests/` and fix any issues
3. Update canonical docs if module interfaces changed:
   - `docs-canonical/ARCHITECTURE.md` for dependency or structure changes
   - `docs-canonical/REQUIREMENTS.md` for requirement changes
   - `docs-canonical/DATA-MODEL.md` for data shape changes
   - `docs-canonical/TEST-SPEC.md` for new test obligations
4. Update detailed reference docs if needed:
   - `docs/product_breakdown.md` for I/O contract changes
   - `docs/module_dependency.md` for dependency changes
   - `docs/data_flow.md` for data shape changes

## Constitution

The project constitution is at `.specify/memory/constitution.md`. It defines non-negotiable principles including spec-driven development, module-boundary testing, module-first architecture, and the "no framework for V1" rule.

## Key References

| Document | Path | Type |
|----------|------|------|
| Architecture | `docs-canonical/ARCHITECTURE.md` | Canonical |
| Requirements | `docs-canonical/REQUIREMENTS.md` | Canonical |
| Data Model | `docs-canonical/DATA-MODEL.md` | Canonical |
| Test Spec | `docs-canonical/TEST-SPEC.md` | Canonical |
| Environment | `docs-canonical/ENVIRONMENT.md` | Canonical |
| Product Breakdown | `docs/product_breakdown.md` | Reference |
| Algo Spec V1.1 | `docs/algo_spec_v1_1.md` | Reference |
| Module Dependencies | `docs/module_dependency.md` | Reference |
| Data Flow | `docs/data_flow.md` | Reference |
| Outreach Experiment | `docs/outreach_experiment.md` | Reference |
| Spec Workflow Guide | `docs/spec_workflow_guide.md` | Reference |
| Constitution | `.specify/memory/constitution.md` | Governance |
