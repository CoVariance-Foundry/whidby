// Home page data + page component.
// Light academic styling, mirrors Niche Search visual language.

const HOME_STATS = [
  { label: "Niches scored",        value: "128",  delta: "+14 this week",    kind: "up" },
  { label: "Metros in watchlist",  value: "47",   delta: "+3 this week",     kind: "up" },
  { label: "Avg opportunity",      value: "68.4", delta: "↑ 2.1 vs last mo", kind: "up" },
  { label: "Reports generated",    value: "19",   delta: "2 in review",      kind: "neutral" },
];

const HOME_RECOMMENDED = [
  { metro: "Tucson, AZ",      niche: "roofing",            score: 82, archetypeId: "PACK_VULN", why: "Weak local pack, avg 24 reviews" },
  { metro: "Boise, ID",       niche: "gutter installation", score: 79, archetypeId: "PACK_VULN", why: "Pack vulnerable, high demand"   },
  { metro: "Chattanooga, TN", niche: "tree service",       score: 76, archetypeId: "FRAG_WEAK", why: "Fragmented, low DA top-5"        },
  { metro: "Des Moines, IA",  niche: "deck builders",      score: 73, archetypeId: "BARREN",    why: "Low competition, modest demand"  },
];

const HOME_ACTIVITY = [
  { kind:"report",   title:"Mountain West roofing sweep",  meta:"5 metros · 3 highs", ts:"2h ago" },
  { kind:"scored",   title:"roofing · Phoenix, AZ",        meta:"Score 42 · Aggregator dominated", ts:"2h ago" },
  { kind:"saved",    title:"Fast‑path pack opportunities", meta:"Strategy saved", ts:"yesterday" },
  { kind:"scored",   title:"water damage · Tampa, FL",     meta:"Score 61 · Pack established", ts:"yesterday" },
  { kind:"report",   title:"Florida inland flood niches",  meta:"8 metros · 2 highs", ts:"3d ago" },
  { kind:"scored",   title:"garage door repair · Austin, TX", meta:"Score 54 · Fragmented competitive", ts:"3d ago" },
];

function HomePage({ tweaks }) {
  return (
    <div className={"app density-" + tweaks.density}>
      <Sidebar active="home" />
      <div className="main">
        <Topbar crumbs={["Home"]} />

        <div className="page">
          {/* Hero / greeting */}
          <div style={{display:"flex", alignItems:"flex-end", justifyContent:"space-between", gap:24, marginBottom:24}}>
            <div>
              <div className="kicker">Tuesday morning · January 21</div>
              <div className="page-h1" style={{marginTop:6}}>Good morning, Alex.</div>
              <div className="page-sub">
                Your watchlist moved up 2.1 points this month. Three new metros matched your saved strategies overnight.
              </div>
            </div>
            <div style={{display:"flex", gap:8}}>
              <button className="btn-ghost"><Icon d={I.beaker} /> Run experiment</button>
              <a href="Niche Search.html" className="btn-primary" style={{textDecoration:"none"}}>
                <Icon d={I.search} /> New search
              </a>
            </div>
          </div>

          {/* Stats row */}
          <div style={{display:"grid", gridTemplateColumns:"repeat(4, 1fr)", gap:12, marginBottom:28}}>
            {HOME_STATS.map((s, i) => (
              <div key={i} style={{
                background:"var(--card)",
                border:"1px solid var(--rule)",
                borderRadius:10,
                padding:"16px 18px",
                boxShadow:"0 1px 0 rgba(47,38,20,0.03)",
              }}>
                <div className="field-label" style={{marginBottom:8}}>{s.label}</div>
                <div style={{
                  fontFamily:"var(--serif)",
                  fontSize:30, fontWeight:600, letterSpacing:"-0.5px",
                  lineHeight:1, fontVariantNumeric:"tabular-nums",
                }}>{s.value}</div>
                <div style={{
                  marginTop:8, fontSize:12,
                  color: s.kind === "up" ? "var(--accent-ink)" : "var(--ink-3)",
                  fontFamily:"var(--serif)", fontStyle:"italic",
                }}>{s.delta}</div>
              </div>
            ))}
          </div>

          {/* Quick search strip */}
          <div style={{
            background:"var(--card)",
            border:"1px solid var(--rule)",
            borderRadius:12,
            padding:"18px 20px",
            marginBottom:28,
            display:"flex", alignItems:"center", gap:14,
          }}>
            <div style={{
              width:36, height:36, borderRadius:8,
              background:"var(--accent-soft)", color:"var(--accent-ink)",
              display:"grid", placeItems:"center", flexShrink:0,
            }}>
              <Icon d={I.search} size={16} />
            </div>
            <div style={{flex:1}}>
              <div style={{fontFamily:"var(--serif)", fontSize:15, fontWeight:600, color:"var(--ink)"}}>
                Score a niche or explore by strategy
              </div>
              <div style={{fontSize:12.5, color:"var(--ink-3)", marginTop:3}}>
                Search by niche + city, or pick a strategy and let Widby surface matching metros.
              </div>
            </div>
            <div className="chip-row">
              <a className="chip" href="Niche Search.html" style={{textDecoration:"none"}}>
                <Icon d={I.search}/> Niche &amp; city
              </a>
              <a className="chip" href="Niche Search.html" style={{textDecoration:"none"}}>
                <Icon d={I.sparkle}/> By strategy
              </a>
            </div>
          </div>

          {/* Two-col: recommended + activity */}
          <div style={{display:"grid", gridTemplateColumns:"minmax(0, 1.55fr) minmax(0, 1fr)", gap:28}}>
            {/* Recommended */}
            <div>
              <div className="results-head">
                <div>
                  <span className="results-title">Recommended for you</span>
                  <span className="results-count" style={{marginLeft:10}}>
                    Based on your saved strategies
                  </span>
                </div>
                <a href="Niche Search.html" className="btn-ghost" style={{textDecoration:"none"}}>
                  See all <Icon d={I.arrow} />
                </a>
              </div>

              <div style={{
                display:"grid",
                gridTemplateColumns:"repeat(2, 1fr)",
                gap:12,
              }}>
                {HOME_RECOMMENDED.map((r, i) => {
                  const arch = ARCHETYPES.find(a => a.id === r.archetypeId);
                  return (
                    <div key={i} style={{
                      background:"var(--card)",
                      border:"1px solid var(--rule)",
                      borderRadius:10,
                      padding:"16px 18px",
                      display:"flex", flexDirection:"column", gap:12,
                    }}>
                      <div style={{display:"flex", justifyContent:"space-between", alignItems:"flex-start", gap:10}}>
                        <div style={{flex:1, minWidth:0}}>
                          <div style={{fontFamily:"var(--serif)", fontSize:17, fontWeight:600, letterSpacing:"-0.2px", lineHeight:1.2}}>
                            {r.metro}
                          </div>
                          <div style={{fontSize:12.5, color:"var(--ink-3)", fontStyle:"italic", fontFamily:"var(--serif)", marginTop:2}}>
                            {r.niche}
                          </div>
                        </div>
                        <div style={{textAlign:"right"}}>
                          <div className="score">{r.score}</div>
                          <div style={{width:54, marginTop:5}}>
                            <div className="score-bar"><div style={{width: r.score+"%"}}/></div>
                          </div>
                        </div>
                      </div>

                      <span className={"badge " + arch.glyph} style={{alignSelf:"flex-start"}}>
                        <span className="badge-dot" style={{background:"currentColor"}}></span>
                        {arch.short}
                      </span>

                      <div style={{
                        fontSize:12.5, color:"var(--ink-2)",
                        lineHeight:1.5,
                        paddingTop:10,
                        borderTop:"1px dashed var(--rule)",
                      }}>
                        {r.why}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Activity */}
            <div>
              <div className="results-head">
                <span className="results-title">Recent activity</span>
                <button className="btn-ghost"><Icon d={I.clock} /> All</button>
              </div>
              <div style={{
                background:"var(--card)",
                border:"1px solid var(--rule)",
                borderRadius:10,
                overflow:"hidden",
              }}>
                {HOME_ACTIVITY.map((a, i) => {
                  const iconD = a.kind === "report" ? I.list
                             : a.kind === "saved"  ? I.star
                             : I.search;
                  return (
                    <div key={i} style={{
                      display:"flex", alignItems:"flex-start", gap:12,
                      padding:"12px 16px",
                      borderBottom: i < HOME_ACTIVITY.length - 1 ? "1px solid var(--rule)" : "none",
                    }}>
                      <div style={{
                        width:28, height:28, borderRadius:"50%",
                        background:"var(--paper-alt)", color:"var(--ink-2)",
                        display:"grid", placeItems:"center", flexShrink:0,
                        border:"1px solid var(--rule)",
                      }}>
                        <Icon d={iconD} size={12}/>
                      </div>
                      <div style={{flex:1, minWidth:0}}>
                        <div style={{fontSize:13, color:"var(--ink)", fontWeight:500}}>{a.title}</div>
                        <div style={{fontSize:11.5, color:"var(--ink-3)", fontStyle:"italic", fontFamily:"var(--serif)", marginTop:2}}>
                          {a.meta}
                        </div>
                      </div>
                      <div style={{fontSize:11, color:"var(--ink-3)", flexShrink:0, fontVariantNumeric:"tabular-nums"}}>
                        {a.ts}
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Saved searches block */}
              <div style={{marginTop:22}}>
                <div className="field-label" style={{fontSize:13, marginBottom:8, display:"flex", alignItems:"center", justifyContent:"space-between"}}>
                  <span>Saved searches</span>
                  <Icon d={I.star} size={11}/>
                </div>
                <div style={{display:"flex", flexDirection:"column", gap:6}}>
                  {SAVED_SEARCHES.map((s, i) => (
                    <button key={i} style={{
                      textAlign:"left", padding:"10px 12px",
                      background:"var(--card)",
                      border:"1px solid var(--rule)",
                      borderRadius:8,
                    }}>
                      <div style={{fontSize:12.5, fontWeight:500}}>{s.label}</div>
                      <div style={{fontSize:11, color:"var(--ink-3)", marginTop:3, fontFamily:"var(--serif)", fontStyle:"italic"}}>
                        {s.sub}
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

window.HomePage = HomePage;
window.HOME_STATS = HOME_STATS;
window.HOME_RECOMMENDED = HOME_RECOMMENDED;
window.HOME_ACTIVITY = HOME_ACTIVITY;
