# Module Dependency Graph

## Build Order (Critical Path)

```
M0 (DataForSEO Client) ──┐
M1 (Metro Database) ──────┤
M2 (Supabase Schema) ─────┼──→ M4 (Keyword Expansion) ──→ M5 (Data Collection) ──→ M6 (Signal Extraction) ──→ M7 (Scoring) ──→ M8 (Classification) ──→ M9 (Report)
M3 (LLM Client) ──────────┘                                                                                       ↑
                                                                                                                    │
                           ┌──→ M10 (Business Discovery) ──→ M11 (Site Scanning) ──→ M12 (Audit Gen) ──→ M13 (Outreach) ──→ M14 (Tracking) ──→ M15 (Analysis) ──┘
                           │                                                                                                                                         │
M0 ────────────────────────┤                                                                                                                        (rentability signal
M1 ────────────────────────┤                                                                                                                         feeds back into M7)
M3 ────────────────────────┘

M16 (Eval Frontend): scaffolded in Phase 1, pages added as each module is built
```

## Dependency Matrix

| Module | Depends On | Depended On By |
|--------|-----------|----------------|
| M0: DataForSEO Client | — | M4, M5, M10, M11 |
| M1: Metro Database | — | M5, M10 |
| M2: Supabase Schema | — | M9, M14, M15 |
| M3: LLM Client | — | M4, M8, M12, M14 |
| M4: Keyword Expansion | M0, M3 | M5 |
| M5: Data Collection | M0, M1, M4 | M6 |
| M6: Signal Extraction | M5 | M7 |
| M7: Scoring Engine | M6 | M8, M9, M15 |
| M8: Classification | M6, M7, M3 | M9 |
| M9: Report Generation | M4-M8, M2 | — |
| M10: Business Discovery | M0, M1 | M11 |
| M11: Site Scanning | M0, M10 | M12 |
| M12: Audit Generation | M3, M11 | M13 |
| M13: Outreach Delivery | M12 | M14 |
| M14: Response Tracking | M3, M13, M2 | M15 |
| M15: Experiment Analysis | M14, M2 | M7 (feedback loop) |
| M16: Eval Frontend | All modules | — |

## Research Agent Layer

```
                                    ┌──────────────────────────────────────────┐
                                    │          RESEARCH AGENT (RA)              │
                                    │                                          │
M7 (Scoring) output ──────────────→ │  RA-1: Hypothesis Generator              │
M0 (DataForSEO Client) ──────────→ │  RA-2: Experiment Planner                │
M1 (Metro Database) ──────────────→ │  RA-3: Ralph Research Loop               │
M3 (LLM Client) ─────────────────→ │  RA-4: Evaluator + Recommender           │
                                    │  RA-5: Graph Memory + Filesystem Store   │
                                    └──────────────┬───────────────────────────┘
                                                   │
                                                   ▼
                                    Recommendations → M7 parameter updates
```

| Module | Depends On | Depended On By |
|--------|-----------|----------------|
| RA-1: Hypothesis Generator | M7 output | RA-2 |
| RA-2: Experiment Planner | RA-1 | RA-3 |
| RA-3: Ralph Research Loop | RA-2, RA-4, RA-5 | — |
| RA-4: Evaluator + Recommender | RA-3 | M7 (parameter proposals) |
| RA-5: Memory (Graph + FS) | — | RA-1, RA-3, RA-4 |

See `docs/research_agent_design.md` for full architecture, loop semantics, and tool contracts.

## Parallel Build Opportunities

These modules have no dependencies on each other and can be built simultaneously:

- M0, M1, M2, M3 (all foundation — build in parallel in Week 1)
- M10-M12 can start as soon as M0 + M1 + M3 are done (don't need M4-M9)
- M8 and M9 can be built in parallel (M8 needs M6+M7, M9 needs M4-M8 but can be built alongside M8)
- RA modules can be built after M0, M1, M3 are complete (independent of M4-M9 pipeline)