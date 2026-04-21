// shared.jsx — primitives reused across Widby niche-search variations
// All components live inside a .app container that sets dark tokens.

const { useState, useRef, useEffect, useMemo } = React;

// ─────────────────────────────────────────────────────────────
// Reference data
// ─────────────────────────────────────────────────────────────
const US_CITIES = [
  { name: "Phoenix", state: "AZ", pop: "1.6M", tier: "major" },
  { name: "Tucson", state: "AZ", pop: "542k", tier: "mid" },
  { name: "Mesa", state: "AZ", pop: "504k", tier: "mid" },
  { name: "Scottsdale", state: "AZ", pop: "241k", tier: "mid" },
  { name: "Austin", state: "TX", pop: "964k", tier: "major" },
  { name: "Dallas", state: "TX", pop: "1.3M", tier: "major" },
  { name: "Houston", state: "TX", pop: "2.3M", tier: "major" },
  { name: "San Antonio", state: "TX", pop: "1.5M", tier: "major" },
  { name: "Fort Worth", state: "TX", pop: "918k", tier: "mid" },
  { name: "El Paso", state: "TX", pop: "679k", tier: "mid" },
  { name: "Plano", state: "TX", pop: "285k", tier: "mid" },
  { name: "Denver", state: "CO", pop: "715k", tier: "major" },
  { name: "Colorado Springs", state: "CO", pop: "478k", tier: "mid" },
  { name: "Boulder", state: "CO", pop: "108k", tier: "small" },
  { name: "Seattle", state: "WA", pop: "737k", tier: "major" },
  { name: "Spokane", state: "WA", pop: "229k", tier: "mid" },
  { name: "Tacoma", state: "WA", pop: "219k", tier: "mid" },
  { name: "Portland", state: "OR", pop: "652k", tier: "major" },
  { name: "Eugene", state: "OR", pop: "176k", tier: "small" },
  { name: "Salem", state: "OR", pop: "175k", tier: "small" },
  { name: "Charlotte", state: "NC", pop: "897k", tier: "major" },
  { name: "Raleigh", state: "NC", pop: "470k", tier: "mid" },
  { name: "Durham", state: "NC", pop: "285k", tier: "mid" },
  { name: "Asheville", state: "NC", pop: "94k", tier: "small" },
  { name: "Nashville", state: "TN", pop: "689k", tier: "major" },
  { name: "Memphis", state: "TN", pop: "628k", tier: "major" },
  { name: "Knoxville", state: "TN", pop: "192k", tier: "small" },
  { name: "Chattanooga", state: "TN", pop: "181k", tier: "small" },
  { name: "Atlanta", state: "GA", pop: "499k", tier: "major" },
  { name: "Savannah", state: "GA", pop: "147k", tier: "small" },
  { name: "Augusta", state: "GA", pop: "202k", tier: "small" },
  { name: "Orlando", state: "FL", pop: "307k", tier: "mid" },
  { name: "Tampa", state: "FL", pop: "398k", tier: "mid" },
  { name: "Jacksonville", state: "FL", pop: "949k", tier: "major" },
  { name: "Miami", state: "FL", pop: "442k", tier: "major" },
  { name: "St. Petersburg", state: "FL", pop: "258k", tier: "mid" },
  { name: "Fort Lauderdale", state: "FL", pop: "183k", tier: "small" },
  { name: "Columbus", state: "OH", pop: "905k", tier: "major" },
  { name: "Cleveland", state: "OH", pop: "372k", tier: "mid" },
  { name: "Cincinnati", state: "OH", pop: "309k", tier: "mid" },
  { name: "Toledo", state: "OH", pop: "270k", tier: "mid" },
  { name: "Akron", state: "OH", pop: "190k", tier: "small" },
  { name: "Indianapolis", state: "IN", pop: "880k", tier: "major" },
  { name: "Fort Wayne", state: "IN", pop: "263k", tier: "mid" },
  { name: "Louisville", state: "KY", pop: "633k", tier: "major" },
  { name: "Lexington", state: "KY", pop: "322k", tier: "mid" },
  { name: "Kansas City", state: "MO", pop: "508k", tier: "major" },
  { name: "St. Louis", state: "MO", pop: "301k", tier: "mid" },
  { name: "Springfield", state: "MO", pop: "169k", tier: "small" },
  { name: "Omaha", state: "NE", pop: "487k", tier: "mid" },
  { name: "Lincoln", state: "NE", pop: "292k", tier: "mid" },
  { name: "Des Moines", state: "IA", pop: "214k", tier: "small" },
  { name: "Cedar Rapids", state: "IA", pop: "137k", tier: "small" },
  { name: "Milwaukee", state: "WI", pop: "577k", tier: "major" },
  { name: "Madison", state: "WI", pop: "269k", tier: "mid" },
  { name: "Green Bay", state: "WI", pop: "107k", tier: "small" },
  { name: "Minneapolis", state: "MN", pop: "429k", tier: "major" },
  { name: "St. Paul", state: "MN", pop: "311k", tier: "mid" },
  { name: "Duluth", state: "MN", pop: "86k", tier: "small" },
  { name: "Albuquerque", state: "NM", pop: "564k", tier: "major" },
  { name: "Santa Fe", state: "NM", pop: "87k", tier: "small" },
  { name: "Las Vegas", state: "NV", pop: "641k", tier: "major" },
  { name: "Reno", state: "NV", pop: "264k", tier: "mid" },
  { name: "Salt Lake City", state: "UT", pop: "199k", tier: "small" },
  { name: "Provo", state: "UT", pop: "115k", tier: "small" },
  { name: "Boise", state: "ID", pop: "235k", tier: "mid" },
];

const NICHE_SUGGESTIONS = [
  "roofing", "plumbing", "hvac", "electricians", "emergency plumber",
  "water damage restoration", "mold remediation", "foundation repair",
  "tree removal", "junk removal", "pressure washing", "gutter cleaning",
  "personal injury lawyer", "criminal defense attorney", "dui lawyer",
  "bankruptcy attorney", "family law", "estate planning",
  "dentist", "orthodontist", "chiropractor", "physical therapy",
  "veterinarian", "pet grooming", "dog training",
  "garage door repair", "locksmith", "appliance repair",
  "pool cleaning", "pest control", "lawn care", "landscaping",
  "auto body shop", "windshield repair", "towing",
  "wedding photographer", "videographer", "event rentals",
];

const ARCHETYPES = [
  { id: "AGGREGATOR_DOMINATED",   short: "Aggregator Dominant",      tint: "var(--arch-aggregator)",      blurb: "Yelp, HomeAdvisor, Angi own the SERP. Target long-tail, avoid head terms." },
  { id: "LOCAL_PACK_FORTIFIED",   short: "Local Pack Fortified",     tint: "var(--arch-pack-fortified)",  blurb: "Strong GBP with established, actively-reviewed businesses. Long timeline." },
  { id: "LOCAL_PACK_ESTABLISHED", short: "Local Pack Established",   tint: "var(--arch-pack-established)",blurb: "Pack exists with moderate-strength businesses. GBP-first, 4–8 months." },
  { id: "LOCAL_PACK_VULNERABLE",  short: "Local Pack Vulnerable",    tint: "var(--arch-pack-vulnerable)", blurb: "Pack is weak. GBP + site combo, fastest path to leads, 2–4 months." },
  { id: "FRAGMENTED_WEAK",        short: "Fragmented Weak",          tint: "var(--arch-fragmented-weak)", blurb: "Lots of low-quality local sites. Classic rank-and-rent — quality wins." },
  { id: "FRAGMENTED_COMPETITIVE", short: "Fragmented Competitive",   tint: "var(--arch-fragmented-comp)", blurb: "Local sites with real authority. Needs link-building investment." },
  { id: "BARREN",                 short: "Barren",                   tint: "var(--arch-barren)",          blurb: "Nobody competing. Low-hanging fruit if real demand exists." },
  { id: "MIXED",                  short: "Mixed",                    tint: "var(--arch-mixed)",           blurb: "No dominant pattern. Analyze SERP gaps case-by-case." },
];

const STRATEGY_PRESETS = [
  {
    id: "mid-tier-aggregator",
    title: "Mid-tier aggregator plays",
    tagline: "Long-tail wins where Yelp owns the SERP",
    archetype: "AGGREGATOR_DOMINATED",
    tier: "mid",
    scoreMin: 55,
    count: 86,
  },
  {
    id: "vulnerable-pack-quick",
    title: "Vulnerable pack, quick wins",
    tagline: "Weak GBP, 2–4 month path to leads",
    archetype: "LOCAL_PACK_VULNERABLE",
    tier: "any",
    scoreMin: 65,
    count: 142,
  },
  {
    id: "barren-prospectors",
    title: "Barren prospector",
    tagline: "Low-competition SERPs with real demand",
    archetype: "BARREN",
    tier: "any",
    scoreMin: 70,
    count: 38,
  },
  {
    id: "fragmented-weak-classic",
    title: "Classic rank-and-rent",
    tagline: "Fragmented weak — quality site beats the field",
    archetype: "FRAGMENTED_WEAK",
    tier: "any",
    scoreMin: 60,
    count: 203,
  },
  {
    id: "small-city-sweep",
    title: "Small city sweep",
    tagline: "Sub-200k metros, any archetype, high score",
    archetype: "any",
    tier: "small",
    scoreMin: 75,
    count: 167,
  },
  {
    id: "established-patient",
    title: "Established pack, patient build",
    tagline: "Review campaign + GBP-first, 4–8 months",
    archetype: "LOCAL_PACK_ESTABLISHED",
    tier: "major",
    scoreMin: 50,
    count: 94,
  },
];

// Fake but plausible result rows
function makeResults(seed, query) {
  const rng = mulberry32(hashStr(seed));
  const cities = [...US_CITIES].sort(() => rng() - 0.5).slice(0, 18);
  const niches = query.service
    ? [query.service]
    : ["roofing", "plumbing", "hvac", "tree removal", "garage door repair"];

  return cities.map((c, i) => {
    const arch = ARCHETYPES[Math.floor(rng() * ARCHETYPES.length)];
    const score = Math.round(40 + rng() * 55);
    const niche = query.service || niches[i % niches.length];
    const volume = Math.round(80 + rng() * 2400);
    const cpc = (3 + rng() * 22).toFixed(2);
    const aio = Math.round(rng() * 28);
    const tier = c.tier;
    const difficulty = ["Easy", "Moderate", "Hard", "Very Hard"][Math.floor(rng() * 4)];
    return { city: c, niche, arch, score, volume, cpc, aio, tier, difficulty };
  });
}

function hashStr(s) { let h = 2166136261; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; }
function mulberry32(a) { return function () { let t = (a += 0x6D2B79F5); t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }

// ─────────────────────────────────────────────────────────────
// Icon set (hand-rolled, stroked, currentColor)
// ─────────────────────────────────────────────────────────────
const I = {
  search: (p) => <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" {...p}><circle cx="7" cy="7" r="4.5"/><path d="M10.5 10.5L14 14"/></svg>,
  pin:    (p) => <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M8 14s5-4.5 5-8.5a5 5 0 10-10 0C3 9.5 8 14 8 14z"/><circle cx="8" cy="5.5" r="1.8"/></svg>,
  niche:  (p) => <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" {...p}><path d="M3 13V6l5-3 5 3v7"/><path d="M6 13v-3h4v3"/></svg>,
  star:   (p) => <svg viewBox="0 0 16 16" fill="currentColor" {...p}><path d="M8 1.5l2 4.2 4.6.5-3.4 3.1.9 4.5L8 11.6l-4.1 2.2.9-4.5L1.4 6.2l4.6-.5z"/></svg>,
  starO:  (p) => <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" {...p}><path d="M8 1.5l2 4.2 4.6.5-3.4 3.1.9 4.5L8 11.6l-4.1 2.2.9-4.5L1.4 6.2l4.6-.5z"/></svg>,
  clock:  (p) => <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" {...p}><circle cx="8" cy="8" r="6"/><path d="M8 5v3.2L10 10"/></svg>,
  arrow:  (p) => <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M6 3l5 5-5 5"/></svg>,
  sliders:(p) => <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" {...p}><path d="M3 4h7M13 4h0M3 8h2M8 8h5M3 12h7M13 12h0"/><circle cx="11" cy="4" r="1.6"/><circle cx="6.5" cy="8" r="1.6"/><circle cx="11" cy="12" r="1.6"/></svg>,
  grid:   (p) => <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" {...p}><rect x="2" y="2" width="5" height="5"/><rect x="9" y="2" width="5" height="5"/><rect x="2" y="9" width="5" height="5"/><rect x="9" y="9" width="5" height="5"/></svg>,
  list:   (p) => <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" {...p}><path d="M3 4h10M3 8h10M3 12h10"/></svg>,
  x:      (p) => <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" {...p}><path d="M4 4l8 8M12 4l-8 8"/></svg>,
  plus:   (p) => <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" {...p}><path d="M8 3v10M3 8h10"/></svg>,
  sparkle:(p) => <svg viewBox="0 0 16 16" fill="currentColor" {...p}><path d="M8 1l1.2 3.8L13 6l-3.8 1.2L8 11l-1.2-3.8L3 6l3.8-1.2z"/></svg>,
  chevron:(p) => <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M4 6l4 4 4-4"/></svg>,
  check:  (p) => <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M3 8.5l3.5 3L13 5"/></svg>,
};

// ─────────────────────────────────────────────────────────────
// CityAutocomplete — input with dropdown keyed on name/state
// ─────────────────────────────────────────────────────────────
function CityAutocomplete({ value, onChange, placeholder = "City", testId, dense }) {
  const [open, setOpen] = useState(false);
  const [focus, setFocus] = useState(0);
  const ref = useRef(null);

  const matches = useMemo(() => {
    const q = value.trim().toLowerCase();
    if (!q) return US_CITIES.slice(0, 8);
    return US_CITIES.filter(
      (c) => c.name.toLowerCase().startsWith(q) || c.state.toLowerCase() === q || (c.name + ", " + c.state).toLowerCase().includes(q)
    ).slice(0, 8);
  }, [value]);

  useEffect(() => {
    const onDoc = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("pointerdown", onDoc);
    return () => document.removeEventListener("pointerdown", onDoc);
  }, []);

  const pick = (c) => { onChange(c.name); setOpen(false); };

  return (
    <div ref={ref} style={{ position: "relative", flex: 1, minWidth: 0 }}>
      <div style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "var(--color-text-muted)", display: "flex" }}><I.pin width="14" height="14"/></div>
      <input
        data-testid={testId}
        value={value}
        placeholder={placeholder}
        onFocus={() => setOpen(true)}
        onChange={(e) => { onChange(e.target.value); setOpen(true); setFocus(0); }}
        onKeyDown={(e) => {
          if (!open && e.key !== "Escape") setOpen(true);
          if (e.key === "ArrowDown") { e.preventDefault(); setFocus((f) => Math.min(f + 1, matches.length - 1)); }
          else if (e.key === "ArrowUp") { e.preventDefault(); setFocus((f) => Math.max(f - 1, 0)); }
          else if (e.key === "Enter" && matches[focus]) { e.preventDefault(); pick(matches[focus]); }
          else if (e.key === "Escape") setOpen(false);
        }}
        style={{
          width: "100%", background: "var(--color-dark)", border: "1px solid var(--color-dark-border)",
          borderRadius: 8, padding: dense ? "9px 12px 9px 34px" : "11px 12px 11px 34px",
          fontSize: "var(--fs-body, 14px)", color: "var(--color-text-primary)", outline: "none",
        }}
        onFocusCapture={(e) => (e.currentTarget.style.borderColor = "var(--color-accent)")}
        onBlurCapture={(e) => (e.currentTarget.style.borderColor = "var(--color-dark-border)")}
      />
      {open && matches.length > 0 && (
        <div style={{
          position: "absolute", top: "calc(100% + 4px)", left: 0, right: 0, zIndex: 20,
          background: "var(--color-dark-card)", border: "1px solid var(--color-dark-border)",
          borderRadius: 8, padding: 4, maxHeight: 280, overflowY: "auto",
          boxShadow: "0 8px 24px rgba(0,0,0,0.4)",
        }}>
          {matches.map((c, i) => (
            <button key={c.name + c.state} onMouseEnter={() => setFocus(i)} onClick={() => pick(c)}
              style={{
                display: "flex", alignItems: "center", gap: 10, width: "100%", textAlign: "left",
                padding: "8px 10px", borderRadius: 6, border: "none", background: i === focus ? "var(--color-dark-hover)" : "transparent",
                color: "var(--color-text-primary)", fontSize: 13,
              }}>
              <I.pin width="13" height="13" style={{ color: "var(--color-text-muted)" }}/>
              <span style={{ flex: 1 }}>{c.name}<span style={{ color: "var(--color-text-muted)" }}>, {c.state}</span></span>
              <span style={{ color: "var(--color-text-muted)", fontSize: 11, fontVariantNumeric: "tabular-nums" }}>{c.pop}</span>
              <Tag>{c.tier}</Tag>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function Tag({ children, tone = "default" }) {
  const tones = {
    default: { bg: "rgba(163,163,163,0.12)", color: "var(--color-text-secondary)" },
    accent:  { bg: "var(--color-accent-bg)", color: "var(--color-accent-light)" },
    warn:    { bg: "rgba(245,158,11,0.12)", color: "var(--color-warning)" },
  };
  const t = tones[tone] || tones.default;
  return <span style={{ fontSize: 10, letterSpacing: 0.4, textTransform: "uppercase", background: t.bg, color: t.color, padding: "2px 6px", borderRadius: 4, fontWeight: 500 }}>{children}</span>;
}

// ─────────────────────────────────────────────────────────────
// NicheInput — service/keyword with suggestion chips
// ─────────────────────────────────────────────────────────────
function NicheInput({ value, onChange, dense, testId }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const matches = useMemo(() => {
    const q = value.trim().toLowerCase();
    if (!q) return NICHE_SUGGESTIONS.slice(0, 8);
    return NICHE_SUGGESTIONS.filter((n) => n.toLowerCase().includes(q)).slice(0, 8);
  }, [value]);

  useEffect(() => {
    const onDoc = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("pointerdown", onDoc);
    return () => document.removeEventListener("pointerdown", onDoc);
  }, []);

  return (
    <div ref={ref} style={{ position: "relative", flex: 1.3, minWidth: 0 }}>
      <div style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "var(--color-text-muted)", display: "flex" }}><I.niche width="14" height="14"/></div>
      <input
        data-testid={testId}
        value={value}
        placeholder="Niche (e.g. roofing)"
        onFocus={() => setOpen(true)}
        onChange={(e) => { onChange(e.target.value); setOpen(true); }}
        style={{
          width: "100%", background: "var(--color-dark)", border: "1px solid var(--color-dark-border)",
          borderRadius: 8, padding: dense ? "9px 12px 9px 34px" : "11px 12px 11px 34px",
          fontSize: "var(--fs-body, 14px)", color: "var(--color-text-primary)", outline: "none",
        }}
        onFocusCapture={(e) => (e.currentTarget.style.borderColor = "var(--color-accent)")}
        onBlurCapture={(e) => (e.currentTarget.style.borderColor = "var(--color-dark-border)")}
      />
      {open && matches.length > 0 && (
        <div style={{
          position: "absolute", top: "calc(100% + 4px)", left: 0, right: 0, zIndex: 20,
          background: "var(--color-dark-card)", border: "1px solid var(--color-dark-border)",
          borderRadius: 8, padding: 4, maxHeight: 240, overflowY: "auto",
          boxShadow: "0 8px 24px rgba(0,0,0,0.4)",
        }}>
          {matches.map((m) => (
            <button key={m} onClick={() => { onChange(m); setOpen(false); }}
              style={{ display: "block", width: "100%", textAlign: "left", padding: "7px 10px", borderRadius: 6, border: "none", background: "transparent", color: "var(--color-text-primary)", fontSize: 13 }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "var(--color-dark-hover)")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}>
              {m}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// PrimaryBtn, GhostBtn
// ─────────────────────────────────────────────────────────────
function PrimaryBtn({ children, icon, onClick, dense, testId }) {
  return (
    <button data-testid={testId} onClick={onClick}
      onMouseEnter={(e) => (e.currentTarget.style.background = "var(--color-accent-dark)")}
      onMouseLeave={(e) => (e.currentTarget.style.background = "var(--color-accent)")}
      style={{
        display: "inline-flex", alignItems: "center", gap: 8, border: "none",
        background: "var(--color-accent)", color: "#04231a", fontWeight: 600, fontSize: 13,
        padding: dense ? "9px 14px" : "11px 16px", borderRadius: 8, whiteSpace: "nowrap",
      }}>
      {icon}<span>{children}</span>
    </button>
  );
}

function GhostBtn({ children, icon, onClick, active = false, dense }) {
  return (
    <button onClick={onClick}
      style={{
        display: "inline-flex", alignItems: "center", gap: 6,
        background: active ? "var(--color-dark-hover)" : "transparent",
        color: active ? "var(--color-text-primary)" : "var(--color-text-secondary)",
        border: "1px solid var(--color-dark-border)", borderRadius: 8,
        padding: dense ? "7px 10px" : "9px 12px", fontSize: 12.5, fontWeight: 500,
      }}
      onMouseEnter={(e) => (e.currentTarget.style.background = "var(--color-dark-hover)")}
      onMouseLeave={(e) => (e.currentTarget.style.background = active ? "var(--color-dark-hover)" : "transparent")}>
      {icon}<span>{children}</span>
    </button>
  );
}

// ─────────────────────────────────────────────────────────────
// Results — list + grid renderers
// ─────────────────────────────────────────────────────────────
function ScoreBadge({ score }) {
  const tone = score >= 75 ? "var(--color-accent)" : score >= 55 ? "var(--color-warning)" : "var(--color-text-muted)";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 56 }}>
      <div style={{ width: 36, height: 36, borderRadius: 8, background: "var(--color-dark)", border: `1px solid ${tone}`, color: tone, display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 600, fontSize: 14, fontVariantNumeric: "tabular-nums" }}>
        {score}
      </div>
    </div>
  );
}

function ArchetypeChip({ arch, compact }) {
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 6,
      padding: compact ? "2px 8px" : "3px 10px", borderRadius: 999,
      background: `color-mix(in oklab, ${arch.tint} 14%, transparent)`,
      color: arch.tint, fontSize: compact ? 10.5 : 11.5, fontWeight: 500, whiteSpace: "nowrap",
    }}>
      <span style={{ width: 6, height: 6, borderRadius: 3, background: arch.tint }} />
      {arch.short}
    </span>
  );
}

function ResultRow({ r, dense }) {
  return (
    <div style={{
      display: "grid",
      gridTemplateColumns: "40px 1.4fr 1fr 110px 80px 80px 60px 20px",
      alignItems: "center", gap: 12,
      padding: dense ? "8px 12px" : "12px 14px",
      borderBottom: "1px solid var(--color-dark-border)",
      cursor: "pointer",
    }}
    onMouseEnter={(e) => (e.currentTarget.style.background = "var(--color-dark-hover)")}
    onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}>
      <ScoreBadge score={r.score} />
      <div style={{ minWidth: 0 }}>
        <div style={{ fontWeight: 600, fontSize: 14, color: "var(--color-text-primary)", textTransform: "capitalize", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {r.niche} · {r.city.name}
        </div>
        <div style={{ fontSize: 11.5, color: "var(--color-text-muted)", display: "flex", gap: 8, marginTop: 2 }}>
          <span>{r.city.state}</span>
          <span>·</span>
          <span>{r.city.pop}</span>
          <span>·</span>
          <span style={{ textTransform: "capitalize" }}>{r.tier} metro</span>
        </div>
      </div>
      <div><ArchetypeChip arch={r.arch} compact /></div>
      <div style={{ fontSize: 12, color: "var(--color-text-secondary)", fontVariantNumeric: "tabular-nums" }}>{r.volume.toLocaleString()}/mo</div>
      <div style={{ fontSize: 12, color: "var(--color-text-secondary)", fontVariantNumeric: "tabular-nums" }}>${r.cpc}</div>
      <div style={{ fontSize: 12, color: r.aio > 15 ? "var(--color-warning)" : "var(--color-text-muted)", fontVariantNumeric: "tabular-nums" }}>{r.aio}% AIO</div>
      <div style={{ fontSize: 11, color: "var(--color-text-muted)" }}>{r.difficulty}</div>
      <div style={{ color: "var(--color-text-muted)" }}><I.arrow width="12" height="12"/></div>
    </div>
  );
}

function ResultsHeader() {
  return (
    <div style={{
      display: "grid",
      gridTemplateColumns: "40px 1.4fr 1fr 110px 80px 80px 60px 20px",
      alignItems: "center", gap: 12,
      padding: "8px 14px",
      borderBottom: "1px solid var(--color-dark-border)",
      fontSize: 10.5, letterSpacing: 0.6, textTransform: "uppercase", color: "var(--color-text-muted)", fontWeight: 500,
    }}>
      <div>Score</div>
      <div>Niche · Metro</div>
      <div>Archetype</div>
      <div>Volume</div>
      <div>CPC</div>
      <div>AI</div>
      <div>Diff.</div>
      <div></div>
    </div>
  );
}

function ResultsList({ results, dense }) {
  return (
    <div style={{ background: "var(--color-dark-card)", border: "1px solid var(--color-dark-border)", borderRadius: 12, overflow: "hidden" }}>
      <ResultsHeader />
      <div style={{ maxHeight: 520, overflowY: "auto" }}>
        {results.map((r, i) => <ResultRow key={i} r={r} dense={dense} />)}
      </div>
    </div>
  );
}

function ResultCard({ r }) {
  return (
    <div style={{
      background: "var(--color-dark-card)", border: "1px solid var(--color-dark-border)",
      borderRadius: 10, padding: 14, cursor: "pointer", display: "flex", flexDirection: "column", gap: 10,
    }}
    onMouseEnter={(e) => { e.currentTarget.style.borderColor = "var(--color-accent)"; }}
    onMouseLeave={(e) => { e.currentTarget.style.borderColor = "var(--color-dark-border)"; }}>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
        <ScoreBadge score={r.score} />
        <ArchetypeChip arch={r.arch} compact />
      </div>
      <div>
        <div style={{ fontWeight: 600, fontSize: 14, textTransform: "capitalize" }}>{r.niche}</div>
        <div style={{ fontSize: 12, color: "var(--color-text-secondary)", marginTop: 2 }}>{r.city.name}, {r.city.state} · {r.city.pop}</div>
      </div>
      <div style={{ display: "flex", gap: 12, fontSize: 11, color: "var(--color-text-muted)", fontVariantNumeric: "tabular-nums", borderTop: "1px solid var(--color-dark-border)", paddingTop: 8 }}>
        <div><span style={{ color: "var(--color-text-secondary)" }}>{r.volume.toLocaleString()}</span>/mo</div>
        <div>${r.cpc} cpc</div>
        <div style={{ color: r.aio > 15 ? "var(--color-warning)" : "var(--color-text-muted)" }}>{r.aio}% AIO</div>
      </div>
    </div>
  );
}

function ResultsGrid({ results }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 12 }}>
      {results.map((r, i) => <ResultCard key={i} r={r} />)}
    </div>
  );
}

// Export everything to window for cross-script use
Object.assign(window, {
  US_CITIES, NICHE_SUGGESTIONS, ARCHETYPES, STRATEGY_PRESETS,
  makeResults, hashStr, mulberry32,
  I, Tag, CityAutocomplete, NicheInput, PrimaryBtn, GhostBtn,
  ScoreBadge, ArchetypeChip, ResultRow, ResultsHeader, ResultsList, ResultCard, ResultsGrid,
});
