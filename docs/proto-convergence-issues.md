# Proto → Production Convergence: Epics & Issues

> Generated from code-level comparison of `whidby-ux-proto` (northstar) vs `apps/app` (production).
> Structure: **Project → Epic → Issue → Sub-issue**. Agent-ready — no time estimates, clear instructions only.
> System design callouts flagged with **[SYSTEM DESIGN REQUIRED]**.

---

## Epic 1: App Frame — Sidebar → Top Navbar

**Goal:** Replace the current left sidebar + topbar layout with the proto's sticky top navbar. This is the foundational change — every other epic depends on it.

### Issue 1.1: Remove Sidebar, Implement Top Navbar

Replace `Sidebar.tsx` + `Topbar.tsx` with a single `Navbar.tsx` component matching the proto's horizontal top-bar pattern.

**Sub-issues:**

#### 1.1.1: Create `Navbar.tsx` Component

- Sticky top, white bg, `backdrop-blur`, `border-b border-gray-100`
- Left: Logo mark (8×8 dark rounded square with emerald circle icon) + "Widby" text (lg bold, tracking-tight)
- Center nav links (authenticated): **Dashboard**, **Strategies**, **Explore**, **Multi-market**, **Reports**
  - Active state: `text-ink` / Inactive: `text-neutral-500`
  - Route matching: Strategies matches `/strategies/*`, Reports matches `/reports` and `/report/*`
- Right: Usage pill + Profile menu (see 1.1.3 and 1.1.4)
- Mobile: hamburger → full-width dropdown with all links + scan counter

#### 1.1.2: Update Protected Layout

- Replace the sidebar + topbar flex composition in `(protected)/layout.tsx`
- New structure: `Navbar` (sticky top) → `<main>` (full-width, `bg-gray-50`, max-w-7xl centered)
- Remove `Sidebar` and `Topbar` imports and all references
- Remove `.app` / `.density-roomy` class-based layout
- Ensure breadcrumb functionality migrates into individual page headers (kicker labels) rather than a global topbar

#### 1.1.3: Scan Counter Usage Pill

- Render to the left of the profile menu, visible only when authenticated
- Layout: `bg-gray-50 rounded-full` pill
- Content: `{scansUsed}/{scansLimit} scans` (monospace, tabular-nums) + dot separator + plan label (capitalized, emerald accent)
- **[SYSTEM DESIGN REQUIRED]**: The production app has no scan quota concept yet. The Supabase schema, auth context, and billing integration need a `scans_used` / `scans_limit` model. Decide whether to back this with Stripe metered billing or a simple row in a `user_quotas` table.

#### 1.1.4: Profile Menu Dropdown

- Trigger: circular button (8×8, `emerald-100` bg, user initial uppercase, `hover:ring-2 ring-emerald-200`)
- Dropdown (w-48, white, shadow-lg, `border border-gray-200`):
  - "Signed in as" label (xs, gray-400) + username (sm, font-medium)
  - Links: "Account settings" → `/settings`, "Plan & billing" → `/settings` (billing tab)
  - Divider
  - "Sign out" (red-600)
- Replaces current `UserMenu.tsx` dropdown which lives in sidebar footer

#### 1.1.5: Route Suppression on Onboarding

- On `/signup` and `/onboarding` routes: hide all nav links, show only "← Back to home" link
- Matches proto behavior where onboarding is distraction-free

#### 1.1.6: Remove Deprecated Navigation Items

- Remove "Niche Finder" nav item (replaced by strategy-based flows)
- Remove "Recommendations" nav item (was a coming-soon stub)
- Add "Multi-market" nav item pointing to new `/agency` route (Epic 5)

---

### Issue 1.2: App Footer

Add a minimal in-app footer matching the proto.

**Sub-issues:**

#### 1.2.1: Create `Footer.tsx` Component

- In-app footer (authenticated routes): white bg, `border-t border-gray-100`, `mt-16 py-4`
- Left: green status dot + "All systems operational" + links (Support, About)
- Right: "© 2026 Widby. All rights reserved." + separator + "A Covariance product."
- All text: `text-xs text-neutral-500`

#### 1.2.2: Route-Aware Footer Rendering

- Marketing routes (`/`, `/pricing`, `/about`, `/contact`): full marketing footer with 4-column grid (Product, Resources, Company columns)
- App routes: minimal footer only
- Add to root or protected layout

---

## Epic 2: Dashboard — Replace Home Page

**Goal:** Replace the current home page (stat cards + hero quick search + recent activity) with the proto's dashboard design featuring first-run banner, usage strip, recommended strategy hero, and cross-linking cards.

### Issue 2.1: Dashboard Data & Context

**Sub-issues:**

#### 2.1.1: Extend Auth/App Context with Scan Quotas

- **[SYSTEM DESIGN REQUIRED]**: Production currently has no global app context like the proto's `AppProvider`. Need to decide: React Context, Zustand, or server-side props.
- Required state: `plan` (free/pro/scale), `scansUsed`, `scansLimit`, `reports[]`, `hasGeneratedReport`, onboarding segment data
- The proto computes `scansLimit` from plan (free=3, pro=30, scale=150)

#### 2.1.2: Dashboard Data Loader

- Adapt `load-dashboard.ts` to fetch: scan quota from new quota source, recent reports from Supabase, user's recommended strategy (from onboarding answers)
- Server-side fetch in `(protected)/page.tsx`

### Issue 2.2: First-Run Banner

- Conditional display: shown until first scan is completed (`!hasGeneratedReport`)
- 2px emerald-300 border, green left accent bar
- Star icon in white circle (emerald-500 bg)
- Headline: "Start here" + subtext: "Three steps to your first report. Takes about five minutes."
- 3 numbered steps with checkmark when complete
- CTA: "Open {starterStrategy.name} →" (ink bg, white text)
- Secondary: "Or browse Explore first (free)" (underlined, gray-500)
- **[SYSTEM DESIGN REQUIRED]**: Requires onboarding-to-strategy routing logic. The proto has `routeOnboardingToStrategy()` mapping (intent, focus) → recommended strategy. This logic needs to be built or ported, and onboarding answers need to be persisted (currently onboarding writes to Supabase but may not store strategy routing fields).

### Issue 2.3: Usage Strip (4-Card Grid)

- `grid-cols-4` responsive layout
- Cards: white bg, `border border-gray-200`, rounded-lg, p-4
- Labels: 10px, gray-400, uppercase, tracking-wide
- Cards:
  1. **Scans remaining**: `{remaining}/{limit}` in emerald-700
  2. **Current plan**: capitalized name + "Manage" link → `/pricing`
  3. **Reports**: count + "View all" link → `/reports`
  4. **Current lens**: starter strategy name or "—" + "Change" link → `/strategies`

### Issue 2.4: Recommended Strategy Hero Card

- Dark gradient bg (`from-gray-900 to-gray-800`), white text
- Icon badge: `emerald-500/20` bg with strategy icon
- Label: "Recommended for you" (xs, emerald-300, uppercase)
- H2: strategy name (2xl bold)
- User question (italic, sm, gray-300)
- CTA: "Run {name} →" (emerald-500 bg) + "See all strategies" (underlined)
- Requires same onboarding routing as 2.2

### Issue 2.5: Secondary Surface Cards (2-Column Grid)

**Sub-issues:**

#### 2.5.1: Explore Banner Card

- White bg, `border-2 border-gray-200`, `hover:border-gray-900`, rounded-xl, p-6
- Sky-tinted icon (sky-100 bg, sky-600 text)
- Title: "Explore cached data"
- Subtitle: "Browse for free — no scans consumed." (italic)
- CTA: "Open Explore" → `/explore`

#### 2.5.2: Multi-Market Banner Card

- Same structure, indigo accents
- Title: "Multi-market scan"
- Subtitle: "For agencies and scaled operators." (italic)
- CTA → `/agency`

### Issue 2.6: Strategy Shortcuts Grid

- Section label: "Your strategy shortcuts" (sm, semibold, uppercase)
- "See all →" link (emerald-700) → `/strategies`
- `grid-cols-2 md:grid-cols-3`, gap-3
- Each card: white bg, border, rounded-lg, p-3, `hover:border-gray-900`
- Icon (7×7 in gray-50 square) + title (sm semibold) + subtitle (xs gray-500, truncated)

### Issue 2.7: Recent Reports Section

- White card, border, rounded-xl, p-5
- Label: "Recent reports" (sm, semibold, uppercase) + "View all →" link
- Empty state: italic, centered, gray-500
- Populated: `divide-y divide-gray-100`, each row: title + subtitle + source badge + scan count (monospace) + arrow

### Issue 2.8: Remove Deprecated Home Components

- Remove `HeroQuickSearch.tsx` (replaced by strategy-first flow)
- Remove `RecommendedMetros.tsx` (replaced by strategy shortcuts + explore cards)
- Remove `SavedSearchesBlock.tsx` (was placeholder)
- Update `StatCardRow.tsx` → repurpose as Usage Strip or remove

---

## Epic 3: Strategy Section — Align Gallery & Detail Flows

**Goal:** The strategy section is closest to parity. Align the gallery page header/copy and detail page results layout, and add the Next Moves cross-linking pattern.

### Issue 3.1: Strategy Gallery — Header & Copy Update

**Sub-issues:**

#### 3.1.1: Update Gallery Header

- Current: H1 "Strategy discovery" + description about ranking lenses
- Proto: Label "Strategies" (xs, gray-400, uppercase) + H1 "Pick a *lens*." (serif, 4xl, "lens" in emerald/accent) + description (base, gray-500, max-w-2xl)
- Add subtext: "Not sure which lens fits? Browse Explore first..." (sm, gray-500)

#### 3.1.2: Add AI-Proof Filter Toggle

- Top-right toggle button
- Off: gray-200 border, white bg / On: emerald-50 bg, emerald-300 border, emerald-700 text
- Icon + "AI-Proof filter on/off" (xs, font-medium)
- Filters strategy cards to show only AI-resilient strategies

#### 3.1.3: Recommendation Banner

- Conditionally displayed when user has onboarding routing data
- Dark bg (ink/gray-900), white text, animated fade-in
- Icon badge (accent/15 bg) + "Our recommendation" label (10px, accent-light)
- Routing rationale text

#### 3.1.4: Strategy Card Layout Updates

- Current cards use CSS variables (--card, --rule) and custom classes
- Proto cards use Tailwind: white bg, border-gray-200, rounded-xl, hover effects, motion animations
- Add: strategy icon with accent-colored bg, user question (italic), lock/unlock badge, "Recommended" badge on starter strategy
- Grid: `grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6`

#### 3.1.5: Locked/Unlocked Sections

- Split gallery into "Available to you" and "Unlock as you progress" sections
- Locked cards show lock icon and are non-clickable
- **[SYSTEM DESIGN REQUIRED]**: Strategy unlock logic. Proto uses `hasGeneratedReport` as the gate — first scan unlocks remaining strategies. Production needs to decide: is this purely client-side state, or persisted per-user in Supabase?

### Issue 3.2: Strategy Detail — Input Forms

**Sub-issues:**

#### 3.2.1: Implement `InputShell` Wrapper

- max-w-2xl centered
- Large strategy icon (14×14, accent-50 bg, rounded-xl)
- H2: "Run {strategy.name}" (xl bold)
- User question (italic, sm, gray-500)
- Form card: white, rounded-xl, border, p-6
- Cost note below: xs gray-400, showing scan cost

#### 3.2.2: Per-Strategy Form Variants

- Each strategy has unique accent color for submit button:
  - Easy Win: emerald-500 | Cash Cow: amber-500 | Blue Ocean: sky-500 | GBP Blitz: rose-500 | Portfolio Builder: violet-500 | Expand & Conquer: indigo-500 | Seasonal Arbitrage: teal-500
- Some strategies have info boxes (e.g., Cash Cow: amber-50 bg, amber-200 border explaining signal weighting)
- Map current `StrategyPageClient.tsx` form inputs to proto form patterns

### Issue 3.3: Strategy Detail — Results Layout

**Sub-issues:**

#### 3.3.1: `StrategyResultHeader` Component

- Shows strategy name, context line (city/service/scope), scan cost consumed
- AI-Proof mode toggle (top-right)

#### 3.3.2: Hero Score Section (Easy Win Example)

- White card, border, rounded-xl, p-8
- `ScoreCircle` (100px, colored border based on score threshold) + verdict text
- Badge strip: time-to-rank (emerald-50), AI Resilience, Confidence (gray-100)

#### 3.3.3: Signals Grid

- Section title (sm, semibold, uppercase)
- Cards: white, border, p-4, rounded-lg
- Each: label (xs, gray-400, uppercase), big value (2xl, bold, monospace), delta arrow (↑/↓, colored)

#### 3.3.4: Composite Opportunity Score

- Large score (3xl, bold, monospace)
- Progress bar (h-1.5, bg-gray-100 with colored fill)
- Helper text (xs, gray-400)

### Issue 3.4: Next Moves Component (Cross-Linking)

**This is a critical UX pattern that appears on strategy results AND report detail pages. It does not exist in production today.**

**Sub-issues:**

#### 3.4.1: Create Shared `NextMoveCard` Component

- Props: `href`, `title`, `subtitle`, `primary?` (boolean)
- Base: `group bg-white rounded-xl border p-4 hover:border-gray-900 transition-colors block` (Link wrapper)
- Border: `border-gray-900` if primary, `border-gray-200` otherwise
- Title: sm, semibold, gray-900
- Subtitle: xs, gray-500, mt-0.5
- CTA: "Continue" + chevron arrow (emerald-700, xs, semibold, `group-hover:gap-2 transition-all`)

#### 3.4.2: Next Moves on Strategy Results

- Section title: "NEXT MOVES" (sm, semibold, uppercase, gray-900)
- Grid: `md:grid-cols-3 gap-3` (or `grid-cols-2` when only 2 cards)
- **Per-strategy card configurations:**
  - **Easy Win results**: "Try another lens" → `/strategies` | "Browse similar markets" → `/explore` | "Generate Competitor Intel" → `/competitor-intel?city=X&service=Y` (primary)
  - **Cash Cow results**: "Check ease of rank" → `/strategies/easy_win` | "Try another lens" → `/strategies` | "Competitor Intel on #1" → `/competitor-intel?...` (primary)
  - **Blue Ocean results**: "Validate rank ease" → `/strategies/easy_win` | "Check cities for #1" → `/explore` (primary) — only 2 cards
  - Other strategies follow similar patterns with context-aware subtitles

#### 3.4.3: Next Moves on Report Detail

- Same component, different card set:
  - "Run Competitor Intel" → `/competitor-intel?city=X&service=Y` (primary)
  - "Check the economics" → `/strategies/cash_cow`
  - "Find lookalike cities" → `/strategies/expand_conquer`

#### 3.4.4: Strategy Guidance Block (Report Only)

- Dark gradient card (`from-gray-900 to-gray-800`), white text, rounded-xl, p-6
- Label: "Strategy guidance" (xs, emerald-300, semibold, uppercase)
- H2: guidance headline (serif, 2xl)
- Strategy text (sm, gray-200)
- "Priority actions" label + numbered list (monospace 00 format, sm, gray-100)
- Est. time to rank (sm, gray-300, bottom, border-t white/10)
- **[SYSTEM DESIGN REQUIRED]**: Guidance data (headline, strategy text, priority actions, time-to-rank) is not in the current scoring pipeline output. Either the M9 report assembly needs to generate this, or a separate LLM pass is needed post-scoring. Define the data contract.

---

## Epic 4: Explore Page — Subheader & Strategy Jump

**Goal:** Explore is already close. Update the subheader copy and add the "jump to a strategy" cross-link.

### Issue 4.1: Update Explore Page Header

**Sub-issues:**

#### 4.1.1: Update Subheader Text

- Current: "Browse the data layer for free. Narrow down by demographics, then spend scans on the markets that need fresh numbers."
- Proto: Same text, but add jump link below: "Know what you want? Jump to a strategy →" (text-emerald-700, links to `/strategies`)

#### 4.1.2: Add Scans Indicator (Header Right)

- Dark pill (gray-900 bg, white text, rounded-lg, px-4, py-2.5)
- Label: "Scans this month" (10px, gray-400, uppercase)
- Big number: scansRemaining (xl, bold, monospace)
- Helper: "/ {limit} remaining" (xs, gray-400)
- Progress bar below (h-1, bg-gray-800, emerald-500 fill based on usage %)
- This requires the scan quota context from Epic 1 / Issue 1.1.3

### Issue 4.2: Explore Table — Minor Alignment

**Sub-issues:**

#### 4.2.1: Column Alignment

- Proto columns: City, Pop., Median HH income, Biz density, Growth YoY, Services cached, Best opportunity
- Production columns: City, Pop., Median HH income, Biz density, Growth YoY, Best score, Services, Expand
- Rename "Best score" → "Best opportunity", add mini colored bar next to score
- Move "Services" column to "Services cached" position
- Proto adds avg note below best opportunity score

#### 4.2.2: Table Footer

- Add footer text: "All data cached · costs no scans · last refreshed within 7 days" (xs, gray-400)

#### 4.2.3: City Drawer — Service Selection for Fresh Scan

- Proto drawer has service checkboxes with "Select all / Deselect all"
- Each service row shows: checkbox + label + archetype + AI resilience + last scored date + opportunity score
- Footer CTA: "{N} services selected" + "Run fresh scan →" button
- Confirm modal with cost preview and remaining scans
- **[SYSTEM DESIGN REQUIRED]**: The "Run fresh scan from Explore" flow currently uses a different path than strategy-based scoring. Need to unify the scan execution and quota deduction into a single backend flow.

---

## Epic 5: Multi-Market Page (New)

**Goal:** Implement the `/agency` route — a batch scan configuration page for agencies and scaled operators. This is entirely new functionality.

**[SYSTEM DESIGN REQUIRED]**: This is a new feature end-to-end. Needs system design covering: batch scan orchestration (queueing N city×service combos), scan cost calculation and deduction, progress tracking, and how results map to individual reports.

### Issue 5.1: Create `/agency` Route & Page Shell

- New route: `(protected)/agency/page.tsx`
- Page header: Label "Multi-market scan" (xs, gray-400, uppercase) + H1 "Scale your analysis across markets" (2xl bold)
- Description: "Configure a scan across 10–100 city + service combos..."
- Scans available indicator (top-right, gray-900 bg pill): "{remaining} / {limit}" (xl, bold, monospace)

### Issue 5.2: Three-Step Flow State Machine

- State: `"configure" | "confirm" | "complete"`
- Step transitions managed via local component state

**Sub-issues:**

#### 5.2.1: Step 1 — Configure

Four card sections (white bg, border, rounded-xl, p-5):

1. **Pick a strategy lens**: Button group (Easy Win, Cash Cow, Blue Ocean, GBP Blitz). Active = gray-900 bg, white text. Inactive = white bg, gray-200 border.
2. **City criteria**: Population range (two inputs, step 5000) + Income range (two inputs, step 1000) + `StateMultiselect` component + City cap dropdown (10/25/50/100)
   - Summary line: "{N} cities match your criteria. Example: [first 3]..."
3. **Services to scan**: Toggleable pills (rounded-full). Unselected = white/border-gray-200. Selected = emerald-500/white text.
   - Note: "Each city × service combo costs ~0.6 scans"
4. **Run summary**: 4-metric grid (cities matched, services, combinations, est. scan cost in emerald-700) + affordability status message (blue/yellow/green) + "Review & run →" button

#### 5.2.2: Step 2 — Confirm

- Review card: strategy lens, cities count, services per city, total combos, cost (emphasized), remaining after run
- Buttons: "Back" (text gray-500) + "Run scan" (emerald-500)

#### 5.2.3: Step 3 — Complete

- Center card: emerald checkmark icon + "Scan queued" (xl bold)
- "{N} combos · {M} scans consumed · running on pipeline..."
- Buttons: "Back to dashboard" (emerald-500) + "Configure another run" (text gray-500)

### Issue 5.3: Port `StateMultiselect` Component

- The proto has a `StateMultiselect.tsx` with 50-state popover, search, and chip display
- Production Explore already has a similar state filter — extract into shared component or port proto's version
- Chip display: up to 6 chips + "+N" overflow counter

### Issue 5.4: Multi-Market Backend

- **[SYSTEM DESIGN REQUIRED]**: No backend exists for batch scanning. Need:
  - `POST /api/agent/batch-scan` endpoint accepting strategy lens, city criteria, service list, city cap
  - Queue system (simple DB queue or proper job queue) to process N combos sequentially
  - Scan cost pre-calculation and atomic deduction
  - Progress reporting (websocket or polling)
  - Each combo produces one report, all linked to a batch run ID

### Issue 5.5: Add "Multi-market" to Navbar

- Already covered in Issue 1.1.6, but ensure the route `/agency` is correctly linked and active-state matching works for `/agency/*`

---

## Epic 6: Reports Page — Match Proto Layout

**Goal:** Update the reports list page to match the proto's search + sort + card list design, and update report detail with strategy guidance + Next Moves.

### Issue 6.1: Reports List Redesign

**Sub-issues:**

#### 6.1.1: Update Page Header

- Current: Summary stat cards (total reports, most common strategy) + search + archetype filter
- Proto: Label "History" (xs, gray-400, uppercase) + H1 "Reports" (2xl bold) + Description: "Every scan produces a report. Reports don't expire, don't cost extra scans to revisit."

#### 6.1.2: Search & Sort Controls

- Search input: full-width with icon, placeholder "Search your reports", `border-gray-200 focus:border-gray-400`
- Sort dropdown: "Newest first" / "Oldest first" / "Most scans used"
- Count: "{filtered} / {total}" (xs, gray-400, monospace)
- Remove the stat cards above the search (production-specific, not in proto)

#### 6.1.3: Report List as Card Rows

- Container: white bg, rounded-xl, border, `divide-y divide-gray-100`
- Each row (Link wrapper): `flex items-center justify-between gap-4 px-5 py-4 hover:bg-gray-50`
  - Title (sm, font-semibold, gray-900, truncate)
  - Source badge (10px, gray-100 bg, gray-600 text, rounded-full, uppercase) — e.g., "Easy Win", "Explore", "Multi-market"
  - Subtitle (sm, gray-500, truncate)
  - Meta: "formatDate · {scansConsumed} scans" (xs, gray-400, monospace)
  - Arrow icon (right)
- Rows link to `/report/{id}` (not a modal — proto uses a dedicated page)

#### 6.1.4: Empty State

- Large gray icon (12×12, gray-100 bg, gray-400)
- "No reports yet" (font-semibold)
- "Run your first scan from a strategy, explore, or multi-market batch..."
- CTAs: "Pick a strategy" (ink bg) + "Browse Explore" (white border)

#### 6.1.5: Migrate Report Detail from Modal to Page

- Current: clicking a report opens `ReportDetailModal` as an overlay
- Proto: report detail is at `/report/[id]` as a full page
- Create `(protected)/report/[id]/page.tsx` with the full report layout
- Keep modal available as optional quick-view, but primary navigation goes to page

### Issue 6.2: Report Detail — Strategy Guidance Section

- Add below tab content area (Competition/Demand/Monetization/AI Resilience)
- Dark gradient card: see Issue 3.4.4
- Requires guidance data from backend

### Issue 6.3: Report Detail — Next Moves Section

- Add below strategy guidance: see Issue 3.4.3
- Cards: "Run Competitor Intel" (primary) → `/competitor-intel?city=X&service=Y`, "Check the economics" → `/strategies/cash_cow`, "Find lookalike cities" → `/strategies/expand_conquer`

### Issue 6.4: Report Detail — Header Updates

**Sub-issues:**

#### 6.4.1: Report Header Layout

- Breadcrumb: "Reports / Report" (sm, gray-400, italic)
- H1: "{niche}" (serif, 3xl)
- Subtitle: "{metro}, {state} · {date}" (serif, italic, sm, gray-500)
- Right controls: ExportMenu + "Delete report" link (sm, gray-500, hover:red-600)

#### 6.4.2: Meta Pills Row

- Below header: scoring version pill, weighting selector, "Standard" pill
- Style: gray-100 bg, rounded-full, text-sm

#### 6.4.3: Headline Scores Band

- `grid-cols-3 md:grid-cols-6 gap-4`
- 6 cells: Demand, Organic comp., Local comp., Monetization, AI resilience, Opportunity
- Each: big number (3xl, bold, color-coded) + bar (h-[3px]) + label (italic, xs, gray-500)

#### 6.4.4: Export Menu

- **[SYSTEM DESIGN REQUIRED]**: Proto has tiered export (PDF/CSV/Share/JSON) using `@react-pdf/renderer`. Production needs to decide: add `@react-pdf/renderer` as dependency, or implement server-side PDF generation via the Python pipeline.

#### 6.4.5: Delete Confirmation Modal

- Modal: white, rounded-2xl, p-6
- H3: "Delete this report?" (serif, 2xl)
- Cancel + "Delete report" (red-600 bg) buttons
- **Note**: Current production uses `archive_account_report` RPC — preserve this backend, just update the UI.

---

## Epic 7: Account & Settings — Update Without Losing Functions

**Goal:** Align the settings/account page with the proto's cleaner card layout while preserving production's critical functions (password reset, Stripe billing portal, admin link).

### Issue 7.1: Account Page Redesign

**Sub-issues:**

#### 7.1.1: Profile Section

- White card, border, rounded-xl, p-6
- H2: "Profile" (font-semibold)
- Grid: `sm:grid-cols-2 gap-4 text-sm`
- Fields: Name, Email, Segment (if available), Referred by (if coach ref exists)
- Source data from Supabase auth metadata (already available)

#### 7.1.2: Plan & Usage Section

- White card, border, rounded-xl, p-6
- Header: "Plan & Usage" (semibold) + "Upgrade / Change Plan" link (emerald-600) → **preserve current Stripe billing portal link** (`/api/billing/portal`)
- Grid: `sm:grid-cols-3 gap-4 text-sm` — Current Plan, Scans Used, Scans Remaining
- Usage bar: h-2, bg-gray-200, rounded-full, emerald-500 fill (amber-500 if >80% used)
- **Critical**: Do not break Stripe checkout or portal integration. The "Upgrade / Change Plan" link should call the existing `/api/billing/portal` endpoint.

#### 7.1.3: Saved Reports Preview

- White card, border, rounded-xl, p-6
- Header: "Saved Reports" (semibold) + "View all →" link → `/reports`
- Show first 5 reports with title + subtitle + arrow
- Empty: "No reports yet..." (sm, gray-400)

#### 7.1.4: Danger Zone / Sign Out

- Card with "Sign out" link (sm, gray-500, hover:red-600)
- Preserve production sign-out logic (Supabase `signOut()`)

### Issue 7.2: Preserve Password Reset

- Keep `/settings/password` route and `PasswordResetForm` component
- Ensure it's reachable from the new account page (add link in Profile section or as separate card)

### Issue 7.3: Preserve Admin Dashboard Link

- Current: UserMenu has "Admin dashboard" external link
- Move to: Profile dropdown in new Navbar (Issue 1.1.4) — show only for admin users
- Preserve the external link to `{adminUrl}`

---

## Epic 8: Competitor Intel Page (New — Referenced by Next Moves)

**Goal:** The Next Moves cards reference `/competitor-intel?city=X&service=Y`. This page needs to exist for the cross-linking to work.

**[SYSTEM DESIGN REQUIRED]**: Entirely new feature. Needs system design for SERP competitor data retrieval, display, and how it relates to the existing scoring pipeline.

### Issue 8.1: Create `/competitor-intel` Route

- New route: `(protected)/competitor-intel/page.tsx`
- Accepts query params: `city`, `service`
- Proto has `CompetitorIntelClient.tsx` with SERP drilldown
- At minimum, implement a stub page that accepts the params and shows a "Coming soon" state, so Next Moves links don't 404

### Issue 8.2: Competitor Intel UI (Full Implementation)

- Header: strategy lens icon + "Competitor Intel" label
- City + service context display
- SERP results table: rank, URL, domain authority, page authority, backlinks
- Competitor cards with strength/weakness indicators
- **Defer to separate system design document** — this is a full feature build

---

## Epic 9: Design System Alignment

**Goal:** Converge typography, colors, and shared components to match the proto's visual language.

### Issue 9.1: Typography Migration

**Sub-issues:**

#### 9.1.1: Font Stack Update

- Current: Source Serif 4 (serif), Inter (sans), JetBrains Mono (mono)
- Proto: DM Serif Display (serif), Inter (sans), JetBrains Mono (mono)
- Decision needed: adopt DM Serif Display or keep Source Serif 4. If adopting, update `layout.tsx` font imports and CSS variables.

#### 9.1.2: Heading Patterns

- Proto uses serif for large H1s (strategy names, report titles, "Pick a *lens*.")
- Monospace for all numeric values (scores, counts, metrics)
- Italic serif for signal labels and report metadata

### Issue 9.2: Color System Alignment

- Proto accent: emerald-500/600/700 (primary CTA, active states)
- Strategy accents: sky (blue ocean), amber (cash cow), indigo (expand), violet (portfolio), teal (seasonal), rose (gbp)
- Score colors: emerald ≥80, sky ≥60, amber ≥40, red <40
- Production currently uses CSS variables (`--accent`, `--ink`, etc.) — migrate to Tailwind utility classes matching proto, or update CSS variable values

### Issue 9.3: Shared Component Library

**Sub-issues:**

#### 9.3.1: Extract `NextMoveCard` to Shared Components

- Used on strategy results, report detail, and potentially dashboard
- Single component file in `src/components/NextMoveCard.tsx`

#### 9.3.2: Extract `ScoreCircle` and `Bar` to Shared Components

- Used across strategy results, report detail, explore table
- Consistent color thresholds (80/60/40 breakpoints)

#### 9.3.3: Extract `StateMultiselect` to Shared Components

- Used in Explore filters and Multi-market configuration
- Port from proto or refactor production's existing state filter

---

## System Design Requirements Summary

The following items need system design documents before implementation:

| ID | Area | Description |
|----|------|-------------|
| SD-1 | Scan Quotas | User quota model (scans_used, scans_limit), plan tiers, Supabase schema, billing integration |
| SD-2 | Onboarding → Strategy Routing | Persist onboarding answers, `routeOnboardingToStrategy()` logic, recommended strategy resolution |
| SD-3 | Strategy Unlock Logic | Gate mechanism for locked/unlocked strategies, persistence model |
| SD-4 | Strategy Guidance Data | Data contract for guidance headline, strategy text, priority actions, time-to-rank. LLM generation vs. template. |
| SD-5 | Multi-Market Batch Scanning | Batch scan orchestration, queueing, cost calculation, progress tracking, report linkage |
| SD-6 | Unified Scan Execution | Single backend flow for scan deduction across strategies, explore fresh scans, and multi-market batches |
| SD-7 | Competitor Intel | SERP competitor data retrieval, display model, relationship to scoring pipeline |
| SD-8 | Report Export | PDF/CSV/JSON export implementation approach (client-side @react-pdf vs. server-side generation) |

---

## Dependency Graph

```
Epic 1 (App Frame)
  ├── Epic 2 (Dashboard) — needs navbar + scan quota context
  ├── Epic 4 (Explore) — needs scan indicator from navbar context
  ├── Epic 5 (Multi-market) — needs new nav item + scan quota
  ├── Epic 6 (Reports) — needs new nav routing
  └── Epic 7 (Settings) — needs profile menu migration

Epic 3 (Strategies)
  └── Epic 8 (Competitor Intel) — Next Moves links require this route

Epic 9 (Design System) — can run in parallel, informs all other epics
```

**Recommended execution order:**
1. Epic 9 (Design System) — establish shared primitives first
2. Epic 1 (App Frame) — foundational layout change
3. Epic 2 (Dashboard) — highest-visibility change
4. Epic 3 (Strategies) — closest to parity, includes Next Moves
5. Epic 4 (Explore) — minor updates
6. Epic 6 (Reports) — moderate redesign
7. Epic 7 (Settings) — preserve critical functions
8. Epic 5 (Multi-market) — new feature, needs backend
9. Epic 8 (Competitor Intel) — new feature, can stub initially
