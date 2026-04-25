# Widby Niche Finder: Autocomplete → Report System Architecture

## End-to-End Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           DOMAIN LAYER                                          │
│                                                                                 │
│  User Intent: "I want to score 'dental implants' in 'Phoenix, AZ'"            │
│                                                                                 │
│  Two-phase interaction:                                                         │
│    Phase 1 — AUTOCOMPLETE: User types city → system resolves to geocoded place │
│    Phase 2 — SCORING:      User submits (niche + city) → full pipeline run     │
└─────────────────────────────────────────────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════════════════════
  PHASE 1: AUTOCOMPLETE (city resolution + DFS location code bridging)
═══════════════════════════════════════════════════════════════════════════════════

┌──────────────────────────────────────────────────────┐
│  FRONTEND · React (apps/app/ or apps/admin/)         │
│                                                      │
│  CityAutocomplete.tsx                                │
│  ┌────────────────────────────────────────────────┐  │
│  │  User types: "phoe"                            │  │
│  │  Debounce: 250ms, min 2 chars                  │  │
│  │  → fetchPlaceSuggestions(q="phoe", limit=8)    │  │
│  └────────────────┬───────────────────────────────┘  │
│                   │                                  │
│  place-suggest.ts │                                  │
│  ┌────────────────▼───────────────────────────────┐  │
│  │  GET /api/agent/places/suggest?q=phoe&limit=8  │  │
│  │  Fallback: /api/agent/metros/suggest (legacy)  │  │
│  └────────────────┬───────────────────────────────┘  │
└───────────────────┼──────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────────┐
│  NEXT.JS PROXY LAYER                                 │
│  /api/agent/places/suggest/route.ts                  │
│                                                      │
│  ┌────────────────────────────────────────────────┐  │
│  │  Validates: q ≥ 2 chars, limit 1–20            │  │
│  │  Forwards to: NEXT_PUBLIC_API_URL              │  │
│  │     (Render: https://whidby-1.onrender.com)    │  │
│  │     (Local:  http://localhost:8000)             │  │
│  └────────────────┬───────────────────────────────┘  │
└───────────────────┼──────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  FASTAPI · GET /api/places/suggest        (src/research_agent/api.py)       │
│                                                                              │
│  ┌─── Step 1: Mapbox Geocoding ───────────────────────────────────────────┐  │
│  │  fetch_mapbox_place_suggestions()  (src/research_agent/places.py)      │  │
│  │                                                                        │  │
│  │  API: api.mapbox.com/search/geocode/v6/forward                        │  │
│  │  Params: {q, types=place, autocomplete=true, limit}                   │  │
│  │                                                                        │  │
│  │  Returns per feature:                                                  │  │
│  │    {place_id, city, region, country, lat, lon}                        │  │
│  └────────────────────────────────────────┬───────────────────────────────┘  │
│                                           │                                  │
│  ┌─── Step 2: DFS Location Bridging ─────▼───────────────────────────────┐  │
│  │  DataForSEOLocationBridge.enrich(suggestions)                          │  │
│  │                                                                        │  │
│  │  ┌──────────────────────────────────────────────────────────────────┐  │  │
│  │  │  For each PlaceSuggestion:                                      │  │  │
│  │  │    1. Normalize city name (lowercase, alphanumeric)             │  │  │
│  │  │    2. Search ~95k DFS location rows                             │  │  │
│  │  │    3. Score matches:                                            │  │  │
│  │  │       • Exact city + state match → score 110 (high confidence)  │  │  │
│  │  │       • Exact city match         → score 100 (high confidence)  │  │  │
│  │  │       • City substring           → score  75 (medium)          │  │  │
│  │  │       • Name substring           → score  55 (low → code=null) │  │  │
│  │  │    4. Attach: dataforseo_location_code + match_confidence       │  │  │
│  │  └──────────────────────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────┬───────────────────────────────┘  │
│                                           │                                  │
│  Response: PlaceSuggestion[]              │                                  │
│  ┌────────────────────────────────────────▼───────────────────────────────┐  │
│  │  [{                                                                    │  │
│  │     place_id: "mapbox.place_xyz",                                     │  │
│  │     city: "Phoenix",                                                   │  │
│  │     region: "AZ",                                                      │  │
│  │     country: "United States",                                          │  │
│  │     dataforseo_location_code: 2840,    ← bridged                      │  │
│  │     dataforseo_match_confidence: "high"                                │  │
│  │  }, ...]                                                               │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼ (response bubbles back up)
┌──────────────────────────────────────────────────────┐
│  FRONTEND · CityAutocomplete dropdown                │
│                                                      │
│  ┌────────────────────────────────────────────────┐  │
│  │  ┌──────────────────────────────────────────┐  │  │
│  │  │ ▸ Phoenix, AZ, United States             │  │  │
│  │  │   Scottsdale, AZ, United States          │  │  │
│  │  │   Phoenix, OR, United States             │  │  │
│  │  └──────────────────────────────────────────┘  │  │
│  │                                                │  │
│  │  User selects "Phoenix, AZ"                    │  │
│  │  → onChange(city="Phoenix", suggestion={        │  │
│  │       place_id, region:"AZ", dfs_code:2840     │  │
│  │    })                                          │  │
│  │  → Parent form captures all metadata           │  │
│  └────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════════════════════
  PHASE 2: SCORING (niche + city → pipeline → report)
═══════════════════════════════════════════════════════════════════════════════════

┌──────────────────────────────────────────────────────┐
│  FRONTEND · StandardNicheForm                        │
│                                                      │
│  Form state (NicheQueryInput):                       │
│  ┌────────────────────────────────────────────────┐  │
│  │  city: "Phoenix"                               │  │
│  │  service: "dental implants"                    │  │
│  │  state: "AZ"             ← from autocomplete   │  │
│  │  place_id: "mapbox.xyz"  ← from autocomplete   │  │
│  │  dataforseo_location_code: 2840  ← bridged     │  │
│  └────────────────┬───────────────────────────────┘  │
│                   │ POST /api/agent/scoring           │
└───────────────────┼──────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────────┐
│  NEXT.JS PROXY · /api/agent/scoring/route.ts         │
│                                                      │
│  ┌────────────────────────────────────────────────┐  │
│  │  validateNicheQueryInput(body)                  │  │
│  │  Maps to FastAPI payload:                       │  │
│  │    {                                            │  │
│  │      niche: "dental implants",                  │  │
│  │      city: "Phoenix",                           │  │
│  │      state: "AZ",                               │  │
│  │      place_id: "mapbox.xyz",                    │  │
│  │      dataforseo_location_code: 2840,            │  │
│  │      strategy_profile: "balanced",              │  │
│  │      dry_run: false                             │  │
│  │    }                                            │  │
│  └────────────────┬───────────────────────────────┘  │
└───────────────────┼──────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  FASTAPI · POST /api/niches/score         (src/research_agent/api.py)       │
│                                                                              │
│  ┌─── Step 0: Canonical Key ─────────────────────────────────────────────┐  │
│  │  resolve_canonical_key(niche, city, state, place_id, dfs_code)        │  │
│  │  → Normalizes: "dental implants" + "phoenix, az"                      │  │
│  │  → SHA256 hash for deduplication                                      │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌─── Step 1: Metro Resolution ──────────────────────────────────────────┐  │
│  │                                                                        │  │
│  │  ┌─ Branch A: Explicit DFS code (from autocomplete bridge) ─────────┐ │  │
│  │  │  dataforseo_location_code=2840                                    │ │  │
│  │  │  → Synthetic Metro {                                              │ │  │
│  │  │      cbsa_code: "mapbox:mapbox.xyz",                              │ │  │
│  │  │      cbsa_name: "Phoenix, AZ",                                    │ │  │
│  │  │      dataforseo_location_codes: [2840]                            │ │  │
│  │  │    }                                                              │ │  │
│  │  │  → BYPASSES MetroDB seed entirely                                 │ │  │
│  │  └──────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                        │  │
│  │  ┌─ Branch B: City found in MetroDB seed ───────────────────────────┐ │  │
│  │  │  MetroDB.find_by_city("Phoenix", state="AZ")                     │ │  │
│  │  │  → Seeded Metro with pre-configured DFS codes                    │ │  │
│  │  └──────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                        │  │
│  │  ┌─ Branch C: State-level fallback ─────────────────────────────────┐ │  │
│  │  │  City not in seed, but state="AZ" provided                       │ │  │
│  │  │  → Find highest-population AZ metro as DFS code donor            │ │  │
│  │  └──────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                        │  │
│  │  ┌─ Branch D: No match ─────────────────────────────────────────────┐ │  │
│  │  │  → ValueError("no CBSA match")                                   │ │  │
│  │  └──────────────────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌─── Steps 2–7: Scoring Pipeline (M4 → M9) ────────────────────────────┐  │
│  │                                                                        │  │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────┐  │  │
│  │  │ M4: Keyword   │    │ M5: Data     │    │ M6: Signal              │  │  │
│  │  │ Expansion     │───▸│ Collection   │───▸│ Extraction              │  │  │
│  │  │               │    │              │    │                          │  │  │
│  │  │ LLM + DFS     │    │ SERP, Maps,  │    │ 5 signal categories:    │  │  │
│  │  │ expand niche   │    │ Keywords,    │    │ • demand                │  │  │
│  │  │ into T1/T2/T3  │    │ Backlinks,   │    │ • organic_competition   │  │  │
│  │  │ keywords       │    │ Reviews,     │    │ • local_competition     │  │  │
│  │  │               │    │ GBP, etc.    │    │ • ai_resilience         │  │  │
│  │  │ ~10-30 terms   │    │              │    │ • monetization          │  │  │
│  │  └──────────────┘    └──────────────┘    └──────────┬───────────────┘  │  │
│  │                                                      │                  │  │
│  │                                                      ▼                  │  │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────┐  │  │
│  │  │ M9: Report   │    │ M8: Classify │    │ M7: Scoring             │  │  │
│  │  │ Assembly     │◂───│ + Guidance   │◂───│ Engine                  │  │  │
│  │  │              │    │              │    │                          │  │  │
│  │  │ Final report  │    │ AI exposure   │    │ Per-category scores     │  │  │
│  │  │ document with │    │ SERP archetype│    │ (0–100) + composite     │  │  │
│  │  │ all scores,   │    │ Difficulty    │    │ opportunity score       │  │  │
│  │  │ signals,      │    │ LLM guidance  │    │                          │  │  │
│  │  │ guidance      │    │              │    │ Strategy weights applied │  │  │
│  │  └──────┬───────┘    └──────────────┘    │ (balanced/aggressive/    │  │  │
│  │         │                                 │  conservative)           │  │  │
│  │         │                                 └──────────────────────────┘  │  │
│  └─────────┼─────────────────────────────────────────────────────────────┘  │
│            │                                                                 │
│  ┌─────────▼─────────────────────────────────────────────────────────────┐  │
│  │  Step 8: Persistence                                                   │  │
│  │                                                                        │  │
│  │  SupabasePersistence.persist_report()                                  │  │
│  │  ┌────────────────────────────────────────────────────────────────┐    │  │
│  │  │  reports           → 1 row (report_id, niche, geo, meta)      │    │  │
│  │  │  report_keywords   → N rows (keyword, tier, intent, volume)   │    │  │
│  │  │  metro_signals     → 1 row (5 JSONB signal bundles)           │    │  │
│  │  │  metro_scores      → 1 row (6 scores + classification)       │    │  │
│  │  └────────────────────────────────────────────────────────────────┘    │  │
│  │                                                                        │  │
│  │  KBPersistence (Knowledge Base)                                        │  │
│  │  ┌────────────────────────────────────────────────────────────────┐    │  │
│  │  │  upsert_entity    → canonical key entity (dedup by niche+geo) │    │  │
│  │  │  create_snapshot   → versioned report snapshot                 │    │  │
│  │  │  store_evidence    → signal bundles + keyword expansion        │    │  │
│  │  └────────────────────────────────────────────────────────────────┘    │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  Response:                                                                   │
│  ┌───────────────────────────────────────────────────────────────────────┐   │
│  │  {                                                                    │   │
│  │    report_id: "uuid",                                                │   │
│  │    opportunity_score: 72,                                            │   │
│  │    classification_label: "High",                                     │   │
│  │    evidence: [{category, label, value, source}, ...],                │   │
│  │    report: { ... full M9 report ... },                               │   │
│  │    entity_id, snapshot_id, persist_warning                           │   │
│  │  }                                                                    │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼ (response returns through proxy)
┌──────────────────────────────────────────────────────┐
│  FRONTEND · Score Result Display                     │
│                                                      │
│  ┌────────────────────────────────────────────────┐  │
│  │  Opportunity Score: 72/100  [HIGH]             │  │
│  │  Demand: 85  |  Competition: 62  |  AI: 71    │  │
│  │  Archetype: local_service                      │  │
│  │  Difficulty: growing                           │  │
│  │                                                │  │
│  │  → View Full Report (/reports/{report_id})     │  │
│  │    (fetches from Supabase via GET endpoint)    │  │
│  └────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════════════════════
  LAYER ARCHITECTURE
═══════════════════════════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  ╔═══════════════════════════════════════════════════════════════════════╗   │
│  ║  FRONTEND LAYER  (Next.js 16 / React)                               ║   │
│  ║                                                                      ║   │
│  ║  apps/app/ (port 3002)          apps/admin/ (port 3001)             ║   │
│  ║  Consumer product               Research dashboard                   ║   │
│  ║  Light academic theme           Dark theme                           ║   │
│  ║                                                                      ║   │
│  ║  Shared patterns:                                                    ║   │
│  ║  • CityAutocomplete component (debounced Mapbox autocomplete)       ║   │
│  ║  • NicheQueryInput type (city + service + metadata)                 ║   │
│  ║  • API proxy routes (/api/agent/*)                                  ║   │
│  ║  • Auth via Supabase signInWithPassword                             ║   │
│  ╚════════════════════════════════════╤══════════════════════════════════╝   │
│                                       │                                     │
│                    NEXT_PUBLIC_API_URL │  (snake_case JSON)                  │
│                                       │                                     │
│  ╔════════════════════════════════════╧══════════════════════════════════╗   │
│  ║  API LAYER  (FastAPI / Python 3.11+)                                 ║   │
│  ║  src/research_agent/api.py                                           ║   │
│  ║                                                                      ║   │
│  ║  Endpoints:                                                          ║   │
│  ║  • GET  /api/places/suggest  — Mapbox + DFS bridge                  ║   │
│  ║  • GET  /api/metros/suggest  — Legacy CBSA seed lookup              ║   │
│  ║  • POST /api/niches/score    — Full scoring pipeline                ║   │
│  ║  • GET  /api/niches/{id}     — Read stored report                   ║   │
│  ║                                                                      ║   │
│  ║  Deployed: Render (whidby-1.onrender.com)                           ║   │
│  ╚════════════════════════════════════╤══════════════════════════════════╝   │
│                                       │                                     │
│  ╔════════════════════════════════════╧══════════════════════════════════╗   │
│  ║  DOMAIN LAYER  (Python modules M0–M9)                                ║   │
│  ║                                                                      ║   │
│  ║  Orchestrator: src/pipeline/orchestrator.py                          ║   │
│  ║    score_niche_for_metro() composes:                                 ║   │
│  ║                                                                      ║   │
│  ║  ┌─────────┐  ┌──────────┐  ┌──────────┐                           ║   │
│  ║  │ M0: DFS │  │ M1: Metro│  │ M3: LLM  │   Foundation              ║   │
│  ║  │ Client  │  │ DB       │  │ Client   │                            ║   │
│  ║  └────┬────┘  └────┬─────┘  └────┬─────┘                           ║   │
│  ║       │            │             │                                   ║   │
│  ║  ┌────▼────┐  ┌────▼─────┐  ┌───▼──────┐                           ║   │
│  ║  │ M4:     │  │ M5: Data │  │ M6:      │   Pipeline                 ║   │
│  ║  │ Keyword │─▸│ Collect  │─▸│ Signal   │                            ║   │
│  ║  │ Expand  │  │          │  │ Extract  │                            ║   │
│  ║  └─────────┘  └──────────┘  └───┬──────┘                           ║   │
│  ║                                  │                                   ║   │
│  ║  ┌─────────┐  ┌──────────┐  ┌───▼──────┐                           ║   │
│  ║  │ M9:     │  │ M8:      │  │ M7:      │   Scoring + Output         ║   │
│  ║  │ Report  │◂─│ Classify │◂─│ Score    │                            ║   │
│  ║  │ Assembly│  │ +Guidance │  │ Engine   │                            ║   │
│  ║  └─────────┘  └──────────┘  └──────────┘                           ║   │
│  ║                                                                      ║   │
│  ║  Design: Pure functions, no side effects, deterministic pipeline     ║   │
│  ║  No agent frameworks — LLM is a utility, not an orchestrator        ║   │
│  ╚════════════════════════════════════╤══════════════════════════════════╝   │
│                                       │                                     │
│  ╔════════════════════════════════════╧══════════════════════════════════╗   │
│  ║  INFRASTRUCTURE LAYER                                                ║   │
│  ║                                                                      ║   │
│  ║  ┌─ Supabase (PostgreSQL + Auth) ─────────────────────────────────┐  ║   │
│  ║  │  Tables: reports, report_keywords, metro_signals, metro_scores │  ║   │
│  ║  │  KB: entities, snapshots, evidence                             │  ║   │
│  ║  │  Auth: email+password (signInWithPassword)                     │  ║   │
│  ║  │  RLS: authenticated→SELECT, service_role→INSERT                │  ║   │
│  ║  └────────────────────────────────────────────────────────────────┘  ║   │
│  ║                                                                      ║   │
│  ║  ┌─ External APIs ───────────────────────────────────────────────┐   ║   │
│  ║  │  Mapbox Geocoding v6 — city autocomplete + coordinates        │   ║   │
│  ║  │  DataForSEO — SERP, keywords, backlinks, reviews, GBP, etc.  │   ║   │
│  ║  │  Anthropic Claude — keyword expansion (M4) + guidance (M8)    │   ║   │
│  ║  └──────────────────────────────────────────────────────────────┘   ║   │
│  ║                                                                      ║   │
│  ║  ┌─ Deployment ──────────────────────────────────────────────────┐   ║   │
│  ║  │  Vercel — apps/app + apps/admin (auto-deploy from main)      │   ║   │
│  ║  │  Render — FastAPI backend (whidby-1.onrender.com)            │   ║   │
│  ║  └──────────────────────────────────────────────────────────────┘   ║   │
│  ╚══════════════════════════════════════════════════════════════════════╝   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════════════════════
  KEY DATA SHAPES AT BOUNDARIES
═══════════════════════════════════════════════════════════════════════════════════

  Mapbox Feature ──normalize──▸ PlaceSuggestion ──DFS bridge──▸ PlaceSuggestion+code
  ╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌

  Mapbox raw:                     Normalized:                  Enriched:
  {                               {                            {
    id: "mapbox.place_xyz",         place_id: "mapbox.xyz",      place_id: "mapbox.xyz",
    properties: {                   city: "Phoenix",             city: "Phoenix",
      name: "Phoenix",             region: "AZ",                region: "AZ",
      context: {                   country: "United States"      country: "United States",
        region: { code: "US-AZ" }  }                            dataforseo_location_code: 2840,
      }                                                          dataforseo_match_confidence: "high"
    }                                                           }
  }

  PlaceSuggestion ──user selects──▸ NicheQueryInput ──proxy──▸ NicheScoreRequest
  ╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌

  Frontend form:                   Next.js maps to:
  {                                {
    city: "Phoenix",                 niche: "dental implants",
    service: "dental implants",      city: "Phoenix",
    state: "AZ",                     state: "AZ",
    place_id: "mapbox.xyz",          place_id: "mapbox.xyz",
    dataforseo_location_code: 2840   dataforseo_location_code: 2840,
  }                                  strategy_profile: "balanced",
                                     dry_run: false
                                   }

  M9 Report ──persist──▸ Supabase (4 tables)
  ╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌

  reports          ← 1 row: report_id, niche_keyword, geo_target, meta (JSONB)
  report_keywords  ← N rows: keyword, tier, intent, search_volume, cpc
  metro_signals    ← 1 row: demand/organic/local/ai/monetization (each JSONB)
  metro_scores     ← 1 row: 6 numeric scores + classification labels + guidance


═══════════════════════════════════════════════════════════════════════════════════
  CRITICAL BRIDGING INSIGHT
═══════════════════════════════════════════════════════════════════════════════════

  The autocomplete isn't just UX sugar — it's the PRIMARY mechanism for location
  code resolution. The DFS bridge in Phase 1 determines which DataForSEO location
  code gets used for ALL data collection in Phase 2.

  When a user selects a city from the dropdown:
    • place_id     → used for Metro cbsa_code (synthetic: "mapbox:place_xyz")
    • dfs_code     → used for ALL DataForSEO API calls (SERP, keywords, etc.)
    • region/state → used for fallback Metro resolution if bridge fails

  Without autocomplete (manual city entry): the system falls back to MetroDB
  seed lookup or state-level DFS code donation — less precise targeting.
