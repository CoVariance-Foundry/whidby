# TanStack Migration — Baseline Audit

## apps/app (Consumer)

### Client Fetch Hotspots

| Surface | File | Endpoint / Data | Pattern | State on Nav |
|---------|------|-----------------|---------|--------------|
| Niche scoring | `src/app/(protected)/niche-finder/NicheFinderClient.tsx` | `POST /api/agent/scoring` | useState discriminated union (idle/loading/error/success) | **Ephemeral** |
| Metro suggest | `src/lib/niche-finder/metro-suggest.ts` → `CityAutocomplete` | `GET /api/agent/metros/suggest` | Debounced fetch + AbortController | **Ephemeral** |
| Report detail | `src/app/(protected)/reports/ReportsPageClient.tsx` | Supabase `.from("reports").select()` | Modal loading/open/error states | **Ephemeral** |
| Report delete | Same file | Supabase `.from("reports").delete()` | Optimistic local filter of rows | Client-only |
| Auth (login) | `src/app/login/page.tsx` | `signInWithPassword` | Not a Query target | Cookie-persisted |

### Persistence (localStorage)

| Module | Key | Used By |
|--------|-----|---------|
| `history-storage.ts` | `widby.niche.recent` | NicheFinderClient (recent searches) |
| `history-storage.ts` | `widby.niche.pinned` | Unused in UI currently |

### Migration Priority

1. **NicheFinderClient** scoring → `useMutation` (preserves result across nav)
2. **Metro suggest** → `useQuery` with debounce (cancel-on-retype)
3. **ReportsPageClient** detail fetch → `useQuery` by report ID
4. **ReportsPageClient** delete → `useMutation` + invalidation

---

## apps/admin (Research Dashboard)

### Client Fetch Hotspots

| Surface | File | Endpoint | Pattern | State on Nav |
|---------|------|----------|---------|--------------|
| Niche scoring | `(protected)/page.tsx` | `POST /api/agent/scoring` | useState loading/result/error | **Ephemeral** |
| Exploration | `(protected)/exploration/page.tsx` | `POST /api/agent/exploration` | Same pattern | **Ephemeral** |
| Assistant chat | `components/niche-finder/ExplorationAssistantPanel.tsx` | `POST /api/agent/exploration-chat` | Single response state | **Ephemeral** |
| Dashboard | `(protected)/dashboard/page.tsx` | `GET /api/agent/sessions` | useEffect on mount | **Ephemeral** |
| Recommendations | `(protected)/recommendations/page.tsx` | `GET sessions` + N× `GET sessions/{id}` | useEffect on mount | **Ephemeral** |
| Graph | `(protected)/graph/page.tsx` | `GET /api/agent/graph` | useEffect on mount | **Ephemeral** |
| Experiments | `(protected)/experiments/page.tsx` | `GET sessions` + `GET experiments/{id}` | useEffect + dep change | **Ephemeral** |
| Chat | `(protected)/chat/page.tsx` | `POST /api/agent/chat` + `POST sessions` | Message append pattern | **Ephemeral** |
| Metro suggest | `components/niche-finder/CityAutocomplete.tsx` | `GET /api/agent/metros/suggest` | Debounce + abort | **Ephemeral** |

### Persistence (localStorage)

| Module | Key | Used By |
|--------|-----|---------|
| `session-context.ts` | `widby:niche-query-context` | Home page, Exploration page |

### Shared Query Keys (deduplication opportunity)

- `['agent','sessions']` — used by dashboard, recommendations, experiments
- `['agent','session', runId]` — used by recommendations detail
- `['agent','graph']` — graph page
- `['agent','experiments', runId]` — experiments page

### Migration Priority

1. **Home page** scoring → `useMutation`
2. **Exploration** scoring → `useMutation`
3. **Sessions list** → shared `useQuery` (dashboard/recommendations/experiments)
4. **Graph** → `useQuery`
5. **Experiments detail** → `useQuery` keyed by runId
6. **Chat** → `useMutation` (append pattern, no cache)
