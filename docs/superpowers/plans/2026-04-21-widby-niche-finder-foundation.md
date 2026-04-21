# Widby Niche Finder Foundation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the three consumer-facing pages (Home, Niche Finder command-center, Reports with archetype chip filter) on `apps/app`, matching the Widby design bundle, backed by the existing deterministic niche-scoring backend (merged from 013 + 014). Zero Claude calls — Foundation is pure deterministic product.

**Architecture:** Next.js 16 App Router on `apps/app` (port 3002). Server components for data-reading pages (`/`, `/reports`), client components for interactive pages (`/niche-finder`). Light academic theme already wired in [apps/app/src/app/globals.css](../../../apps/app/src/app/globals.css). Supabase is the SSR data source for reports; FastAPI is the scoring backend. No Claude in Foundation — agentic features wait until Phase 2 (Managed Agents) in a separate spec.

**Tech Stack:** Next.js 16 (App Router) · React 19 · TypeScript 5 · Vitest + @testing-library/react · Playwright for E2E · Tailwind v4 + custom CSS tokens · Supabase JS SDK.

**Spec reference:** [docs/superpowers/specs/2026-04-21-widby-niche-finder-v1-design.md](../specs/2026-04-21-widby-niche-finder-v1-design.md)

**Design bundle reference:** [docs/designs/widby-niche-finder-v1/project/lib/](../../designs/widby-niche-finder-v1/project/lib/) — the JSX files (`niche-home.jsx`, `niche-v-b.jsx`, `niche-reports.jsx`, `niche-shared.jsx`, `niche-strategy.jsx`) are the visual source of truth. Adapt to Next.js, don't copy the prototype's internal structure verbatim.

**Baseline (already in place on this branch):**
- `main` + 013 (backend: `POST /api/niches/score`, `GET /api/niches/{id}`, `GET /api/metros/suggest`, Supabase persistence)
- `main` + 014 (consumer: scaffolded `/niche-finder` with CityAutocomplete, `/reports` with SSR, `/recommendations` stub, RLS migration 005)
- `apps/app/src/lib/archetypes.ts` exists with the 8-archetype registry
- `apps/app/src/app/globals.css` has the academic theme tokens and archetype tint classes (`.arch-*`)
- Python 298/298 ✓ · apps/app vitest 24/24 ✓ · apps/admin vitest 35/35 ✓ · ruff ✓ · tsc ✓

---

## Phase B — Home page

Replaces the current `(protected)/page.tsx` redirect stub with the dashboard layout per `niche-home.jsx` design reference.

### Task B1: Home stat-card component

**Files:**
- Create: `apps/app/src/components/home/StatCardRow.tsx`
- Test: `apps/app/src/components/home/StatCardRow.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `apps/app/src/components/home/StatCardRow.test.tsx`:

```tsx
// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import StatCardRow from "./StatCardRow";

describe("StatCardRow", () => {
  it("renders four stats with labels and values", () => {
    render(
      <StatCardRow
        stats={[
          { label: "Niches scored", value: "42" },
          { label: "Watchlist", value: "8" },
          { label: "Avg score", value: "67" },
          { label: "Reports", value: "42" },
        ]}
      />,
    );
    expect(screen.getByText("Niches scored")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByText("Watchlist")).toBeInTheDocument();
    expect(screen.getByText("67")).toBeInTheDocument();
  });

  it("renders an optional delta below the value when provided", () => {
    render(
      <StatCardRow
        stats={[
          { label: "Reports", value: "42", delta: "+3 this week" },
        ]}
      />,
    );
    expect(screen.getByText("+3 this week")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/app && npx vitest run src/components/home/StatCardRow.test.tsx`
Expected: FAIL — `Cannot find module './StatCardRow'`

- [ ] **Step 3: Create the component**

Create `apps/app/src/components/home/StatCardRow.tsx`:

```tsx
export interface StatCard {
  label: string;
  value: string;
  delta?: string;
}

export default function StatCardRow({ stats }: { stats: StatCard[] }) {
  return (
    <div
      role="list"
      style={{
        display: "grid",
        gridTemplateColumns: `repeat(${stats.length}, minmax(0, 1fr))`,
        gap: 16,
      }}
    >
      {stats.map((stat) => (
        <div
          role="listitem"
          key={stat.label}
          style={{
            background: "var(--card)",
            border: "1px solid var(--rule)",
            borderRadius: 12,
            padding: "18px 20px",
            display: "flex",
            flexDirection: "column",
            gap: 6,
          }}
        >
          <div
            style={{
              fontFamily: "var(--sans)",
              fontSize: 11.5,
              letterSpacing: "0.06em",
              textTransform: "uppercase",
              color: "var(--ink-3)",
            }}
          >
            {stat.label}
          </div>
          <div
            style={{
              fontFamily: "var(--serif)",
              fontSize: 32,
              fontWeight: 600,
              color: "var(--ink)",
              lineHeight: 1.1,
            }}
          >
            {stat.value}
          </div>
          {stat.delta ? (
            <div
              style={{
                fontFamily: "var(--sans)",
                fontSize: 12,
                color: "var(--ink-2)",
              }}
            >
              {stat.delta}
            </div>
          ) : null}
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/app && npx vitest run src/components/home/StatCardRow.test.tsx`
Expected: PASS — 2 tests passing.

- [ ] **Step 5: Commit**

```bash
git add apps/app/src/components/home/
git commit -m "feat(app): add StatCardRow component for home dashboard

Four-card grid showing label/value/optional delta.
Uses academic theme tokens (Source Serif for values, Inter for labels)."
```

---

### Task B2: HeroQuickSearch component

**Files:**
- Create: `apps/app/src/components/home/HeroQuickSearch.tsx`
- Test: `apps/app/src/components/home/HeroQuickSearch.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `apps/app/src/components/home/HeroQuickSearch.test.tsx`:

```tsx
// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import HeroQuickSearch from "./HeroQuickSearch";

describe("HeroQuickSearch", () => {
  it("shows the prompt copy and a link to the niche finder", () => {
    render(<HeroQuickSearch />);
    expect(
      screen.getByText(/start a niche scoring run/i),
    ).toBeInTheDocument();
    const link = screen.getByRole("link", { name: /open niche finder/i });
    expect(link).toHaveAttribute("href", "/niche-finder");
  });
});
```

- [ ] **Step 2: Verify the test fails**

Run: `cd apps/app && npx vitest run src/components/home/HeroQuickSearch.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Create the component**

Create `apps/app/src/components/home/HeroQuickSearch.tsx`:

```tsx
import Link from "next/link";

export default function HeroQuickSearch() {
  return (
    <section
      aria-label="Quick search"
      style={{
        background: "var(--card)",
        border: "1px solid var(--rule)",
        borderRadius: 12,
        padding: "22px 24px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 16,
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        <div
          style={{
            fontFamily: "var(--serif)",
            fontSize: 20,
            fontWeight: 600,
            color: "var(--ink)",
          }}
        >
          Start a niche scoring run
        </div>
        <div
          style={{
            fontFamily: "var(--sans)",
            fontSize: 13.5,
            color: "var(--ink-2)",
          }}
        >
          Enter a city and service to generate an opportunity score.
        </div>
      </div>
      <Link
        href="/niche-finder"
        style={{
          fontFamily: "var(--sans)",
          fontSize: 13.5,
          fontWeight: 600,
          color: "var(--card)",
          background: "var(--accent)",
          padding: "10px 18px",
          borderRadius: 8,
          textDecoration: "none",
          whiteSpace: "nowrap",
        }}
      >
        Open niche finder
      </Link>
    </section>
  );
}
```

- [ ] **Step 4: Verify the test passes**

Run: `cd apps/app && npx vitest run src/components/home/HeroQuickSearch.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/app/src/components/home/HeroQuickSearch.tsx apps/app/src/components/home/HeroQuickSearch.test.tsx
git commit -m "feat(app): add HeroQuickSearch component for home dashboard

Prominent CTA card on Home that links to /niche-finder for full
scoring flow. Matches Widby Home design."
```

---

### Task B3: RecommendedMetros component (Supabase-backed server component)

**Files:**
- Create: `apps/app/src/components/home/RecommendedMetros.tsx`
- Test: `apps/app/src/components/home/RecommendedMetros.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `apps/app/src/components/home/RecommendedMetros.test.tsx`:

```tsx
// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import RecommendedMetros from "./RecommendedMetros";

describe("RecommendedMetros", () => {
  it("renders up to six recommended niches", () => {
    render(
      <RecommendedMetros
        items={[
          { id: "a", niche: "roofing", city: "Phoenix, AZ", score: 78 },
          { id: "b", niche: "plumbing", city: "Austin, TX", score: 71 },
          { id: "c", niche: "concrete", city: "Tulsa, OK", score: 65 },
        ]}
      />,
    );
    expect(screen.getByRole("heading", { name: /recommended/i })).toBeInTheDocument();
    expect(screen.getByText("roofing")).toBeInTheDocument();
    expect(screen.getByText("Phoenix, AZ")).toBeInTheDocument();
    expect(screen.getByText("78")).toBeInTheDocument();
  });

  it("renders an empty-state note when items is empty", () => {
    render(<RecommendedMetros items={[]} />);
    expect(screen.getByText(/no recommendations yet/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Verify test fails**

Run: `cd apps/app && npx vitest run src/components/home/RecommendedMetros.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Create the component**

Create `apps/app/src/components/home/RecommendedMetros.tsx`:

```tsx
export interface RecommendedItem {
  id: string;
  niche: string;
  city: string;
  score: number | null;
}

export default function RecommendedMetros({ items }: { items: RecommendedItem[] }) {
  return (
    <section
      aria-labelledby="rec-heading"
      style={{
        background: "var(--card)",
        border: "1px solid var(--rule)",
        borderRadius: 12,
        padding: "18px 20px",
      }}
    >
      <h2
        id="rec-heading"
        style={{
          fontFamily: "var(--serif)",
          fontSize: 18,
          fontWeight: 600,
          color: "var(--ink)",
          margin: "0 0 12px",
        }}
      >
        Recommended
      </h2>
      {items.length === 0 ? (
        <p
          style={{
            fontFamily: "var(--sans)",
            fontSize: 13.5,
            color: "var(--ink-2)",
          }}
        >
          No recommendations yet. Score a niche to get started.
        </p>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
            gap: 12,
          }}
        >
          {items.slice(0, 6).map((item) => (
            <article
              key={item.id}
              style={{
                background: "var(--paper)",
                border: "1px solid var(--rule)",
                borderRadius: 10,
                padding: "12px 14px",
                display: "flex",
                flexDirection: "column",
                gap: 4,
                minWidth: 0,
              }}
            >
              <div
                style={{
                  fontFamily: "var(--sans)",
                  fontSize: 13.5,
                  fontWeight: 600,
                  color: "var(--ink)",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {item.city}
              </div>
              <div
                style={{
                  fontFamily: "var(--sans)",
                  fontSize: 12.5,
                  color: "var(--ink-2)",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {item.niche}
              </div>
              {item.score !== null ? (
                <div
                  style={{
                    fontFamily: "var(--mono)",
                    fontSize: 18,
                    fontWeight: 600,
                    color: "var(--accent-ink)",
                    marginTop: 4,
                  }}
                >
                  {item.score}
                </div>
              ) : null}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
```

- [ ] **Step 4: Verify test passes**

Run: `cd apps/app && npx vitest run src/components/home/RecommendedMetros.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/app/src/components/home/RecommendedMetros.tsx apps/app/src/components/home/RecommendedMetros.test.tsx
git commit -m "feat(app): add RecommendedMetros home component

Displays up to six recent niches as compact cards with
ellipsis-on-overflow and an empty state. Data wiring in page.tsx."
```

---

### Task B4: RecentActivityFeed component

**Files:**
- Create: `apps/app/src/components/home/RecentActivityFeed.tsx`
- Test: `apps/app/src/components/home/RecentActivityFeed.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `apps/app/src/components/home/RecentActivityFeed.test.tsx`:

```tsx
// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import RecentActivityFeed from "./RecentActivityFeed";

describe("RecentActivityFeed", () => {
  it("renders items with timestamp-formatted dates", () => {
    render(
      <RecentActivityFeed
        items={[
          {
            id: "r1",
            niche: "roofing",
            city: "Phoenix, AZ",
            created_at: "2026-04-20T12:00:00Z",
          },
        ]}
      />,
    );
    expect(screen.getByText(/roofing · Phoenix, AZ/i)).toBeInTheDocument();
    // formatted "Apr 20" or "2026-04-20" is acceptable — just ensure a year/month fragment shows
    expect(screen.getByText(/2026|apr/i)).toBeInTheDocument();
  });

  it("shows empty state when items is empty", () => {
    render(<RecentActivityFeed items={[]} />);
    expect(screen.getByText(/no recent activity/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Verify test fails**

Run: `cd apps/app && npx vitest run src/components/home/RecentActivityFeed.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Create the component**

Create `apps/app/src/components/home/RecentActivityFeed.tsx`:

```tsx
export interface ActivityItem {
  id: string;
  niche: string;
  city: string;
  created_at: string;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function RecentActivityFeed({ items }: { items: ActivityItem[] }) {
  return (
    <section
      aria-labelledby="recent-heading"
      style={{
        background: "var(--card)",
        border: "1px solid var(--rule)",
        borderRadius: 12,
        padding: "18px 20px",
      }}
    >
      <h2
        id="recent-heading"
        style={{
          fontFamily: "var(--serif)",
          fontSize: 18,
          fontWeight: 600,
          color: "var(--ink)",
          margin: "0 0 12px",
        }}
      >
        Recent activity
      </h2>
      {items.length === 0 ? (
        <p
          style={{
            fontFamily: "var(--sans)",
            fontSize: 13.5,
            color: "var(--ink-2)",
          }}
        >
          No recent activity. Score a niche to see it here.
        </p>
      ) : (
        <ul
          style={{
            listStyle: "none",
            margin: 0,
            padding: 0,
            display: "flex",
            flexDirection: "column",
            gap: 8,
          }}
        >
          {items.map((item) => (
            <li
              key={item.id}
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "baseline",
                padding: "8px 0",
                borderBottom: "1px solid var(--rule)",
                fontFamily: "var(--sans)",
                fontSize: 13.5,
              }}
            >
              <span style={{ color: "var(--ink)" }}>
                {item.niche} · {item.city}
              </span>
              <span
                style={{
                  color: "var(--ink-3)",
                  fontFamily: "var(--mono)",
                  fontSize: 12,
                }}
              >
                {formatDate(item.created_at)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
```

- [ ] **Step 4: Verify test passes**

Run: `cd apps/app && npx vitest run src/components/home/RecentActivityFeed.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/app/src/components/home/RecentActivityFeed.tsx apps/app/src/components/home/RecentActivityFeed.test.tsx
git commit -m "feat(app): add RecentActivityFeed home component

List of recent niche queries with formatted date stamps
and an empty-state message."
```

---

### Task B5: SavedSearchesBlock component (empty state only)

**Files:**
- Create: `apps/app/src/components/home/SavedSearchesBlock.tsx`
- Test: `apps/app/src/components/home/SavedSearchesBlock.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `apps/app/src/components/home/SavedSearchesBlock.test.tsx`:

```tsx
// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import SavedSearchesBlock from "./SavedSearchesBlock";

describe("SavedSearchesBlock", () => {
  it("shows coming-soon empty state", () => {
    render(<SavedSearchesBlock />);
    expect(screen.getByRole("heading", { name: /saved searches/i })).toBeInTheDocument();
    expect(screen.getByText(/coming soon/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Verify the test fails**

Run: `cd apps/app && npx vitest run src/components/home/SavedSearchesBlock.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Create the component**

Create `apps/app/src/components/home/SavedSearchesBlock.tsx`:

```tsx
export default function SavedSearchesBlock() {
  return (
    <section
      aria-labelledby="saved-heading"
      style={{
        background: "var(--card)",
        border: "1px solid var(--rule)",
        borderRadius: 12,
        padding: "18px 20px",
      }}
    >
      <h2
        id="saved-heading"
        style={{
          fontFamily: "var(--serif)",
          fontSize: 18,
          fontWeight: 600,
          color: "var(--ink)",
          margin: "0 0 12px",
        }}
      >
        Saved searches
      </h2>
      <p
        style={{
          fontFamily: "var(--sans)",
          fontSize: 13.5,
          color: "var(--ink-2)",
          margin: 0,
        }}
      >
        Coming soon. Pin a niche from the finder to see it here.
      </p>
    </section>
  );
}
```

- [ ] **Step 4: Verify test passes**

Run: `cd apps/app && npx vitest run src/components/home/SavedSearchesBlock.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/app/src/components/home/SavedSearchesBlock.tsx apps/app/src/components/home/SavedSearchesBlock.test.tsx
git commit -m "feat(app): add SavedSearchesBlock home placeholder

Static empty-state section on Home until saved-searches
backend lands in Phase 3."
```

---

### Task B6: Home page data loader (server-side)

**Files:**
- Create: `apps/app/src/lib/home/load-dashboard.ts`
- Create: `apps/app/src/lib/home/load-dashboard.test.ts`

This is a pure module that takes a Supabase client and returns the shape the Home page renders. Unit-testable with a mocked client.

- [ ] **Step 1: Write the failing test**

Create `apps/app/src/lib/home/load-dashboard.test.ts`:

```ts
import { describe, it, expect, vi } from "vitest";
import { loadDashboard } from "./load-dashboard";

function makeClient(rows: Array<Record<string, unknown>>) {
  const order = vi.fn().mockResolvedValue({ data: rows, error: null });
  const limit = vi.fn().mockReturnValue({ order: order });
  const select = vi.fn().mockReturnValue({ order: vi.fn().mockReturnValue({ limit }) });
  const from = vi.fn().mockReturnValue({ select });
  return { from } as never;
}

describe("loadDashboard", () => {
  it("returns stats + recent + recommended from reports table", async () => {
    const rows = [
      {
        id: "r1",
        niche_keyword: "roofing",
        geo_target: "Phoenix, AZ",
        created_at: "2026-04-20T12:00:00Z",
        spec_version: "1.1",
        metros: [{ scores: { opportunity: 78 } }],
      },
      {
        id: "r2",
        niche_keyword: "plumbing",
        geo_target: "Austin, TX",
        created_at: "2026-04-19T09:00:00Z",
        spec_version: "1.1",
        metros: [{ scores: { opportunity: 71 } }],
      },
    ];
    const dashboard = await loadDashboard(makeClient(rows));
    expect(dashboard.stats.total_reports).toBe(2);
    expect(dashboard.stats.avg_score).toBe(75); // (78+71)/2 rounded
    expect(dashboard.recent.length).toBe(2);
    expect(dashboard.recent[0].niche).toBe("roofing");
    expect(dashboard.recommended.length).toBe(2);
  });

  it("handles empty reports gracefully", async () => {
    const dashboard = await loadDashboard(makeClient([]));
    expect(dashboard.stats.total_reports).toBe(0);
    expect(dashboard.stats.avg_score).toBe(0);
    expect(dashboard.recent).toEqual([]);
    expect(dashboard.recommended).toEqual([]);
  });
});
```

- [ ] **Step 2: Verify the test fails**

Run: `cd apps/app && npx vitest run src/lib/home/load-dashboard.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement the loader**

Create `apps/app/src/lib/home/load-dashboard.ts`:

```ts
import type { SupabaseClient } from "@supabase/supabase-js";
import type { ActivityItem } from "@/components/home/RecentActivityFeed";
import type { RecommendedItem } from "@/components/home/RecommendedMetros";
import type { StatCard } from "@/components/home/StatCardRow";

interface ReportRow {
  id: string;
  niche_keyword: string;
  geo_target: string;
  created_at: string;
  spec_version: string;
  metros: unknown;
}

function extractScore(metros: unknown): number | null {
  if (!Array.isArray(metros) || metros.length === 0) return null;
  const first = metros[0] as { scores?: { opportunity?: number } };
  const raw = first?.scores?.opportunity;
  return typeof raw === "number" ? Math.round(raw) : null;
}

export interface DashboardData {
  stats: {
    total_reports: number;
    avg_score: number;
    watchlist: number; // placeholder: 0 until saved-searches ships
    niches_scored: number; // same as total_reports in Foundation; diverges later
  };
  recent: ActivityItem[];
  recommended: RecommendedItem[];
  stat_cards: StatCard[];
}

export async function loadDashboard(client: SupabaseClient): Promise<DashboardData> {
  const { data, error } = await client
    .from("reports")
    .select("id, niche_keyword, geo_target, created_at, spec_version, metros")
    .order("created_at", { ascending: false })
    .limit(10);

  if (error) {
    throw new Error(`loadDashboard: ${error.message}`);
  }

  const rows = (data ?? []) as ReportRow[];
  const scored = rows.map((r) => ({ row: r, score: extractScore(r.metros) }));
  const scoresOnly = scored
    .map((s) => s.score)
    .filter((s): s is number => typeof s === "number");

  const avg = scoresOnly.length
    ? Math.round(scoresOnly.reduce((a, b) => a + b, 0) / scoresOnly.length)
    : 0;

  const recent: ActivityItem[] = scored.slice(0, 10).map((s) => ({
    id: s.row.id,
    niche: s.row.niche_keyword,
    city: s.row.geo_target,
    created_at: s.row.created_at,
  }));

  const recommended: RecommendedItem[] = scored.slice(0, 6).map((s) => ({
    id: s.row.id,
    niche: s.row.niche_keyword,
    city: s.row.geo_target,
    score: s.score,
  }));

  const stats = {
    total_reports: rows.length,
    avg_score: avg,
    watchlist: 0,
    niches_scored: rows.length,
  };

  const stat_cards: StatCard[] = [
    { label: "Niches scored", value: String(stats.niches_scored) },
    { label: "Watchlist", value: String(stats.watchlist) },
    { label: "Avg score", value: String(stats.avg_score) },
    { label: "Reports", value: String(stats.total_reports) },
  ];

  return { stats, recent, recommended, stat_cards };
}
```

- [ ] **Step 4: Verify the test passes**

Run: `cd apps/app && npx vitest run src/lib/home/load-dashboard.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/app/src/lib/home/
git commit -m "feat(app): add loadDashboard home data loader

Pure server-side function that reads the reports table once and
projects stats/recent/recommended into the shapes home components expect."
```

---

### Task B7: Home page assembly (replace redirect stub)

**Files:**
- Modify: `apps/app/src/app/(protected)/page.tsx`

- [ ] **Step 1: Read the existing page.tsx to confirm structure**

Read the file to see what it currently does. Expected content: a one-line redirect to `/reports` with a comment.

- [ ] **Step 2: Replace with the Home dashboard**

Replace the contents of `apps/app/src/app/(protected)/page.tsx` with:

```tsx
import { createClient } from "@/lib/supabase/server";
import Sidebar from "@/components/Sidebar";
import Topbar from "@/components/Topbar";
import StatCardRow from "@/components/home/StatCardRow";
import HeroQuickSearch from "@/components/home/HeroQuickSearch";
import RecommendedMetros from "@/components/home/RecommendedMetros";
import RecentActivityFeed from "@/components/home/RecentActivityFeed";
import SavedSearchesBlock from "@/components/home/SavedSearchesBlock";
import { loadDashboard } from "@/lib/home/load-dashboard";

export default async function HomePage() {
  const supabase = await createClient();
  const dashboard = await loadDashboard(supabase);

  return (
    <div className="app density-roomy">
      <Sidebar />
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        <Topbar title="Home" />
        <main
          style={{
            padding: "24px 32px",
            display: "flex",
            flexDirection: "column",
            gap: 20,
            maxWidth: 1280,
            margin: "0 auto",
            width: "100%",
          }}
        >
          <header>
            <h1
              style={{
                fontFamily: "var(--serif)",
                fontSize: 28,
                fontWeight: 600,
                color: "var(--ink)",
                margin: 0,
              }}
            >
              Good work today.
            </h1>
            <p
              style={{
                fontFamily: "var(--sans)",
                fontSize: 14,
                color: "var(--ink-2)",
                margin: "4px 0 0",
              }}
            >
              Your niche-scoring snapshot.
            </p>
          </header>

          <StatCardRow stats={dashboard.stat_cards} />

          <HeroQuickSearch />

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "2fr 1fr",
              gap: 16,
            }}
          >
            <RecommendedMetros items={dashboard.recommended} />
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <RecentActivityFeed items={dashboard.recent} />
              <SavedSearchesBlock />
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Run typecheck**

Run: `cd apps/app && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 4: Smoke-test via vitest (the existing page tests should still pass)**

Run: `cd apps/app && npx vitest run`
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/app/src/app/\(protected\)/page.tsx
git commit -m "feat(app): assemble Home dashboard from B1-B6 components

Replaces the redirect stub with the Widby Home page:
greeting header, 4 stat cards, hero quick-search CTA,
recommended niches grid, recent activity feed, saved-searches
placeholder. Server component; Supabase SSR via loadDashboard."
```

---

## Phase C — Niche Finder command-center upgrade

Upgrades the 014 simple `/niche-finder` page to the Variation B command-center layout.

### Task C1: NicheFinderTabs component

**Files:**
- Create: `apps/app/src/components/niche-finder/NicheFinderTabs.tsx`
- Test: `apps/app/src/components/niche-finder/NicheFinderTabs.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `apps/app/src/components/niche-finder/NicheFinderTabs.test.tsx`:

```tsx
// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import NicheFinderTabs from "./NicheFinderTabs";

describe("NicheFinderTabs", () => {
  it("renders both tabs with the correct aria-selected state", () => {
    render(<NicheFinderTabs active="niche" onChange={() => {}} />);
    const nicheTab = screen.getByRole("tab", { name: /niche & city/i });
    const strategyTab = screen.getByRole("tab", { name: /strategy/i });
    expect(nicheTab).toHaveAttribute("aria-selected", "true");
    expect(strategyTab).toHaveAttribute("aria-selected", "false");
  });

  it("calls onChange with the clicked tab key", async () => {
    const onChange = vi.fn();
    render(<NicheFinderTabs active="niche" onChange={onChange} />);
    const user = userEvent.setup();
    await user.click(screen.getByRole("tab", { name: /strategy/i }));
    expect(onChange).toHaveBeenCalledWith("strategy");
  });
});
```

- [ ] **Step 2: Verify test fails**

Run: `cd apps/app && npx vitest run src/components/niche-finder/NicheFinderTabs.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Create the component**

Create `apps/app/src/components/niche-finder/NicheFinderTabs.tsx`:

```tsx
"use client";

export type TabKey = "niche" | "strategy";

interface Props {
  active: TabKey;
  onChange: (key: TabKey) => void;
}

const TABS: Array<{ key: TabKey; label: string }> = [
  { key: "niche", label: "Niche & city" },
  { key: "strategy", label: "Strategy" },
];

export default function NicheFinderTabs({ active, onChange }: Props) {
  return (
    <div
      role="tablist"
      aria-label="Search mode"
      style={{
        display: "inline-flex",
        gap: 4,
        padding: 4,
        borderRadius: 999,
        background: "var(--paper-alt)",
        border: "1px solid var(--rule)",
      }}
    >
      {TABS.map((tab) => {
        const isActive = tab.key === active;
        return (
          <button
            key={tab.key}
            type="button"
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(tab.key)}
            style={{
              padding: "6px 14px",
              borderRadius: 999,
              fontFamily: "var(--sans)",
              fontSize: 13,
              fontWeight: isActive ? 600 : 500,
              color: isActive ? "var(--card)" : "var(--ink-2)",
              background: isActive ? "var(--accent)" : "transparent",
              border: "none",
              cursor: "pointer",
            }}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 4: Verify test passes**

Run: `cd apps/app && npx vitest run src/components/niche-finder/NicheFinderTabs.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/app/src/components/niche-finder/NicheFinderTabs.tsx apps/app/src/components/niche-finder/NicheFinderTabs.test.tsx
git commit -m "feat(app): add NicheFinderTabs component

Pill-style tab switcher for Niche & city vs Strategy search modes.
Accessible via role=tablist + aria-selected."
```

---

### Task C2: StrategyPresetRail component

**Files:**
- Create: `apps/app/src/components/niche-finder/StrategyPresetRail.tsx`
- Test: `apps/app/src/components/niche-finder/StrategyPresetRail.test.tsx`

Clicking any card in Foundation should show a "coming soon" toast — the archetype-filter backend lands in Phase 3. The component stays pure (no backend call) to keep it testable.

- [ ] **Step 1: Write the failing test**

Create `apps/app/src/components/niche-finder/StrategyPresetRail.test.tsx`:

```tsx
// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import StrategyPresetRail from "./StrategyPresetRail";

describe("StrategyPresetRail", () => {
  it("renders all 8 archetype cards", () => {
    render(<StrategyPresetRail onPick={() => {}} />);
    expect(screen.getByText("Aggregator‑dominated")).toBeInTheDocument();
    expect(screen.getByText("Pack, vulnerable")).toBeInTheDocument();
    expect(screen.getByText("Fragmented, weak")).toBeInTheDocument();
    expect(screen.getByText("Mixed")).toBeInTheDocument();
  });

  it("calls onPick with the archetype id", async () => {
    const onPick = vi.fn();
    render(<StrategyPresetRail onPick={onPick} />);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /pack, vulnerable/i }));
    expect(onPick).toHaveBeenCalledWith("PACK_VULN");
  });
});
```

- [ ] **Step 2: Verify test fails**

Run: `cd apps/app && npx vitest run src/components/niche-finder/StrategyPresetRail.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Create the component**

Create `apps/app/src/components/niche-finder/StrategyPresetRail.tsx`:

```tsx
"use client";

import { ARCHETYPES, type ArchetypeId } from "@/lib/archetypes";

interface Props {
  onPick: (id: ArchetypeId) => void;
}

export default function StrategyPresetRail({ onPick }: Props) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))",
        gap: 12,
      }}
    >
      {ARCHETYPES.map((a) => (
        <button
          key={a.id}
          type="button"
          onClick={() => onPick(a.id)}
          aria-label={a.short}
          style={{
            textAlign: "left",
            background: "var(--card)",
            border: "1px solid var(--rule)",
            borderRadius: 10,
            padding: "14px 16px",
            display: "flex",
            flexDirection: "column",
            gap: 6,
            cursor: "pointer",
            fontFamily: "var(--sans)",
          }}
        >
          <span
            className={a.glyph}
            style={{
              display: "inline-block",
              fontSize: 11,
              padding: "2px 8px",
              borderRadius: 999,
              alignSelf: "flex-start",
              fontWeight: 600,
              letterSpacing: "0.02em",
              textTransform: "uppercase",
            }}
          >
            {a.short}
          </span>
          <span style={{ fontSize: 13, color: "var(--ink)", fontWeight: 500 }}>{a.hint}</span>
          <span style={{ fontSize: 12, color: "var(--ink-2)" }}>{a.strat}</span>
        </button>
      ))}
    </div>
  );
}
```

- [ ] **Step 4: Verify test passes**

Run: `cd apps/app && npx vitest run src/components/niche-finder/StrategyPresetRail.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/app/src/components/niche-finder/StrategyPresetRail.tsx apps/app/src/components/niche-finder/StrategyPresetRail.test.tsx
git commit -m "feat(app): add StrategyPresetRail component

Grid of the 8 archetype preset cards. onPick is stubbed by the page
with a 'coming soon' toast until Phase 3 ships the by-archetype
backend endpoint."
```

---

### Task C3: PinnedRecentRail component (LocalStorage)

**Files:**
- Create: `apps/app/src/components/niche-finder/PinnedRecentRail.tsx`
- Create: `apps/app/src/lib/niche-finder/history-storage.ts`
- Test: `apps/app/src/lib/niche-finder/history-storage.test.ts`
- Test: `apps/app/src/components/niche-finder/PinnedRecentRail.test.tsx`

Split: `history-storage.ts` holds the LocalStorage-touching logic (unit-testable); `PinnedRecentRail.tsx` renders from in-memory arrays passed in as props.

- [ ] **Step 1: Write the failing tests for history-storage**

Create `apps/app/src/lib/niche-finder/history-storage.test.ts`:

```ts
import { describe, it, expect, beforeEach } from "vitest";
import {
  loadRecent,
  pushRecent,
  loadPinned,
  togglePinned,
  type HistoryEntry,
} from "./history-storage";

const memStore: Record<string, string> = {};
const mockLocalStorage = {
  getItem: (k: string) => memStore[k] ?? null,
  setItem: (k: string, v: string) => {
    memStore[k] = v;
  },
  removeItem: (k: string) => {
    delete memStore[k];
  },
  clear: () => {
    for (const k of Object.keys(memStore)) delete memStore[k];
  },
  get length() {
    return Object.keys(memStore).length;
  },
  key: (i: number) => Object.keys(memStore)[i] ?? null,
};

beforeEach(() => {
  mockLocalStorage.clear();
  Object.defineProperty(globalThis, "localStorage", {
    value: mockLocalStorage,
    configurable: true,
  });
});

describe("history-storage", () => {
  it("pushRecent prepends to recent and caps at 8 entries", () => {
    const base: HistoryEntry = { city: "Phoenix, AZ", service: "roofing", at: 0 };
    for (let i = 0; i < 10; i++) {
      pushRecent({ ...base, at: i });
    }
    const recent = loadRecent();
    expect(recent.length).toBe(8);
    expect(recent[0].at).toBe(9); // most recent first
  });

  it("togglePinned adds then removes an entry", () => {
    const entry: HistoryEntry = { city: "Austin, TX", service: "plumber", at: 1 };
    togglePinned(entry);
    expect(loadPinned()).toHaveLength(1);
    togglePinned(entry);
    expect(loadPinned()).toHaveLength(0);
  });

  it("returns empty arrays when storage is blank", () => {
    expect(loadRecent()).toEqual([]);
    expect(loadPinned()).toEqual([]);
  });
});
```

- [ ] **Step 2: Verify test fails**

Run: `cd apps/app && npx vitest run src/lib/niche-finder/history-storage.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Create the history-storage module**

Create `apps/app/src/lib/niche-finder/history-storage.ts`:

```ts
export interface HistoryEntry {
  city: string;
  service: string;
  at: number; // epoch ms
}

const RECENT_KEY = "widby.niche.recent";
const PINNED_KEY = "widby.niche.pinned";
const RECENT_CAP = 8;

function safeParse(raw: string | null): HistoryEntry[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (x): x is HistoryEntry =>
        typeof x === "object" &&
        x !== null &&
        typeof (x as HistoryEntry).city === "string" &&
        typeof (x as HistoryEntry).service === "string" &&
        typeof (x as HistoryEntry).at === "number",
    );
  } catch {
    return [];
  }
}

function key(entry: HistoryEntry): string {
  return `${entry.city.toLowerCase()}|${entry.service.toLowerCase()}`;
}

export function loadRecent(): HistoryEntry[] {
  if (typeof localStorage === "undefined") return [];
  return safeParse(localStorage.getItem(RECENT_KEY));
}

export function pushRecent(entry: HistoryEntry): void {
  if (typeof localStorage === "undefined") return;
  const existing = loadRecent().filter((e) => key(e) !== key(entry));
  const next = [entry, ...existing].slice(0, RECENT_CAP);
  localStorage.setItem(RECENT_KEY, JSON.stringify(next));
}

export function loadPinned(): HistoryEntry[] {
  if (typeof localStorage === "undefined") return [];
  return safeParse(localStorage.getItem(PINNED_KEY));
}

export function togglePinned(entry: HistoryEntry): void {
  if (typeof localStorage === "undefined") return;
  const existing = loadPinned();
  const k = key(entry);
  const found = existing.find((e) => key(e) === k);
  const next = found
    ? existing.filter((e) => key(e) !== k)
    : [entry, ...existing];
  localStorage.setItem(PINNED_KEY, JSON.stringify(next));
}
```

- [ ] **Step 4: Verify the history-storage tests pass**

Run: `cd apps/app && npx vitest run src/lib/niche-finder/history-storage.test.ts`
Expected: PASS.

- [ ] **Step 5: Write PinnedRecentRail test**

Create `apps/app/src/components/niche-finder/PinnedRecentRail.test.tsx`:

```tsx
// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import PinnedRecentRail from "./PinnedRecentRail";

describe("PinnedRecentRail", () => {
  it("renders pinned and recent sections with items", () => {
    render(
      <PinnedRecentRail
        pinned={[{ city: "Austin, TX", service: "plumber", at: 1 }]}
        recent={[{ city: "Phoenix, AZ", service: "roofing", at: 2 }]}
        onPick={() => {}}
      />,
    );
    expect(screen.getByText("Austin, TX")).toBeInTheDocument();
    expect(screen.getByText("plumber")).toBeInTheDocument();
    expect(screen.getByText("Phoenix, AZ")).toBeInTheDocument();
    expect(screen.getByText("roofing")).toBeInTheDocument();
  });

  it("shows empty states when no entries exist", () => {
    render(<PinnedRecentRail pinned={[]} recent={[]} onPick={() => {}} />);
    expect(screen.getByText(/no pinned/i)).toBeInTheDocument();
    expect(screen.getByText(/no recent/i)).toBeInTheDocument();
  });

  it("calls onPick when a recent item is clicked", async () => {
    const onPick = vi.fn();
    render(
      <PinnedRecentRail
        pinned={[]}
        recent={[{ city: "Phoenix, AZ", service: "roofing", at: 1 }]}
        onPick={onPick}
      />,
    );
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /phoenix.*roofing/i }));
    expect(onPick).toHaveBeenCalledWith({
      city: "Phoenix, AZ",
      service: "roofing",
      at: 1,
    });
  });
});
```

- [ ] **Step 6: Verify the PinnedRecentRail test fails**

Run: `cd apps/app && npx vitest run src/components/niche-finder/PinnedRecentRail.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 7: Create the PinnedRecentRail component**

Create `apps/app/src/components/niche-finder/PinnedRecentRail.tsx`:

```tsx
"use client";

import type { HistoryEntry } from "@/lib/niche-finder/history-storage";

interface Props {
  pinned: HistoryEntry[];
  recent: HistoryEntry[];
  onPick: (entry: HistoryEntry) => void;
}

function Row({ entry, onPick }: { entry: HistoryEntry; onPick: (e: HistoryEntry) => void }) {
  return (
    <button
      type="button"
      onClick={() => onPick(entry)}
      aria-label={`${entry.city} ${entry.service}`}
      style={{
        width: "100%",
        textAlign: "left",
        padding: "8px 10px",
        background: "transparent",
        border: "none",
        borderRadius: 8,
        cursor: "pointer",
        fontFamily: "var(--sans)",
        display: "flex",
        flexDirection: "column",
        gap: 2,
      }}
      onMouseEnter={(e) => (e.currentTarget.style.background = "var(--hover)")}
      onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
    >
      <span style={{ fontSize: 13.5, fontWeight: 600, color: "var(--ink)" }}>{entry.city}</span>
      <span style={{ fontSize: 12.5, color: "var(--ink-2)" }}>{entry.service}</span>
    </button>
  );
}

export default function PinnedRecentRail({ pinned, recent, onPick }: Props) {
  return (
    <aside
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 20,
        width: 260,
      }}
    >
      <section>
        <h3
          style={{
            fontFamily: "var(--serif)",
            fontSize: 14,
            fontWeight: 600,
            color: "var(--ink)",
            margin: "0 0 8px",
          }}
        >
          Pinned
        </h3>
        {pinned.length === 0 ? (
          <p style={{ fontFamily: "var(--sans)", fontSize: 12.5, color: "var(--ink-2)" }}>
            No pinned queries yet.
          </p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column" }}>
            {pinned.map((e) => <Row key={`p-${e.at}`} entry={e} onPick={onPick} />)}
          </div>
        )}
      </section>

      <section>
        <h3
          style={{
            fontFamily: "var(--serif)",
            fontSize: 14,
            fontWeight: 600,
            color: "var(--ink)",
            margin: "0 0 8px",
          }}
        >
          Recent
        </h3>
        {recent.length === 0 ? (
          <p style={{ fontFamily: "var(--sans)", fontSize: 12.5, color: "var(--ink-2)" }}>
            No recent queries yet.
          </p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column" }}>
            {recent.map((e) => <Row key={`r-${e.at}`} entry={e} onPick={onPick} />)}
          </div>
        )}
      </section>
    </aside>
  );
}
```

- [ ] **Step 8: Verify test passes**

Run: `cd apps/app && npx vitest run src/components/niche-finder/PinnedRecentRail.test.tsx`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add apps/app/src/components/niche-finder/PinnedRecentRail.tsx apps/app/src/components/niche-finder/PinnedRecentRail.test.tsx apps/app/src/lib/niche-finder/history-storage.ts apps/app/src/lib/niche-finder/history-storage.test.ts
git commit -m "feat(app): add PinnedRecentRail + history-storage

LocalStorage-backed pinned and recent queries rail for Niche Finder.
history-storage.ts handles persistence; the component is pure
presentational and takes arrays as props."
```

---

### Task C4: Niche Finder page rewrite to Variation B

**Files:**
- Modify: `apps/app/src/app/(protected)/niche-finder/page.tsx`

- [ ] **Step 1: Read the existing page.tsx to confirm current shape**

Read `apps/app/src/app/(protected)/niche-finder/page.tsx` so you can see what to keep (the form submit wiring, ClassificationPill, state management) vs replace (the layout).

- [ ] **Step 2: Rewrite with Variation B layout**

Replace the contents of `apps/app/src/app/(protected)/niche-finder/page.tsx` with:

```tsx
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Sidebar from "@/components/Sidebar";
import Topbar from "@/components/Topbar";
import CityAutocomplete from "@/components/niche-finder/CityAutocomplete";
import NicheFinderTabs, { type TabKey } from "@/components/niche-finder/NicheFinderTabs";
import StrategyPresetRail from "@/components/niche-finder/StrategyPresetRail";
import PinnedRecentRail from "@/components/niche-finder/PinnedRecentRail";
import type { StandardSurfaceResponse } from "@/lib/niche-finder/types";
import { validateNicheQueryInput } from "@/lib/niche-finder/request-validation";
import {
  type HistoryEntry,
  loadPinned,
  loadRecent,
  pushRecent,
} from "@/lib/niche-finder/history-storage";

type PageState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "success"; data: StandardSurfaceResponse };

const LABEL_STYLE: Record<string, { className: string; label: string }> = {
  High: { className: "arch-pack-vuln", label: "High opportunity" },
  Medium: { className: "arch-pack-est", label: "Medium opportunity" },
  Low: { className: "arch-barren", label: "Low opportunity" },
};

function ClassificationPill({ label }: { label: string }) {
  const style = LABEL_STYLE[label] ?? { className: "arch-mixed", label };
  return (
    <span
      className={style.className}
      style={{
        display: "inline-block",
        padding: "3px 10px",
        borderRadius: 999,
        fontSize: 11.5,
        fontFamily: "var(--sans)",
        fontWeight: 600,
        letterSpacing: "0.02em",
        textTransform: "uppercase" as const,
      }}
    >
      {style.label}
    </span>
  );
}

export default function NicheFinderPage() {
  const [tab, setTab] = useState<TabKey>("niche");
  const [city, setCity] = useState("");
  const [state, setState] = useState<string | undefined>(undefined);
  const [service, setService] = useState("");
  const [page, setPage] = useState<PageState>({ kind: "idle" });
  const [toast, setToast] = useState<string | null>(null);
  const [pinned, setPinned] = useState<HistoryEntry[]>([]);
  const [recent, setRecent] = useState<HistoryEntry[]>([]);

  useEffect(() => {
    setPinned(loadPinned());
    setRecent(loadRecent());
  }, []);

  function showToast(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(null), 2400);
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const input = { city, service, state };
    const validation = validateNicheQueryInput(input);
    if (!validation.valid) {
      setPage({ kind: "error", message: validation.errors.join(", ") });
      return;
    }
    setPage({ kind: "loading" });
    try {
      const res = await fetch("/api/agent/scoring", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(input),
      });
      if (!res.ok) {
        const text = await res.text();
        setPage({ kind: "error", message: text || `HTTP ${res.status}` });
        return;
      }
      const data = (await res.json()) as StandardSurfaceResponse;
      setPage({ kind: "success", data });
      pushRecent({ city, service, at: Date.now() });
      setRecent(loadRecent());
    } catch (err) {
      setPage({ kind: "error", message: String(err) });
    }
  }

  function applyHistory(entry: HistoryEntry) {
    setCity(entry.city);
    setService(entry.service);
    setTab("niche");
  }

  return (
    <div className="app density-roomy">
      <Sidebar />
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        <Topbar title="Niche finder" />
        <main
          style={{
            padding: "24px 32px",
            display: "flex",
            gap: 24,
            maxWidth: 1280,
            margin: "0 auto",
            width: "100%",
          }}
        >
          <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 20, minWidth: 0 }}>
            <header style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <h1
                style={{
                  fontFamily: "var(--serif)",
                  fontSize: 28,
                  fontWeight: 600,
                  color: "var(--ink)",
                  margin: 0,
                }}
              >
                Score a niche.
              </h1>
              <NicheFinderTabs active={tab} onChange={setTab} />
            </header>

            {tab === "niche" ? (
              <form
                onSubmit={submit}
                style={{
                  background: "var(--card)",
                  border: "1px solid var(--rule)",
                  borderRadius: 12,
                  padding: "16px 20px",
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr auto",
                  gap: 12,
                  alignItems: "end",
                }}
              >
                <CityAutocomplete
                  value={city}
                  onChange={(next) => {
                    setCity(next.city);
                    setState(next.state);
                  }}
                />
                <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                  <span
                    style={{
                      fontFamily: "var(--sans)",
                      fontSize: 11.5,
                      letterSpacing: "0.06em",
                      textTransform: "uppercase",
                      color: "var(--ink-3)",
                    }}
                  >
                    Service
                  </span>
                  <input
                    type="text"
                    value={service}
                    onChange={(e) => setService(e.target.value)}
                    placeholder="e.g. roofing"
                    style={{
                      padding: "8px 12px",
                      border: "1px solid var(--rule)",
                      borderRadius: 8,
                      fontSize: 14,
                      fontFamily: "var(--sans)",
                      background: "var(--paper)",
                      color: "var(--ink)",
                    }}
                  />
                </label>
                <button
                  type="submit"
                  disabled={page.kind === "loading"}
                  style={{
                    padding: "10px 18px",
                    borderRadius: 8,
                    background: "var(--accent)",
                    color: "var(--card)",
                    fontFamily: "var(--sans)",
                    fontSize: 13.5,
                    fontWeight: 600,
                    border: "none",
                    cursor: page.kind === "loading" ? "not-allowed" : "pointer",
                    opacity: page.kind === "loading" ? 0.7 : 1,
                  }}
                >
                  {page.kind === "loading" ? "Scoring…" : "Score niche"}
                </button>
              </form>
            ) : (
              <StrategyPresetRail
                onPick={() => showToast("Strategy search coming soon — Phase 3.")}
              />
            )}

            {page.kind === "error" ? (
              <div
                role="alert"
                style={{
                  padding: "12px 16px",
                  border: "1px solid var(--danger)",
                  background: "var(--danger-soft)",
                  color: "var(--danger)",
                  borderRadius: 8,
                  fontFamily: "var(--sans)",
                  fontSize: 13.5,
                }}
              >
                {page.message}
              </div>
            ) : null}

            {page.kind === "success" ? (
              <section
                aria-label="Score result"
                style={{
                  background: "var(--card)",
                  border: "1px solid var(--rule)",
                  borderRadius: 12,
                  padding: "18px 20px",
                  display: "flex",
                  flexDirection: "column",
                  gap: 8,
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <ClassificationPill label={page.data.score_result.classification_label} />
                  <span
                    style={{
                      fontFamily: "var(--mono)",
                      fontSize: 28,
                      fontWeight: 600,
                      color: "var(--accent-ink)",
                    }}
                  >
                    {page.data.score_result.opportunity_score}
                  </span>
                </div>
                <div
                  style={{
                    fontFamily: "var(--sans)",
                    fontSize: 13.5,
                    color: "var(--ink-2)",
                  }}
                >
                  {page.data.query.service} · {page.data.query.city}
                  {page.data.query.state ? `, ${page.data.query.state}` : null}
                </div>
                {page.data.report_id ? (
                  <Link
                    href={`/reports`}
                    style={{
                      fontFamily: "var(--sans)",
                      fontSize: 13,
                      color: "var(--accent-ink)",
                      marginTop: 4,
                    }}
                  >
                    View in reports →
                  </Link>
                ) : null}
              </section>
            ) : null}
          </div>

          <PinnedRecentRail pinned={pinned} recent={recent} onPick={applyHistory} />
        </main>

        {toast ? (
          <div
            role="status"
            style={{
              position: "fixed",
              bottom: 24,
              left: "50%",
              transform: "translateX(-50%)",
              background: "var(--ink)",
              color: "var(--card)",
              padding: "10px 18px",
              borderRadius: 999,
              fontFamily: "var(--sans)",
              fontSize: 13,
              zIndex: 100,
            }}
          >
            {toast}
          </div>
        ) : null}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Run typecheck**

Run: `cd apps/app && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 4: Run all vitest**

Run: `cd apps/app && npx vitest run`
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/app/src/app/\(protected\)/niche-finder/page.tsx
git commit -m "feat(app): upgrade Niche Finder to Variation B command-center

Two-column layout: main column with heading + tabs + form/strategy
preset rail + result card; right rail with pinned + recent queries.
Strategy tab shows coming-soon toast; real by-archetype endpoint
ships in Phase 3. LocalStorage persistence for pinned/recent."
```

---

## Phase D — Reports chip-filter re-skin

Re-skins the 014 basic `/reports` page into the archetype-chip-filtered archive per `niche-reports.jsx`.

### Task D1: Archetype derivation helper

**Files:**
- Create: `apps/app/src/lib/niche-finder/derive-archetype.ts`
- Create: `apps/app/src/lib/niche-finder/derive-archetype.test.ts`

Derives an archetype id from a report row. Until scoring explicitly emits archetype ids, we use a deterministic derivation from `opportunity_score` + report metadata. Replace with a real read-through once backend emits it.

- [ ] **Step 1: Write the failing test**

Create `apps/app/src/lib/niche-finder/derive-archetype.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { deriveArchetype } from "./derive-archetype";

describe("deriveArchetype", () => {
  it("returns MIXED when no score is present", () => {
    expect(deriveArchetype({ opportunity_score: null })).toBe("MIXED");
  });

  it("maps high opportunity (>=75) to PACK_VULN", () => {
    expect(deriveArchetype({ opportunity_score: 80 })).toBe("PACK_VULN");
  });

  it("maps mid-high (60-74) to FRAG_WEAK", () => {
    expect(deriveArchetype({ opportunity_score: 68 })).toBe("FRAG_WEAK");
  });

  it("maps mid (45-59) to PACK_EST", () => {
    expect(deriveArchetype({ opportunity_score: 50 })).toBe("PACK_EST");
  });

  it("maps low-mid (30-44) to FRAG_COMP", () => {
    expect(deriveArchetype({ opportunity_score: 36 })).toBe("FRAG_COMP");
  });

  it("maps low (<30) to BARREN", () => {
    expect(deriveArchetype({ opportunity_score: 12 })).toBe("BARREN");
  });
});
```

- [ ] **Step 2: Verify the test fails**

Run: `cd apps/app && npx vitest run src/lib/niche-finder/derive-archetype.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Create the derivation helper**

Create `apps/app/src/lib/niche-finder/derive-archetype.ts`:

```ts
import type { ArchetypeId } from "@/lib/archetypes";

/**
 * Temporary mapping until src/pipeline/* emits archetype ids on the
 * report row. Score bands were chosen to give each archetype visible
 * representation in the UI; calibrate once the real field lands.
 */
export function deriveArchetype(row: { opportunity_score: number | null }): ArchetypeId {
  const s = row.opportunity_score;
  if (s === null || s === undefined) return "MIXED";
  if (s >= 75) return "PACK_VULN";
  if (s >= 60) return "FRAG_WEAK";
  if (s >= 45) return "PACK_EST";
  if (s >= 30) return "FRAG_COMP";
  return "BARREN";
}
```

- [ ] **Step 4: Verify the test passes**

Run: `cd apps/app && npx vitest run src/lib/niche-finder/derive-archetype.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/app/src/lib/niche-finder/derive-archetype.ts apps/app/src/lib/niche-finder/derive-archetype.test.ts
git commit -m "feat(app): add deriveArchetype helper for reports page

Maps opportunity_score -> ArchetypeId as a temporary stand-in until
the scoring pipeline emits archetype ids on report rows. Tracked
for replacement in the Phase 3 spec."
```

---

### Task D2: ArchetypeChipFilter component

**Files:**
- Create: `apps/app/src/components/reports/ArchetypeChipFilter.tsx`
- Test: `apps/app/src/components/reports/ArchetypeChipFilter.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `apps/app/src/components/reports/ArchetypeChipFilter.test.tsx`:

```tsx
// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import ArchetypeChipFilter from "./ArchetypeChipFilter";

describe("ArchetypeChipFilter", () => {
  it("renders 'All strategies' + 8 chips", () => {
    render(<ArchetypeChipFilter selected={[]} onChange={() => {}} />);
    expect(screen.getByRole("button", { name: /all strategies/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /aggregator/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /pack, vulnerable/i })).toBeInTheDocument();
  });

  it("calls onChange with toggled selection when a chip is clicked", async () => {
    const onChange = vi.fn();
    render(<ArchetypeChipFilter selected={[]} onChange={onChange} />);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /pack, vulnerable/i }));
    expect(onChange).toHaveBeenCalledWith(["PACK_VULN"]);
  });

  it("clears selection when 'All strategies' is clicked", async () => {
    const onChange = vi.fn();
    render(<ArchetypeChipFilter selected={["PACK_VULN", "FRAG_WEAK"]} onChange={onChange} />);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /all strategies/i }));
    expect(onChange).toHaveBeenCalledWith([]);
  });
});
```

- [ ] **Step 2: Verify the test fails**

Run: `cd apps/app && npx vitest run src/components/reports/ArchetypeChipFilter.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Create the component**

Create `apps/app/src/components/reports/ArchetypeChipFilter.tsx`:

```tsx
"use client";

import { ARCHETYPES, type ArchetypeId } from "@/lib/archetypes";

interface Props {
  selected: ArchetypeId[];
  onChange: (next: ArchetypeId[]) => void;
}

export default function ArchetypeChipFilter({ selected, onChange }: Props) {
  const allSelected = selected.length === 0;
  function toggle(id: ArchetypeId) {
    if (selected.includes(id)) {
      onChange(selected.filter((s) => s !== id));
    } else {
      onChange([...selected, id]);
    }
  }
  return (
    <div
      role="group"
      aria-label="Filter by archetype"
      style={{
        display: "flex",
        gap: 8,
        flexWrap: "wrap",
        alignItems: "center",
      }}
    >
      <button
        type="button"
        onClick={() => onChange([])}
        style={{
          padding: "6px 14px",
          borderRadius: 999,
          fontFamily: "var(--sans)",
          fontSize: 12.5,
          fontWeight: allSelected ? 600 : 500,
          color: allSelected ? "var(--card)" : "var(--ink-2)",
          background: allSelected ? "var(--accent)" : "transparent",
          border: `1px solid ${allSelected ? "var(--accent)" : "var(--rule)"}`,
          cursor: "pointer",
        }}
      >
        All strategies
      </button>
      {ARCHETYPES.map((a) => {
        const isOn = selected.includes(a.id);
        return (
          <button
            key={a.id}
            type="button"
            onClick={() => toggle(a.id)}
            className={isOn ? a.glyph : undefined}
            aria-pressed={isOn}
            style={{
              padding: "6px 12px",
              borderRadius: 999,
              fontFamily: "var(--sans)",
              fontSize: 12.5,
              fontWeight: 600,
              border: `1px solid ${isOn ? "transparent" : "var(--rule)"}`,
              background: isOn ? undefined : "transparent",
              color: isOn ? undefined : "var(--ink-2)",
              cursor: "pointer",
            }}
          >
            {a.short}
          </button>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 4: Verify the test passes**

Run: `cd apps/app && npx vitest run src/components/reports/ArchetypeChipFilter.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/app/src/components/reports/
git commit -m "feat(app): add ArchetypeChipFilter for reports page

Multi-select chip group with All-strategies clear. Chips tint via
the shared .arch-* classes when on. onChange receives the next
selection array for parent state."
```

---

### Task D3: ReportsTable component

**Files:**
- Create: `apps/app/src/components/reports/ReportsTable.tsx`
- Test: `apps/app/src/components/reports/ReportsTable.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `apps/app/src/components/reports/ReportsTable.test.tsx`:

```tsx
// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import ReportsTable, { type TableRow } from "./ReportsTable";

const rows: TableRow[] = [
  {
    id: "r1",
    niche: "roofing",
    city: "Phoenix, AZ",
    archetype_id: "PACK_VULN",
    archetype_short: "Pack, vulnerable",
    opportunity_score: 78,
    spec_version: "1.1",
    created_at: "2026-04-20T12:00:00Z",
  },
  {
    id: "r2",
    niche: "plumbing",
    city: "Austin, TX",
    archetype_id: "FRAG_WEAK",
    archetype_short: "Fragmented, weak",
    opportunity_score: 62,
    spec_version: "1.1",
    created_at: "2026-04-19T09:00:00Z",
  },
];

describe("ReportsTable", () => {
  it("renders a row for each item", () => {
    render(<ReportsTable rows={rows} />);
    expect(screen.getByText("roofing · Phoenix, AZ")).toBeInTheDocument();
    expect(screen.getByText("plumbing · Austin, TX")).toBeInTheDocument();
    expect(screen.getByText("78")).toBeInTheDocument();
    expect(screen.getByText("Pack, vulnerable")).toBeInTheDocument();
  });

  it("shows empty state when rows is empty", () => {
    render(<ReportsTable rows={[]} />);
    expect(screen.getByText(/no reports match/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Verify the test fails**

Run: `cd apps/app && npx vitest run src/components/reports/ReportsTable.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Create the component**

Create `apps/app/src/components/reports/ReportsTable.tsx`:

```tsx
"use client";

import { ARCHETYPES, type ArchetypeId } from "@/lib/archetypes";

export interface TableRow {
  id: string;
  niche: string;
  city: string;
  archetype_id: ArchetypeId;
  archetype_short: string;
  opportunity_score: number | null;
  spec_version: string;
  created_at: string;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function archetypeGlyphClass(id: ArchetypeId): string {
  return ARCHETYPES.find((a) => a.id === id)?.glyph ?? "arch-mixed";
}

export default function ReportsTable({ rows }: { rows: TableRow[] }) {
  if (rows.length === 0) {
    return (
      <div
        role="status"
        style={{
          padding: "24px 20px",
          textAlign: "center",
          fontFamily: "var(--sans)",
          fontSize: 14,
          color: "var(--ink-2)",
          background: "var(--card)",
          border: "1px solid var(--rule)",
          borderRadius: 12,
        }}
      >
        No reports match the current filters.
      </div>
    );
  }

  return (
    <div
      role="table"
      aria-label="Reports"
      style={{
        background: "var(--card)",
        border: "1px solid var(--rule)",
        borderRadius: 12,
        overflow: "hidden",
      }}
    >
      <div
        role="row"
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(0, 3fr) 1fr 1fr 1fr",
          padding: "10px 16px",
          background: "var(--paper-alt)",
          borderBottom: "1px solid var(--rule)",
          fontFamily: "var(--sans)",
          fontSize: 11.5,
          letterSpacing: "0.06em",
          textTransform: "uppercase",
          color: "var(--ink-3)",
          gap: 12,
        }}
      >
        <span role="columnheader">Report</span>
        <span role="columnheader">Strategy</span>
        <span role="columnheader" style={{ textAlign: "right" }}>Top score</span>
        <span role="columnheader" style={{ textAlign: "right" }}>Date</span>
      </div>
      {rows.map((r) => (
        <div
          key={r.id}
          role="row"
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(0, 3fr) 1fr 1fr 1fr",
            padding: "12px 16px",
            borderBottom: "1px solid var(--rule)",
            fontFamily: "var(--sans)",
            fontSize: 13.5,
            color: "var(--ink)",
            alignItems: "flex-start",
            gap: 12,
          }}
        >
          <span
            role="cell"
            style={{
              minWidth: 0,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
            title={`${r.niche} · ${r.city}`}
          >
            {r.niche} · {r.city}
          </span>
          <span role="cell">
            <span
              className={archetypeGlyphClass(r.archetype_id)}
              style={{
                display: "inline-block",
                padding: "2px 10px",
                borderRadius: 999,
                fontSize: 11.5,
                fontWeight: 600,
                textTransform: "uppercase" as const,
                letterSpacing: "0.02em",
              }}
            >
              {r.archetype_short}
            </span>
          </span>
          <span
            role="cell"
            style={{
              textAlign: "right",
              fontFamily: "var(--mono)",
              color: "var(--accent-ink)",
              fontWeight: 600,
            }}
          >
            {r.opportunity_score ?? "—"}
          </span>
          <span
            role="cell"
            style={{
              textAlign: "right",
              fontFamily: "var(--mono)",
              fontSize: 12,
              color: "var(--ink-3)",
            }}
          >
            {formatDate(r.created_at)}
          </span>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 4: Verify the test passes**

Run: `cd apps/app && npx vitest run src/components/reports/ReportsTable.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/app/src/components/reports/ReportsTable.tsx apps/app/src/components/reports/ReportsTable.test.tsx
git commit -m "feat(app): add ReportsTable component

Semantic grid table with Report/Strategy/Top score/Date columns,
ellipsis on long titles with title-tooltip, and an empty state.
Archetype cells use the shared .arch-* tint classes."
```

---

### Task D4: Reports page rewrite

**Files:**
- Modify: `apps/app/src/app/(protected)/reports/page.tsx`
- Create: `apps/app/src/app/(protected)/reports/ReportsPageClient.tsx`

Foundation splits the page into a server component (SSR fetch) and a client component (filter/state). The existing `ReportsView.tsx` stays untouched; this new `ReportsPageClient.tsx` replaces it at the page level.

- [ ] **Step 1: Read the existing reports page structure**

Read `apps/app/src/app/(protected)/reports/page.tsx` and `apps/app/src/app/(protected)/reports/ReportsView.tsx` to confirm the Supabase fetch shape and how they compose.

- [ ] **Step 2: Write the client shell**

Create `apps/app/src/app/(protected)/reports/ReportsPageClient.tsx`:

```tsx
"use client";

import { useMemo, useState } from "react";
import ArchetypeChipFilter from "@/components/reports/ArchetypeChipFilter";
import ReportsTable, { type TableRow } from "@/components/reports/ReportsTable";
import type { ArchetypeId } from "@/lib/archetypes";

interface Props {
  rows: TableRow[];
}

export default function ReportsPageClient({ rows }: Props) {
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<ArchetypeId[]>([]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return rows.filter((r) => {
      if (selected.length > 0 && !selected.includes(r.archetype_id)) return false;
      if (!q) return true;
      return (
        r.niche.toLowerCase().includes(q) ||
        r.city.toLowerCase().includes(q) ||
        r.archetype_short.toLowerCase().includes(q)
      );
    });
  }, [rows, query, selected]);

  const summary = useMemo(() => {
    const byArchetype = new Map<string, number>();
    for (const r of rows) {
      byArchetype.set(r.archetype_short, (byArchetype.get(r.archetype_short) ?? 0) + 1);
    }
    return {
      total: rows.length,
      top_strategy: [...byArchetype.entries()].sort((a, b) => b[1] - a[1])[0]?.[0] ?? "—",
    };
  }, [rows]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <section
        aria-label="Summary"
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
          gap: 12,
        }}
      >
        <div
          style={{
            background: "var(--card)",
            border: "1px solid var(--rule)",
            borderRadius: 12,
            padding: "14px 18px",
          }}
        >
          <div
            style={{
              fontFamily: "var(--sans)",
              fontSize: 11.5,
              letterSpacing: "0.06em",
              textTransform: "uppercase",
              color: "var(--ink-3)",
              marginBottom: 4,
            }}
          >
            Total reports
          </div>
          <div
            style={{
              fontFamily: "var(--serif)",
              fontSize: 24,
              fontWeight: 600,
              color: "var(--ink)",
            }}
          >
            {summary.total}
          </div>
        </div>
        <div
          style={{
            background: "var(--card)",
            border: "1px solid var(--rule)",
            borderRadius: 12,
            padding: "14px 18px",
          }}
        >
          <div
            style={{
              fontFamily: "var(--sans)",
              fontSize: 11.5,
              letterSpacing: "0.06em",
              textTransform: "uppercase",
              color: "var(--ink-3)",
              marginBottom: 4,
            }}
          >
            Most common strategy
          </div>
          <div
            style={{
              fontFamily: "var(--serif)",
              fontSize: 20,
              fontWeight: 600,
              color: "var(--ink)",
            }}
          >
            {summary.top_strategy}
          </div>
        </div>
      </section>

      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Filter by niche, city, or strategy…"
        aria-label="Search reports"
        style={{
          padding: "10px 14px",
          border: "1px solid var(--rule)",
          borderRadius: 10,
          fontFamily: "var(--sans)",
          fontSize: 13.5,
          background: "var(--card)",
          color: "var(--ink)",
        }}
      />

      <ArchetypeChipFilter selected={selected} onChange={setSelected} />

      <ReportsTable rows={filtered} />

      <div
        aria-live="polite"
        style={{
          fontFamily: "var(--sans)",
          fontSize: 12.5,
          color: "var(--ink-3)",
        }}
      >
        Showing {filtered.length} of {rows.length}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Rewrite the page.tsx to use the new client component**

Replace `apps/app/src/app/(protected)/reports/page.tsx` with:

```tsx
import Sidebar from "@/components/Sidebar";
import Topbar from "@/components/Topbar";
import { createClient } from "@/lib/supabase/server";
import { ARCHETYPES, type ArchetypeId } from "@/lib/archetypes";
import { mapReportRow } from "@/lib/niche-finder/reports-mapper";
import { deriveArchetype } from "@/lib/niche-finder/derive-archetype";
import type { TableRow } from "@/components/reports/ReportsTable";
import ReportsPageClient from "./ReportsPageClient";

function archetypeShort(id: ArchetypeId): string {
  return ARCHETYPES.find((a) => a.id === id)?.short ?? "Mixed";
}

export default async function ReportsPage() {
  const supabase = await createClient();
  const { data, error } = await supabase
    .from("reports")
    .select("id, niche_keyword, geo_target, created_at, spec_version, metros")
    .order("created_at", { ascending: false })
    .limit(50);

  if (error) {
    throw new Error(`reports list: ${error.message}`);
  }

  const rows: TableRow[] = (data ?? []).map((raw) => {
    const m = mapReportRow({
      id: raw.id,
      niche_keyword: raw.niche_keyword,
      geo_target: raw.geo_target,
      created_at: raw.created_at,
      spec_version: raw.spec_version,
      metros: raw.metros,
    });
    const archetype_id = deriveArchetype({ opportunity_score: m.opportunity_score });
    return {
      id: m.id,
      niche: m.niche_keyword,
      city: m.geo_target,
      archetype_id,
      archetype_short: archetypeShort(archetype_id),
      opportunity_score: m.opportunity_score,
      spec_version: m.spec_version,
      created_at: m.created_at,
    };
  });

  return (
    <div className="app density-roomy">
      <Sidebar />
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        <Topbar title="Reports" />
        <main
          style={{
            padding: "24px 32px",
            maxWidth: 1280,
            margin: "0 auto",
            width: "100%",
            display: "flex",
            flexDirection: "column",
            gap: 20,
          }}
        >
          <header>
            <h1
              style={{
                fontFamily: "var(--serif)",
                fontSize: 28,
                fontWeight: 600,
                color: "var(--ink)",
                margin: 0,
              }}
            >
              Reports
            </h1>
            <p
              style={{
                fontFamily: "var(--sans)",
                fontSize: 14,
                color: "var(--ink-2)",
                margin: "4px 0 0",
              }}
            >
              Every niche score you've run, most recent first.
            </p>
          </header>
          <ReportsPageClient rows={rows} />
        </main>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run typecheck**

Run: `cd apps/app && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 5: Run all vitest**

Run: `cd apps/app && npx vitest run`
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add apps/app/src/app/\(protected\)/reports/
git commit -m "feat(app): re-skin Reports page with archetype chip filter

Split into server component (SSR Supabase fetch + archetype derivation)
and ReportsPageClient (stateful filter/search/summary + table).
Replaces the 014 basic ReportsView. Also retires it as a file the
page references — kept in place for Phase 5 exploration drill-down."
```

---

## Phase E — Polish

### Task E1: Playwright E2E — full Foundation flow

**Files:**
- Create: `apps/app/e2e/niche-foundation.spec.ts`

- [ ] **Step 1: Check existing e2e configuration**

Run: `ls apps/app/e2e/` and `cat apps/app/playwright.config.ts`. Confirm that `NEXT_PUBLIC_NICHE_DRY_RUN=1` is the dry-run env var (it should be per 013 spec).

- [ ] **Step 2: Write the E2E spec**

Create `apps/app/e2e/niche-foundation.spec.ts`:

```ts
import { test, expect } from "@playwright/test";

test.describe("Foundation flow", () => {
  test("home page renders dashboard sections", async ({ page }) => {
    await page.goto("/");
    // Auth redirect may intercept — the suite should be pre-authenticated
    // via storageState (inherit from existing niche-scoring.spec if present).
    await expect(page.getByRole("heading", { name: /good work/i })).toBeVisible();
    await expect(page.getByRole("link", { name: /open niche finder/i })).toBeVisible();
  });

  test("niche finder command center loads and switches tabs", async ({ page }) => {
    await page.goto("/niche-finder");
    await expect(page.getByRole("heading", { name: /score a niche/i })).toBeVisible();
    await page.getByRole("tab", { name: /strategy/i }).click();
    // Strategy preset rail shows
    await expect(page.getByText(/aggregator‑dominated|pack, vulnerable/i)).toBeVisible();
    // Click a preset card → coming-soon toast
    await page.getByRole("button", { name: /pack, vulnerable/i }).click();
    await expect(page.getByRole("status")).toContainText(/coming soon/i);
  });

  test("reports page filters by archetype chip", async ({ page }) => {
    await page.goto("/reports");
    await expect(page.getByRole("heading", { name: /^reports$/i })).toBeVisible();
    await page.getByRole("button", { name: /pack, vulnerable/i }).click();
    // aria-live region should report a row count
    await expect(page.getByText(/showing \d+ of/i)).toBeVisible();
    // Click All strategies to clear
    await page.getByRole("button", { name: /all strategies/i }).click();
  });
});
```

- [ ] **Step 3: Run the E2E test**

Run: `cd apps/app && NEXT_PUBLIC_NICHE_DRY_RUN=1 npx playwright test e2e/niche-foundation.spec.ts`
Expected: all three tests pass (they may need a login storageState helper — inherit from existing Playwright suite).

- [ ] **Step 4: Commit**

```bash
git add apps/app/e2e/niche-foundation.spec.ts
git commit -m "test(app): Playwright E2E for Foundation consumer flow

Covers home → niche-finder tab switching + coming-soon toast →
reports chip filter. Uses NEXT_PUBLIC_NICHE_DRY_RUN=1 to avoid
live API calls."
```

---

### Task E2: Update apps/app/CLAUDE.md + repo CLAUDE.md

**Files:**
- Modify: `apps/app/CLAUDE.md`

- [ ] **Step 1: Rewrite the "Topology (current)" section**

Read `apps/app/CLAUDE.md` to find the Topology section. Replace it with a block that lists the new (protected) tree:

```
apps/app/
  src/
    app/
      (protected)/
        page.tsx                 Home dashboard (SSR — loadDashboard)
        niche-finder/
          page.tsx               Variation B command center
        reports/
          page.tsx               SSR Supabase fetch + client shell
          ReportsPageClient.tsx  Client filter/search/summary + table
          ReportsView.tsx        Legacy 014 client table (unused by Foundation)
        recommendations/         Coming-soon stub
        layout.tsx               Sidebar + Topbar shell
      api/agent/                 scoring + metros/suggest + health proxies
      auth/                      Supabase auth callback
      login/                     Sign-in flow
    components/
      home/                      StatCardRow, HeroQuickSearch, RecommendedMetros,
                                  RecentActivityFeed, SavedSearchesBlock
      niche-finder/              CityAutocomplete, NicheFinderTabs,
                                  StrategyPresetRail, PinnedRecentRail
      reports/                   ArchetypeChipFilter, ReportsTable
      Sidebar.tsx / Topbar.tsx / StatusPill.tsx
    lib/
      archetypes.ts              8-archetype registry (id/short/glyph/hint/strat)
      home/load-dashboard.ts     Supabase → DashboardData loader
      niche-finder/              types, request-validation, metro-suggest,
                                  reports-mapper, history-storage, derive-archetype
      supabase/                  Supabase server/client factories
```

- [ ] **Step 2: Add a "Foundation flow" section**

Under the existing "Niche-finder flow on consumer" heading (or create a sibling), add:

```
## Foundation flow (2026-04-21)

All Foundation pages are deterministic — no Claude calls. Agentic
features (exploration assistant, strategy search, shareable reports)
arrive from Phase 2 onward on Managed Agents. See
`docs/superpowers/specs/2026-04-21-widby-niche-finder-v1-design.md`
for the phased roadmap and the separation-of-concerns rule that
keeps the product lane deterministic.
```

- [ ] **Step 3: Commit**

```bash
git add apps/app/CLAUDE.md
git commit -m "docs(app): refresh CLAUDE.md for Foundation shipped state

Lists the new Home/Niche Finder/Reports components and lib modules.
References the 2026-04-21 design spec for the phased roadmap."
```

---

## Self-review checklist

Run these checks before declaring the plan done:

- **Spec coverage:** Home page (✓ B1-B7), Niche Finder command center + tabs + preset rail + pinned/recent (✓ C1-C4), Reports chip filter + table + page (✓ D1-D4), Playwright E2E (✓ E1), CLAUDE.md update (✓ E2). Covers every Foundation requirement from the spec.
- **Non-goals honored:** no saved-searches backend work, no exploration surface, no Managed Agents plumbing, no module extraction, no report detail pages. All deferred per the spec.
- **Type consistency:** `ArchetypeId` imported from `@/lib/archetypes` in D1-D4; `TableRow` exported from `ReportsTable.tsx` and consumed by `ReportsPageClient`; `HistoryEntry` exported from `history-storage.ts` and consumed by `PinnedRecentRail`.
- **File paths exact:** every Create/Modify uses absolute `apps/app/src/...` paths.
- **Test code complete:** each task contains full test file contents, not pseudocode.
- **Commit messages specific:** each commit names the component/feature, avoids generic "fix typo" style.

## Verification after all tasks

Run from the worktree root after completing every task:

```bash
# Python baseline (should match baseline from Phase A)
pytest tests/unit/ -q --tb=no
ruff check src/ tests/

# apps/app
cd apps/app
npx tsc --noEmit
npx vitest run

# apps/admin (must not regress)
cd ../admin
npx tsc --noEmit
npx vitest run
```

All four must be green. Playwright E2E is run manually via `NEXT_PUBLIC_NICHE_DRY_RUN=1 npx playwright test e2e/niche-foundation.spec.ts` inside `apps/app`.
