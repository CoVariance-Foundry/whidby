# Cursor Agent Instructions

## Spec-Kit Workflow

All remaining module work (M4-M15, M16 page increments) MUST use the spec-kit lifecycle. Use the slash commands in `.cursor/commands/speckit.*.md`.

### Before Writing Code

1. Read the relevant module spec in `docs/product_breakdown.md`
2. Read the algo/experiment spec section referenced in the module
3. Check `docs/module_dependency.md` to verify prerequisites are complete
4. Run `/speckit.specify` to create the feature spec artifact
5. Run `/speckit.clarify` to resolve ambiguities
6. Run `/speckit.plan` to create the technical plan
7. Run `/speckit.tasks` to generate the task breakdown

### When Writing Code

1. Follow TDD: write tests first, confirm they fail, then implement
2. Unit tests go in `tests/unit/test_{module}.py` (no network, no API keys)
3. Integration tests go in `tests/integration/test_{module}_integration.py` with `@pytest.mark.integration`
4. All Python code must pass `ruff check`
5. All TypeScript/JS must pass `npm run lint`
6. Type annotations required on all functions
7. Google-style docstrings on all public functions

### After Writing Code

1. Run `pytest tests/unit/ -v` and verify all pass
2. Run `ruff check src/ tests/` and fix any issues
3. Update architecture docs if module interfaces changed:
   - `docs/product_breakdown.md` for I/O contract changes
   - `docs/module_dependency.md` for dependency changes
   - `docs/data_flow.md` for data shape changes

## Constitution

The project constitution is at `.specify/memory/constitution.md`. It defines non-negotiable principles including TDD, module-first architecture, and the "no framework for V1" rule.

## Key References

| Document | Path |
|----------|------|
| Product Breakdown | `docs/product_breakdown.md` |
| Algo Spec V1.1 | `docs/algo_spec_v1_1.md` |
| Outreach Experiment | `docs/outreach_experiment.md` |
| Module Dependencies | `docs/module_dependency.md` |
| Data Flow | `docs/data_flow.md` |
| Spec Workflow Guide | `docs/spec_workflow_guide.md` |
| Constitution | `.specify/memory/constitution.md` |
