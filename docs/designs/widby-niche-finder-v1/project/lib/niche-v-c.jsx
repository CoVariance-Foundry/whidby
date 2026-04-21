// Variation C — Split workspace. Persistent left panel for the search
// builder (sticky). Right side shows live results reacting to the
// current selection. Builder has tabs stacked at top; current selection
// is surfaced as a "query summary" chip strip above results.

function VariationC({ tweaks }) {
  const [tab, setTab] = React.useState("strategy");
  const [selectedArch, setSelectedArch] = React.useState("PACK_VULN");
  const arch = ARCHETYPES.find(a => a.id === selectedArch);

  return (
    <div className={"app density-" + tweaks.density}>
      <Sidebar active="finder" />
      <div className="main">
        <Topbar crumbs={["Niche finder", "Workspace"]} />

        <div style={{display:"grid", gridTemplateColumns:"380px 1fr", flex:1, minHeight:0}}>
          {/* Builder panel */}
          <div style={{
            borderRight:"1px solid var(--rule)",
            background:"var(--paper-alt)",
            padding:"22px 20px",
            overflowY:"auto",
            display:"flex", flexDirection:"column", gap:18,
          }}>
            <div>
              <div style={{fontSize:11, color:"var(--ink-3)", textTransform:"uppercase", letterSpacing:"0.07em"}}>Builder</div>
              <div className="page-h1" style={{fontSize:20, marginTop:4}}>Search criteria</div>
            </div>

            <div className="tabs" style={{alignSelf:"stretch"}}>
              <button className={"tab" + (tab==="niche" ? " active" : "")} onClick={() => setTab("niche")} style={{flex:1, justifyContent:"center"}}>
                <Icon d={I.search}/> Niche &amp; city
              </button>
              <button className={"tab" + (tab==="strategy" ? " active" : "")} onClick={() => setTab("strategy")} style={{flex:1, justifyContent:"center"}}>
                <Icon d={I.sparkle}/> Strategy
              </button>
            </div>

            {tab === "niche" ? (
              <div style={{display:"flex", flexDirection:"column", gap:14}}>
                <NicheField value="roofing" />
                <CityField value="Phoenix" />
                <div>
                  <div className="field-label">Suggestions for "P..."</div>
                  <div className="chip-row">
                    {CITY_SUGGESTIONS.slice(0,4).map((c) => (
                      <button key={c.name} className="chip">
                        <Icon d={I.mapPin}/> {c.name}, {c.state}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div style={{display:"flex", flexDirection:"column", gap:14}}>
                {tweaks.strategyStyle === "presets" ? (
                  <div style={{display:"flex", flexDirection:"column", gap:8}}>
                    {ARCHETYPES.slice(0,6).map((a) => (
                      <button key={a.id}
                        onClick={() => setSelectedArch(a.id)}
                        className={"preset" + (selectedArch===a.id ? " selected" : "")}
                        style={{padding:"11px 12px", gap:2}}>
                        <div style={{display:"flex", alignItems:"center", gap:11}}>
                          <div className={"preset-glyph " + a.glyph} style={{width:28, height:28, fontSize:12, borderRadius:7}}>{a.icon}</div>
                          <div style={{flex:1, minWidth:0}}>
                            <div className="preset-title" style={{fontSize:13}}>{a.title}</div>
                            <div className="preset-desc" style={{fontSize:11.5, marginTop:1}}>{a.hint}</div>
                          </div>
                          <div className="preset-check"><Icon d={I.check} size={11} sw={3}/></div>
                        </div>
                      </button>
                    ))}
                  </div>
                ) : (
                  <StrategyPicker style={tweaks.strategyStyle} selected={selectedArch} onSelect={setSelectedArch} />
                )}

                <div>
                  <div className="field-label">Metro tier</div>
                  <div className="chip-row">
                    {["Major", "Mid‑tier", "Small"].map((t, i) => (
                      <button key={t} className="chip" style={i===1 ? {background:"var(--accent-soft)", borderColor:"var(--accent)", color:"var(--accent-ink)"} : {}}>{t}</button>
                    ))}
                  </div>
                </div>
              </div>
            )}

            <div style={{marginTop:"auto", display:"flex", flexDirection:"column", gap:10}}>
              <button className="btn-primary" style={{justifyContent:"center"}}>
                <Icon d={I.search}/> Run search
              </button>
              <div style={{display:"flex", gap:8}}>
                <button className="btn-ghost" style={{flex:1, justifyContent:"center"}}><Icon d={I.save}/> Save</button>
                <button className="btn-ghost" style={{flex:1, justifyContent:"center"}}><Icon d={I.clock}/> Recent</button>
              </div>
            </div>
          </div>

          {/* Results panel */}
          <div style={{padding:"22px 28px 40px", overflowY:"auto"}}>
            {/* Query summary strip */}
            <div style={{
              display:"flex", alignItems:"center", gap:10,
              padding:"11px 14px",
              background:"var(--card)",
              border:"1px solid var(--rule)",
              borderRadius:10,
              marginBottom:18,
              fontSize:12.5,
            }}>
              <Icon d={I.filter} />
              <span style={{color:"var(--ink-3)"}}>Strategy</span>
              <span className={"badge " + arch.glyph}>
                <span className="badge-dot" style={{background:"currentColor"}}/>
                {arch.short}
              </span>
              <span style={{color:"var(--ink-3)"}}>· score ≥</span>
              <span style={{fontWeight:600, fontVariantNumeric:"tabular-nums"}}>60</span>
              <span style={{color:"var(--ink-3)"}}>· tier</span>
              <span style={{fontWeight:500}}>Mid‑tier</span>
              <div style={{flex:1}}/>
              <button className="btn-ghost" style={{padding:"4px 9px"}}><Icon d={I.x} size={11}/> Clear</button>
            </div>

            <Results limit={7} showHeader={true} tools={true}/>

            {/* Saved rail inline */}
            <div style={{marginTop:26}}>
              <div className="field-label" style={{display:"flex", alignItems:"center", gap:6}}>
                <Icon d={I.star} size={11}/> Saved searches
              </div>
              <div style={{display:"grid", gridTemplateColumns:"repeat(3, 1fr)", gap:10}}>
                {SAVED_SEARCHES.map((s, i) => (
                  <button key={i} style={{
                    textAlign:"left",
                    padding:"12px 14px",
                    background:"var(--card)",
                    border:"1px solid var(--rule)",
                    borderRadius:10,
                  }}>
                    <div style={{fontSize:13, fontWeight:500}}>{s.label}</div>
                    <div style={{fontSize:11.5, color:"var(--ink-3)", marginTop:4}}>{s.sub}</div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

window.VariationC = VariationC;
