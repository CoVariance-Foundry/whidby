// Variation B — Command center. Full-bleed hero with a large unified
// search input, strategy presets rendered as horizontal scroll rail,
// and results in a denser, card-style grid + saved searches rail.

function VariationB({ tweaks }) {
  const [tab, setTab] = React.useState("strategy");
  const [selectedArch, setSelectedArch] = React.useState("PACK_VULN");

  return (
    <div className={"app density-" + tweaks.density}>
      <Sidebar active="finder" />
      <div className="main">
        <Topbar crumbs={["Niche finder"]} />

        {/* Hero */}
        <div style={{
          padding:"34px 40px 22px",
          background:`radial-gradient(circle at 20% 0%, rgba(15,122,87,0.08), transparent 55%), var(--paper)`,
          borderBottom:"1px solid var(--rule)",
        }}>
          <div style={{display:"flex", alignItems:"baseline", gap:14, marginBottom:14}}>
            <div className="page-h1" style={{fontSize:28}}>Search niches</div>
            <div className="page-sub" style={{margin:0}}>
              {tab==="niche" ? "Score a specific niche in a specific city." : "Pick a strategy. Widby finds metros that match."}
            </div>
          </div>

          <div className="tabs" style={{marginBottom:14}}>
            <button className={"tab" + (tab==="niche" ? " active" : "")} onClick={() => setTab("niche")}>
              <Icon d={I.search} /> Niche &amp; city
            </button>
            <button className={"tab" + (tab==="strategy" ? " active" : "")} onClick={() => setTab("strategy")}>
              <Icon d={I.sparkle} /> Strategy
            </button>
          </div>

          {tab === "niche" ? (
            <div style={{
              display:"flex", alignItems:"center", gap:0,
              background:"var(--card)",
              border:"1px solid var(--rule)",
              borderRadius:12, padding:6,
              maxWidth:760,
            }}>
              <div style={{flex:1, display:"flex", alignItems:"center", gap:10, padding:"8px 12px"}}>
                <Icon d={I.search} />
                <input defaultValue="roofing"
                  style={{flex:1, background:"transparent", border:"none", outline:"none", color:"var(--ink)", fontSize:15, fontFamily:"inherit"}}
                  placeholder="niche"/>
              </div>
              <div style={{width:1, alignSelf:"stretch", margin:"6px 0", background:"var(--rule)"}}/>
              <div style={{flex:1, display:"flex", alignItems:"center", gap:10, padding:"8px 12px", position:"relative"}}>
                <Icon d={I.mapPin} />
                <input defaultValue="Phoenix, AZ"
                  style={{flex:1, background:"transparent", border:"none", outline:"none", color:"var(--ink)", fontSize:15, fontFamily:"inherit"}}
                  placeholder="city"/>
                <span className="ac-tier">Major</span>
              </div>
              <button className="btn-primary" style={{borderRadius:8, padding:"10px 16px"}}>
                Search <Icon d={I.arrow} />
              </button>
            </div>
          ) : (
            <div>
              {tweaks.strategyStyle === "presets" ? (
                <div style={{display:"flex", gap:12, overflowX:"auto", paddingBottom:6}}>
                  {ARCHETYPES.slice(0,6).map((a) => (
                    <button key={a.id} onClick={() => setSelectedArch(a.id)}
                      className={"preset" + (selectedArch===a.id ? " selected" : "")}
                      style={{minWidth:240, flex:"0 0 auto"}}>
                      <div className="preset-head">
                        <div className={"preset-glyph " + a.glyph}>{a.icon}</div>
                        <div className="preset-check"><Icon d={I.check} size={11} sw={3}/></div>
                      </div>
                      <div>
                        <div className="preset-title">{a.title}</div>
                        <div className="preset-desc">{a.hint}</div>
                      </div>
                      <div className="preset-meta">{a.strat}</div>
                    </button>
                  ))}
                </div>
              ) : (
                <div style={{
                  background:"var(--card)",
                  border:"1px solid var(--rule)",
                  borderRadius:12, padding:16,
                }}>
                  <StrategyPicker style={tweaks.strategyStyle} selected={selectedArch} onSelect={setSelectedArch} />
                </div>
              )}
              <div style={{display:"flex", alignItems:"center", gap:10, marginTop:14}}>
                <button className="btn-primary">Run search <Icon d={I.arrow} /></button>
                <button className="btn-ghost"><Icon d={I.save} /> Save as preset</button>
                <div style={{flex:1}}/>
                <span style={{fontSize:12, color:"var(--ink-3)"}}>
                  {selectedArch && ARCHETYPES.find(a=>a.id===selectedArch).title} · {SAMPLE_RESULTS.length} matches
                </span>
              </div>
            </div>
          )}
        </div>

        {/* body: results + rail */}
        <div style={{display:"grid", gridTemplateColumns:"1fr 260px", gap:24, padding:"22px 40px 40px", flex:1, minHeight:0}}>
          <Results limit={6} tools={true} />

          <aside style={{display:"flex", flexDirection:"column", gap:18}}>
            <div>
              <div className="field-label" style={{display:"flex", justifyContent:"space-between", alignItems:"center"}}>
                <span>Pinned</span>
                <Icon d={I.pin} size={11}/>
              </div>
              <div style={{display:"flex", flexDirection:"column", gap:6}}>
                {SAVED_SEARCHES.map((s, i) => (
                  <button key={i} style={{
                    textAlign:"left", padding:"10px 12px",
                    background:"var(--card)",
                    border:"1px solid var(--rule)",
                    borderRadius:9,
                  }}>
                    <div style={{fontSize:12.5, fontWeight:500}}>{s.label}</div>
                    <div style={{fontSize:11, color:"var(--ink-3)", marginTop:3}}>{s.sub}</div>
                  </button>
                ))}
              </div>
            </div>
            <div>
              <div className="field-label">Recent</div>
              <div style={{display:"flex", flexDirection:"column", gap:4}}>
                {RECENT_SEARCHES.map((r, i) => (
                  <button key={i} style={{
                    display:"flex", alignItems:"center", justifyContent:"space-between",
                    padding:"7px 10px", borderRadius:7,
                    color:"var(--ink-2)", fontSize:12,
                  }}>
                    <span style={{display:"flex", alignItems:"center", gap:8, overflow:"hidden"}}>
                      <Icon d={r.mode==="strategy" ? I.sparkle : I.search} size={12}/>
                      <span style={{overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap"}}>{r.label}</span>
                    </span>
                    <span style={{color:"var(--ink-3)", fontSize:10.5}}>{r.ts}</span>
                  </button>
                ))}
              </div>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}

window.VariationB = VariationB;
