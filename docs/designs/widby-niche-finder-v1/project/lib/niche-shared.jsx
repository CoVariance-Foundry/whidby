// Shared data + small components used by all 3 variations.
// Exposed via `window` so sibling <script type="text/babel"> files can use them.

const ARCHETYPES = [
  { id: "AGG",       title: "Aggregator Dominated",   short: "Aggregator‑dominated", glyph: "arch-agg",       icon: "■", hint: "Yelp, HomeAdvisor own the SERP",        strat: "Long‑tail first, skip head terms" },
  { id: "PACK_FORT", title: "Local Pack Fortified",   short: "Pack, fortified",           glyph: "arch-pack-fort", icon: "▲", hint: "Strong GBP, actively reviewed",          strat: "Adjacent sub‑niches, long horizon" },
  { id: "PACK_EST",  title: "Local Pack Established", short: "Pack, established",         glyph: "arch-pack-est",  icon: "◆", hint: "Moderate pack, reviews < 100",           strat: "GBP‑first, 4‑8 month build" },
  { id: "PACK_VULN", title: "Local Pack Vulnerable",  short: "Pack, vulnerable",          glyph: "arch-pack-vuln", icon: "✔", hint: "Weak pack, reviews ≤ 30",            strat: "GBP + site combo, 2‑4 mo" },
  { id: "FRAG_WEAK", title: "Fragmented Weak",        short: "Fragmented, weak",          glyph: "arch-frag-weak", icon: "✦", hint: "Many local sites, low DA",               strat: "Classic rank‑and‑rent" },
  { id: "FRAG_COMP", title: "Fragmented Competitive", short: "Fragmented, comp.",         glyph: "arch-frag-comp", icon: "◯", hint: "Local sites with real authority",        strat: "Link building + longer timeline" },
  { id: "BARREN",    title: "Barren",                 short: "Barren",                     glyph: "arch-barren",    icon: "○", hint: "Nobody competing for this SERP",        strat: "Low‑hanging if demand exists" },
  { id: "MIXED",     title: "Mixed Signals",          short: "Mixed",                     glyph: "arch-mixed",     icon: "◉", hint: "No dominant SERP pattern",               strat: "Inspect gaps in SERP manually" },
];

const CITY_SUGGESTIONS = [
  { name: "Phoenix",     state: "AZ", tier: "Major",    pop: "1.6M" },
  { name: "Philadelphia",state: "PA", tier: "Major",    pop: "1.6M" },
  { name: "Pittsburgh",  state: "PA", tier: "Mid‑tier", pop: "303K" },
  { name: "Portland",    state: "OR", tier: "Mid‑tier", pop: "652K" },
  { name: "Peoria",      state: "IL", tier: "Small",    pop: "113K" },
  { name: "Plano",       state: "TX", tier: "Mid‑tier", pop: "289K" },
];

const NICHE_SUGGESTIONS = [
  "roofing", "roof repair", "roof cleaning", "rodent control", "rug cleaning",
];

const SAMPLE_RESULTS = [
  { metro: "Tucson, AZ",        niche: "roofing",       score: 82, archetypeId: "PACK_VULN", tier: "easy", tierLabel: "Easy",       aio: 4,  delta: "+5.4" },
  { metro: "Albuquerque, NM",   niche: "roofing",       score: 78, archetypeId: "FRAG_WEAK", tier: "easy", tierLabel: "Easy",       aio: 6,  delta: "+3.1" },
  { metro: "Boise, ID",         niche: "roofing",       score: 74, archetypeId: "PACK_VULN", tier: "med",  tierLabel: "Moderate",   aio: 8,  delta: "+2.0" },
  { metro: "Chattanooga, TN",   niche: "roofing",       score: 71, archetypeId: "FRAG_WEAK", tier: "med",  tierLabel: "Moderate",   aio: 5,  delta: "+1.2" },
  { metro: "Fort Wayne, IN",    niche: "roofing",       score: 69, archetypeId: "BARREN",    tier: "easy", tierLabel: "Easy",       aio: 3,  delta: "+0.9" },
  { metro: "Des Moines, IA",    niche: "roofing",       score: 66, archetypeId: "PACK_EST",  tier: "med",  tierLabel: "Moderate",   aio: 7,  delta: "‑0.4" },
  { metro: "Grand Rapids, MI",  niche: "roofing",       score: 63, archetypeId: "MIXED",     tier: "med",  tierLabel: "Moderate",   aio: 9,  delta: "+0.2" },
  { metro: "Phoenix, AZ",       niche: "roofing",       score: 42, archetypeId: "AGG",       tier: "hard", tierLabel: "Very hard",  aio: 22, delta: "‑1.8" },
];

const RECENT_SEARCHES = [
  { mode: "niche",    label: "roofing · Phoenix, AZ",                   ts: "2h" },
  { mode: "niche",    label: "water damage restoration · Tampa, FL",    ts: "yesterday" },
  { mode: "strategy", label: "Pack, vulnerable · score ≥ 70",       ts: "yesterday" },
  { mode: "niche",    label: "garage door repair · Austin, TX",         ts: "3d" },
];

const SAVED_SEARCHES = [
  { mode: "strategy", label: "Mid‑tier aggregator plays",       sub: "Aggregator‑dominated · mid‑tier · score ≥ 60" },
  { mode: "niche",    label: "Roofing sweep \u2014 Mountain West",     sub: "roofing · 5 cities" },
  { mode: "strategy", label: "Fast‑path pack opportunities",    sub: "Pack vulnerable · score ≥ 72" },
];

// ── Tiny inline icons ────────────────────────────────────────────
const Icon = ({ d, size = 14, sw = 1.6, fill = "none" }) => (
  <svg viewBox="0 0 24 24" width={size} height={size}
       fill={fill} stroke="currentColor" strokeWidth={sw}
       strokeLinecap="round" strokeLinejoin="round">
    <path d={d} />
  </svg>
);
const I = {
  search:   "M21 21l-4.3-4.3M17 11a6 6 0 11-12 0 6 6 0 0112 0z",
  pin:      "M12 2v6m0 0L8 12h8l-4-4zm0 6v14",
  clock:    "M12 8v4l3 2M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
  arrow:    "M5 12h14M13 6l6 6-6 6",
  star:     "M12 3l2.9 6 6.6.9-4.8 4.5 1.2 6.6L12 17.9 6.1 21l1.2-6.6L2.5 9.9 9.1 9z",
  map:      "M9 20l-6-2V4l6 2m0 14V6m0 14l6-2m-6-12l6 2m0 0v14m0-14l6-2v14l-6 2",
  mapPin:   "M12 21s-7-7-7-12a7 7 0 1114 0c0 5-7 12-7 12zm0-9a3 3 0 100-6 3 3 0 000 6z",
  building: "M6 21V3h8v18M14 9h4v12M9 7h2M9 11h2M9 15h2",
  sliders:  "M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0M14 4v4M8 10v4M16 16v4",
  sparkle:  "M12 3l1.8 4.5L18 9l-4.2 1.5L12 15l-1.8-4.5L6 9l4.2-1.5zM19 2l.8 2L22 5l-2.2 1L19 8l-.8-2L16 5l2.2-1z",
  filter:   "M4 6h16M7 12h10M10 18h4",
  grid:     "M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z",
  list:     "M4 6h16M4 12h16M4 18h16",
  check:    "M5 13l4 4L19 7",
  x:        "M6 6l12 12M18 6L6 18",
  bell:     "M15 17h5l-1.4-1.4A2 2 0 0118 14.2V11a6 6 0 10-12 0v3.2c0 .5-.2 1-.6 1.4L4 17h5m6 0v1a3 3 0 01-6 0v-1m6 0H9",
  plus:     "M12 5v14M5 12h14",
  save:     "M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2zM17 21v-8H7v8M7 3v5h8",
  chevron:  "M6 9l6 6 6-6",
  up:       "M12 19V5M5 12l7-7 7 7",
  home:     "M3 11l9-8 9 8v10a2 2 0 01-2 2h-3v-7h-8v7H5a2 2 0 01-2-2V11z",
  beaker:   "M9 3v6l-5 9a2 2 0 001.8 3h12.4A2 2 0 0020 18l-5-9V3M9 3h6",
  target:   "M12 12m-9 0a9 9 0 1118 0 9 9 0 11-18 0M12 12m-5 0a5 5 0 1110 0 5 5 0 11-10 0M12 12m-1 0a1 1 0 112 0 1 1 0 11-2 0",
  compass:  "M12 22a10 10 0 110-20 10 10 0 010 20zM15.5 8.5l-2 5-5 2 2-5z",
};

// ── Sidebar ──────────────────────────────────────────────────────
const SIDEBAR_LINKS = {
  home:    "Widby Home.html",
  finder:  "Niche Search.html",
  reports: "Widby Reports.html",
};

function Sidebar({ active = "finder" }) {
  const Item = ({ id, label, d }) => {
    const href = SIDEBAR_LINKS[id];
    const content = (
      <>
        <Icon d={d} /> {label}
      </>
    );
    const cls = "sidebar-item" + (active === id ? " active" : "");
    return href ? (
      <a href={href} className={cls} style={{textDecoration:"none"}}>{content}</a>
    ) : (
      <div className={cls}>{content}</div>
    );
  };
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="sidebar-brand-mark">W</div>
        Widby
      </div>
      <Item id="home"    label="Home"            d={I.home} />
      <Item id="finder"  label="Niche finder"    d={I.search} />
      <Item id="recs"    label="Recommendations" d={I.target} />
      <Item id="reports" label="Reports"         d={I.list} />
      <div className="sidebar-section">Saved</div>
      {SAVED_SEARCHES.slice(0, 3).map((s, i) => (
        <div key={i} className="sidebar-item">
          <Icon d={I.star} /> <span style={{overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap"}}>{s.label}</span>
        </div>
      ))}
      <div className="sidebar-foot">
        <div className="sidebar-foot-av">AR</div>
        <div>
          <div style={{color:"var(--ink)", fontWeight:500}}>Alex Rivera</div>
          <div style={{color:"var(--ink-3)", fontSize:11}}>Pro plan</div>
        </div>
      </div>
    </aside>
  );
}

function Topbar({ crumbs }) {
  return (
    <div className="topbar">
      <div className="crumb">
        {crumbs.map((c, i) => (
          <React.Fragment key={i}>
            {i > 0 && <span>/</span>}
            {i === crumbs.length - 1 ? <b>{c}</b> : <span>{c}</span>}
          </React.Fragment>
        ))}
      </div>
      <div className="topbar-actions">
        <button className="icon-btn" title="Notifications"><Icon d={I.bell} /></button>
        <button className="btn-ghost"><Icon d={I.save} /> Save search</button>
        <button className="btn-primary"><Icon d={I.plus} /> New report</button>
      </div>
    </div>
  );
}

// ── City autocomplete input ──────────────────────────────────────
function CityField({ value, onChange, label = "City" }) {
  const [open, setOpen] = React.useState(false);
  const [q, setQ] = React.useState(value || "P");
  const matches = CITY_SUGGESTIONS.filter(c =>
    c.name.toLowerCase().startsWith(q.toLowerCase())
  );
  return (
    <div style={{ position: "relative", flex: 1, minWidth: 0 }}>
      <div className="field-label">{label}</div>
      <div className="input-wrap">
        <Icon d={I.mapPin} />
        <input
          value={q}
          onChange={(e) => { setQ(e.target.value); onChange && onChange(e.target.value); }}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
          placeholder="Phoenix, Tucson, Boise…"
        />
        <span className="input-kbd">↵</span>
      </div>
      {open && matches.length > 0 && (
        <div className="ac">
          {matches.map((c, i) => (
            <div key={c.name} className={"ac-item" + (i === 0 ? " selected" : "")}>
              <div className="ac-item-main">
                <Icon d={I.mapPin} />
                <div>
                  <b>{c.name}, {c.state}</b>
                  <div style={{fontSize:11, color:"var(--ink-3)", marginTop:1}}>{c.pop} population</div>
                </div>
              </div>
              <span className="ac-tier">{c.tier}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function NicheField({ value, onChange, label = "Niche" }) {
  return (
    <div style={{ flex: 1, minWidth: 0 }}>
      <div className="field-label">{label}</div>
      <div className="input-wrap">
        <Icon d={I.search} />
        <input
          defaultValue={value || "roofing"}
          onChange={(e) => onChange && onChange(e.target.value)}
          placeholder="roofing, plumbing, window cleaning…"
        />
      </div>
    </div>
  );
}

// ── Results table shared across variations ─────────────────────
function Results({ limit = 6, showHeader = true, tools = true }) {
  const rows = SAMPLE_RESULTS.slice(0, limit);
  return (
    <div>
      {showHeader && (
        <div className="results-head">
          <div>
            <span className="results-title">Matching opportunities</span>
            <span className="results-count" style={{marginLeft:10}}>
              {SAMPLE_RESULTS.length} metros · sorted by opportunity score
            </span>
          </div>
          {tools && (
            <div className="results-tools">
              <button className="btn-ghost"><Icon d={I.filter} /> Filter</button>
              <button className="btn-ghost"><Icon d={I.list} /> List</button>
              <button className="btn-ghost"><Icon d={I.map} /> Map</button>
            </div>
          )}
        </div>
      )}
      <div className="results">
        <div className="res-row head">
          <div>Metro</div>
          <div>Archetype</div>
          <div>Score</div>
          <div>Difficulty</div>
          <div>Signals</div>
          <div></div>
        </div>
        {rows.map((r, i) => {
          const arch = ARCHETYPES.find(a => a.id === r.archetypeId);
          return (
            <div key={i} className="res-row">
              <div>
                <div className="res-metro">{r.metro}</div>
                <div className="res-metro-sub">{r.niche}</div>
              </div>
              <div>
                <span className={"badge " + arch.glyph}>
                  <span className="badge-dot" style={{background:"currentColor"}}></span>
                  {arch.short}
                </span>
              </div>
              <div>
                <div className="score">{r.score}</div>
                <div className="score-bar"><div style={{width: r.score + "%"}}/></div>
              </div>
              <div><span className={"tier " + r.tier}>{r.tierLabel}</span></div>
              <div style={{fontSize:11.5, color:"var(--ink-2)", display:"flex", flexDirection:"column", gap:2}}>
                <span>AIO {r.aio}% · Δ {r.delta}</span>
                <span style={{color:"var(--ink-3)"}}>{arch.strat}</span>
              </div>
              <div><button className="res-open"><Icon d={I.arrow} /></button></div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Tweaks panel ─────────────────────────────────────────────────
function TweaksPanel({ open, tweaks, setTweaks }) {
  const set = (k, v) => setTweaks((t) => ({ ...t, [k]: v }));
  const Seg = ({ k, opts }) => (
    <div className="tweaks-seg">
      {opts.map((o) => (
        <button key={o.v} className={tweaks[k] === o.v ? "on" : ""} onClick={() => set(k, o.v)}>
          {o.label}
        </button>
      ))}
    </div>
  );
  return (
    <div className={"tweaks" + (open ? " open" : "")}>
      <h4>Density</h4>
      <Seg k="density" opts={[{v:"roomy", label:"Roomy"}, {v:"compact", label:"Compact"}]} />
      <h4>Strategy picker</h4>
      <Seg k="strategyStyle" opts={[
        {v:"presets", label:"Presets"},
        {v:"chips",   label:"Chips"},
        {v:"matrix",  label:"Matrix"},
      ]} />
    </div>
  );
}

Object.assign(window, {
  ARCHETYPES, CITY_SUGGESTIONS, NICHE_SUGGESTIONS, SAMPLE_RESULTS,
  RECENT_SEARCHES, SAVED_SEARCHES,
  Icon, I, Sidebar, Topbar, CityField, NicheField, Results, TweaksPanel,
});
