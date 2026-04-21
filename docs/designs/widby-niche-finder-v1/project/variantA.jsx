// variantA.jsx — Classic tabs: Niche+City | Strategy (preset cards). Inline results.
const { useState: useStateA, useMemo: useMemoA } = React;

function VariantA({ dense = false, pickerStyle = "presets" }) {
  const [mode, setMode] = useStateA("niche");       // 'niche' | 'strategy'
  const [city, setCity] = useStateA("Phoenix");
  const [niche, setNiche] = useStateA("roofing");
  const [preset, setPreset] = useStateA(STRATEGY_PRESETS[1].id);
  const [archFilter, setArchFilter] = useStateA("LOCAL_PACK_VULNERABLE");
  const [tierFilter, setTierFilter] = useStateA("any");
  const [scoreMin, setScoreMin] = useStateA(60);
  const [view, setView] = useStateA("list");

  const selectedPreset = STRATEGY_PRESETS.find((p) => p.id === preset);

  const queryKey =
    mode === "niche"
      ? `n:${city}|${niche}`
      : `s:${archFilter}|${tierFilter}|${scoreMin}`;

  const results = useMemoA(() => {
    const base = makeResults(queryKey, { service: mode === "niche" ? niche : "" });
    if (mode === "strategy") {
      return base.filter((r) => {
        const archOk = archFilter === "any" || r.arch.id === archFilter;
        const tierOk = tierFilter === "any" || r.tier === tierFilter;
        const scoreOk = r.score >= scoreMin;
        return archOk && tierOk && scoreOk;
      });
    }
    return base;
  }, [queryKey, mode, archFilter, tierFilter, scoreMin, niche]);

  const recents = [
    { mode: "niche", label: "roofing · Phoenix, AZ", time: "2h ago" },
    { mode: "niche", label: "plumbing · Austin, TX", time: "yesterday" },
    { mode: "strategy", label: "Vulnerable pack · any tier · ≥65", time: "2d ago" },
  ];
  const saved = [
    { mode: "strategy", label: "Mid-tier aggregator plays" },
    { mode: "niche", label: "tree removal · Denver, CO" },
  ];

  return (
    <div className="app" style={{ minHeight: "100%", padding: 24, display: "grid", gridTemplateColumns: "260px 1fr", gap: 20 }}>
      {/* Sidebar: recents + saved */}
      <aside style={{ display: "flex", flexDirection: "column", gap: 18 }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10, color: "var(--color-text-primary)", fontWeight: 600, fontSize: 13 }}>
            <div style={{ width: 22, height: 22, borderRadius: 6, background: "var(--color-accent-bg)", color: "var(--color-accent)", display: "grid", placeItems: "center" }}>
              <I.sparkle width="12" height="12" />
            </div>
            Widby
          </div>
          <div style={{ fontSize: 11, color: "var(--color-text-muted)", letterSpacing: 0.6, textTransform: "uppercase", marginBottom: 6 }}>Niche finder</div>
        </div>

        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "var(--color-text-muted)", letterSpacing: 0.6, textTransform: "uppercase", marginBottom: 8 }}>
            <I.starO width="12" height="12" /> Saved
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
            {saved.map((s, i) => (
              <button key={i} style={{
                display: "flex", alignItems: "center", gap: 8, padding: "8px 10px", textAlign: "left",
                background: "transparent", border: "none", borderRadius: 6, color: "var(--color-text-secondary)", fontSize: 12.5,
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "var(--color-dark-hover)")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}>
                <I.star width="11" height="11" style={{ color: "var(--color-accent)" }} />
                <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{s.label}</span>
              </button>
            ))}
          </div>
        </div>

        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "var(--color-text-muted)", letterSpacing: 0.6, textTransform: "uppercase", marginBottom: 8 }}>
            <I.clock width="12" height="12" /> Recent
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
            {recents.map((r, i) => (
              <button key={i} style={{
                display: "flex", alignItems: "flex-start", flexDirection: "column", padding: "8px 10px", textAlign: "left",
                background: "transparent", border: "none", borderRadius: 6, color: "var(--color-text-secondary)",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "var(--color-dark-hover)")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}>
                <span style={{ fontSize: 12.5, color: "var(--color-text-primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 220 }}>{r.label}</span>
                <span style={{ fontSize: 10.5, color: "var(--color-text-muted)", marginTop: 2 }}>
                  <Tag tone={r.mode === "strategy" ? "accent" : "default"}>{r.mode}</Tag> · {r.time}
                </span>
              </button>
            ))}
          </div>
        </div>
      </aside>

      {/* Main */}
      <main style={{ display: "flex", flexDirection: "column", gap: 16, minWidth: 0 }}>
        <header>
          <h1 style={{ fontSize: 22, fontWeight: 600, letterSpacing: -0.3 }}>Find a niche</h1>
          <p style={{ fontSize: 13, color: "var(--color-text-secondary)", marginTop: 4 }}>
            Search by niche + metro, or by strategy archetype.
          </p>
        </header>

        {/* Tabs */}
        <div style={{ display: "flex", gap: 2, background: "var(--color-dark-alt)", border: "1px solid var(--color-dark-border)", borderRadius: 10, padding: 4, width: "fit-content" }}>
          {[
            { id: "niche", label: "Niche + City", icon: <I.search width="13" height="13" /> },
            { id: "strategy", label: "Strategy", icon: <I.sliders width="13" height="13" /> },
          ].map((t) => (
            <button key={t.id} onClick={() => setMode(t.id)}
              style={{
                display: "inline-flex", alignItems: "center", gap: 8, padding: "8px 14px", borderRadius: 7, border: "none",
                background: mode === t.id ? "var(--color-dark-card)" : "transparent",
                color: mode === t.id ? "var(--color-text-primary)" : "var(--color-text-secondary)",
                fontSize: 13, fontWeight: 500,
                boxShadow: mode === t.id ? "0 1px 2px rgba(0,0,0,.3)" : "none",
              }}>
              {t.icon}{t.label}
            </button>
          ))}
        </div>

        {/* Form surface */}
        {mode === "niche" ? (
          <div style={{ background: "var(--color-dark-card)", border: "1px solid var(--color-dark-border)", borderRadius: 12, padding: 14, display: "flex", gap: 10, alignItems: "center" }}>
            <NicheInput value={niche} onChange={setNiche} dense={dense} testId="service-input" />
            <div style={{ color: "var(--color-text-muted)", fontSize: 12, padding: "0 2px" }}>in</div>
            <CityAutocomplete value={city} onChange={setCity} dense={dense} testId="city-input" />
            <PrimaryBtn dense={dense} icon={<I.search width="13" height="13" />} testId="score-niche-btn">Score Niche</PrimaryBtn>
          </div>
        ) : (
          <StrategySurface pickerStyle={pickerStyle} preset={preset} setPreset={setPreset}
            archFilter={archFilter} setArchFilter={setArchFilter}
            tierFilter={tierFilter} setTierFilter={setTierFilter}
            scoreMin={scoreMin} setScoreMin={setScoreMin}
            selectedPreset={selectedPreset} />
        )}

        {/* Results header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 4 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <h2 style={{ fontSize: 14, fontWeight: 600 }}>{results.length} metros</h2>
            {mode === "strategy" && selectedPreset && (
              <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>matching <em style={{ color: "var(--color-text-primary)", fontStyle: "normal" }}>{selectedPreset.title}</em></span>
            )}
          </div>
          <div style={{ display: "flex", gap: 6 }}>
            <GhostBtn dense icon={<I.list width="13" height="13" />} active={view === "list"} onClick={() => setView("list")}>List</GhostBtn>
            <GhostBtn dense icon={<I.grid width="13" height="13" />} active={view === "grid"} onClick={() => setView("grid")}>Grid</GhostBtn>
          </div>
        </div>

        {view === "list" ? <ResultsList results={results} dense={dense} /> : <ResultsGrid results={results} />}
      </main>
    </div>
  );
}

function StrategySurface({ pickerStyle, preset, setPreset, archFilter, setArchFilter, tierFilter, setTierFilter, scoreMin, setScoreMin, selectedPreset }) {
  if (pickerStyle === "chips") {
    return (
      <div style={{ background: "var(--color-dark-card)", border: "1px solid var(--color-dark-border)", borderRadius: 12, padding: 14, display: "flex", flexDirection: "column", gap: 14 }}>
        <div>
          <div style={{ fontSize: 11, letterSpacing: 0.6, textTransform: "uppercase", color: "var(--color-text-muted)", marginBottom: 8 }}>Archetype</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {[{id: "any", short: "Any", tint: "#737373"}, ...ARCHETYPES].map((a) => (
              <button key={a.id} onClick={() => setArchFilter(a.id)}
                style={{
                  display: "inline-flex", alignItems: "center", gap: 6, padding: "6px 10px", borderRadius: 999,
                  background: archFilter === a.id ? `color-mix(in oklab, ${a.tint} 18%, transparent)` : "var(--color-dark)",
                  border: `1px solid ${archFilter === a.id ? a.tint : "var(--color-dark-border)"}`,
                  color: archFilter === a.id ? a.tint : "var(--color-text-secondary)",
                  fontSize: 12, fontWeight: 500,
                }}>
                <span style={{ width: 6, height: 6, borderRadius: 3, background: a.tint }} />
                {a.short}
              </button>
            ))}
          </div>
        </div>
        <div style={{ display: "flex", gap: 16, alignItems: "center", flexWrap: "wrap" }}>
          <div>
            <div style={{ fontSize: 11, letterSpacing: 0.6, textTransform: "uppercase", color: "var(--color-text-muted)", marginBottom: 6 }}>Metro tier</div>
            <div style={{ display: "flex", gap: 4 }}>
              {["any", "major", "mid", "small"].map((t) => (
                <button key={t} onClick={() => setTierFilter(t)}
                  style={{ padding: "6px 12px", borderRadius: 7, border: "1px solid var(--color-dark-border)",
                    background: tierFilter === t ? "var(--color-dark-hover)" : "transparent",
                    color: tierFilter === t ? "var(--color-text-primary)" : "var(--color-text-secondary)",
                    fontSize: 12, fontWeight: 500, textTransform: "capitalize" }}>{t}</button>
              ))}
            </div>
          </div>
          <div style={{ flex: 1, minWidth: 220 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
              <span style={{ fontSize: 11, letterSpacing: 0.6, textTransform: "uppercase", color: "var(--color-text-muted)" }}>Min opportunity score</span>
              <span style={{ fontSize: 12, color: "var(--color-accent)", fontVariantNumeric: "tabular-nums", fontWeight: 600 }}>≥ {scoreMin}</span>
            </div>
            <input type="range" min="0" max="100" value={scoreMin} onChange={(e) => setScoreMin(+e.target.value)} style={{ width: "100%", accentColor: "var(--color-accent)" }} />
          </div>
          <PrimaryBtn icon={<I.search width="13" height="13" />}>Find metros</PrimaryBtn>
        </div>
      </div>
    );
  }

  if (pickerStyle === "matrix") {
    const tiers = [{id: "major", l: "Major"}, {id: "mid", l: "Mid-tier"}, {id: "small", l: "Small"}];
    return (
      <div style={{ background: "var(--color-dark-card)", border: "1px solid var(--color-dark-border)", borderRadius: 12, padding: 14 }}>
        <div style={{ fontSize: 11, letterSpacing: 0.6, textTransform: "uppercase", color: "var(--color-text-muted)", marginBottom: 10 }}>Archetype × metro tier</div>
        <div style={{ display: "grid", gridTemplateColumns: `160px repeat(${tiers.length}, 1fr)`, gap: 1, background: "var(--color-dark-border)", borderRadius: 8, overflow: "hidden" }}>
          <div style={{ background: "var(--color-dark-alt)" }} />
          {tiers.map((t) => <div key={t.id} style={{ background: "var(--color-dark-alt)", padding: "8px 10px", fontSize: 11.5, color: "var(--color-text-secondary)", fontWeight: 500 }}>{t.l}</div>)}
          {ARCHETYPES.slice(0, 6).map((a) => (
            <React.Fragment key={a.id}>
              <div style={{ background: "var(--color-dark-alt)", padding: "10px", fontSize: 12, color: "var(--color-text-primary)", display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ width: 6, height: 6, borderRadius: 3, background: a.tint }} />
                {a.short}
              </div>
              {tiers.map((t) => {
                const active = archFilter === a.id && tierFilter === t.id;
                const count = 8 + ((hashStr(a.id + t.id) % 180));
                return (
                  <button key={t.id} onClick={() => { setArchFilter(a.id); setTierFilter(t.id); }}
                    style={{
                      background: active ? `color-mix(in oklab, ${a.tint} 20%, var(--color-dark))` : "var(--color-dark-card)",
                      border: "none", cursor: "pointer", padding: "10px", textAlign: "left",
                      color: active ? a.tint : "var(--color-text-secondary)",
                      fontSize: 12, fontWeight: active ? 600 : 400,
                      fontVariantNumeric: "tabular-nums",
                    }}>
                    {count}
                  </button>
                );
              })}
            </React.Fragment>
          ))}
        </div>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 12, gap: 12 }}>
          <div style={{ flex: 1 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
              <span style={{ fontSize: 11, letterSpacing: 0.6, textTransform: "uppercase", color: "var(--color-text-muted)" }}>Min opportunity score</span>
              <span style={{ fontSize: 12, color: "var(--color-accent)", fontVariantNumeric: "tabular-nums", fontWeight: 600 }}>≥ {scoreMin}</span>
            </div>
            <input type="range" min="0" max="100" value={scoreMin} onChange={(e) => setScoreMin(+e.target.value)} style={{ width: "100%", accentColor: "var(--color-accent)" }} />
          </div>
          <PrimaryBtn icon={<I.search width="13" height="13" />}>Find metros</PrimaryBtn>
        </div>
      </div>
    );
  }

  // Default: preset cards
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(230px, 1fr))", gap: 10 }}>
        {STRATEGY_PRESETS.map((p) => {
          const arch = ARCHETYPES.find((a) => a.id === p.archetype);
          const tint = arch ? arch.tint : "var(--color-accent)";
          const active = preset === p.id;
          return (
            <button key={p.id} onClick={() => { setPreset(p.id); setArchFilter(p.archetype === "any" ? "any" : p.archetype); setTierFilter(p.tier); setScoreMin(p.scoreMin); }}
              style={{
                textAlign: "left", padding: 14, borderRadius: 10, cursor: "pointer",
                background: active ? `color-mix(in oklab, ${tint} 12%, var(--color-dark-card))` : "var(--color-dark-card)",
                border: `1px solid ${active ? tint : "var(--color-dark-border)"}`,
                display: "flex", flexDirection: "column", gap: 8, position: "relative",
              }}>
              {active && <div style={{ position: "absolute", top: 10, right: 10, width: 18, height: 18, borderRadius: 9, background: tint, color: "var(--color-dark)", display: "grid", placeItems: "center" }}><I.check width="10" height="10" /></div>}
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ width: 8, height: 8, borderRadius: 4, background: tint }} />
                <span style={{ fontSize: 10.5, letterSpacing: 0.5, textTransform: "uppercase", color: tint, fontWeight: 600 }}>
                  {arch ? arch.short : "Any archetype"}
                </span>
              </div>
              <div>
                <div style={{ fontSize: 14, fontWeight: 600, lineHeight: 1.25 }}>{p.title}</div>
                <div style={{ fontSize: 12, color: "var(--color-text-secondary)", marginTop: 4, lineHeight: 1.4 }}>{p.tagline}</div>
              </div>
              <div style={{ display: "flex", gap: 6, marginTop: "auto", paddingTop: 8, borderTop: "1px solid var(--color-dark-border)", alignItems: "center" }}>
                <Tag>{p.tier} tier</Tag>
                <Tag>≥ {p.scoreMin}</Tag>
                <span style={{ marginLeft: "auto", fontSize: 11, color: "var(--color-text-muted)", fontVariantNumeric: "tabular-nums" }}>{p.count} metros</span>
              </div>
            </button>
          );
        })}
      </div>
      {selectedPreset && (
        <div style={{ display: "flex", alignItems: "center", gap: 10, background: "var(--color-dark-card)", border: "1px solid var(--color-dark-border)", borderRadius: 10, padding: "10px 14px" }}>
          <div style={{ color: "var(--color-text-muted)" }}><I.sliders width="14" height="14" /></div>
          <div style={{ fontSize: 12, color: "var(--color-text-secondary)", flex: 1 }}>
            Applying <em style={{ color: "var(--color-text-primary)", fontStyle: "normal", fontWeight: 500 }}>{selectedPreset.title}</em>
          </div>
          <GhostBtn dense icon={<I.sliders width="12" height="12" />}>Customize</GhostBtn>
          <PrimaryBtn dense icon={<I.search width="12" height="12" />}>Run</PrimaryBtn>
        </div>
      )}
    </div>
  );
}

Object.assign(window, { VariantA });
