// Variation A — Classic tabs. Traditional SaaS layout:
// sidebar + topbar + page with segmented tabs for search mode,
// strategy picker (swappable style), then full results table below.

function VariationA({ tweaks }) {
  const [tab, setTab] = React.useState("strategy"); // "niche" | "strategy"
  const [selectedArch, setSelectedArch] = React.useState("PACK_VULN");

  return (
    <div className={"app density-" + tweaks.density}>
      <Sidebar active="finder" />
      <div className="main">
        <Topbar crumbs={["Niche finder", "New search"]} />
        <div className="page">
          <div style={{marginBottom:20}}>
            <div className="page-h1">Find your next niche</div>
            <div className="page-sub">
              Search by niche + city, or pick a strategy and let Widby surface matching metros.
            </div>
          </div>

          <div style={{display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:18}}>
            <div className="tabs">
              <button className={"tab" + (tab==="niche" ? " active" : "")} onClick={() => setTab("niche")}>
                <Icon d={I.search} /> Niche &amp; city
              </button>
              <button className={"tab" + (tab==="strategy" ? " active" : "")} onClick={() => setTab("strategy")}>
                <Icon d={I.sparkle} /> Strategy
              </button>
            </div>
            <div style={{display:"flex", gap:6, alignItems:"center"}}>
              <span style={{fontSize:11, color:"var(--ink-3)", textTransform:"uppercase", letterSpacing:"0.06em"}}>
                Recent
              </span>
              {RECENT_SEARCHES.slice(0,3).map((r,i) => (
                <button key={i} className="chip">
                  <Icon d={I.clock} /> {r.label}
                </button>
              ))}
            </div>
          </div>

          {tab === "niche" ? (
            <div style={{
              background:"var(--card)",
              border:"1px solid var(--rule)",
              borderRadius:12, padding:18, marginBottom:22,
            }}>
              <div style={{display:"flex", gap:12, alignItems:"flex-end"}}>
                <NicheField value="roofing" />
                <CityField value="Phoenix" />
                <button className="btn-primary" style={{height:42}}>
                  Search <Icon d={I.arrow} />
                </button>
              </div>
              <div style={{display:"flex", gap:14, marginTop:14, alignItems:"center"}}>
                <span style={{fontSize:11, color:"var(--ink-3)", textTransform:"uppercase", letterSpacing:"0.06em"}}>Try</span>
                <div className="chip-row">
                  {["roof repair · Tucson", "plumbing · Boise", "HVAC · Tampa", "window cleaning · Reno"].map((c) => (
                    <button key={c} className="chip"><Icon d={I.sparkle}/> {c}</button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div style={{
              background:"var(--card)",
              border:"1px solid var(--rule)",
              borderRadius:12, padding:18, marginBottom:22,
            }}>
              <div style={{display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:14}}>
                <div>
                  <div style={{fontSize:14, fontWeight:600}}>Pick a strategy</div>
                  <div style={{fontSize:12, color:"var(--ink-2)", marginTop:3}}>
                    Each preset maps to a SERP archetype and returns the best‑matching metros across your niche library.
                  </div>
                </div>
                <button className="btn-primary" style={{height:36}}>
                  Run search <Icon d={I.arrow} />
                </button>
              </div>
              <StrategyPicker style={tweaks.strategyStyle} selected={selectedArch} onSelect={setSelectedArch} />
            </div>
          )}

          <Results limit={6} />
        </div>
      </div>
    </div>
  );
}

window.VariationA = VariationA;
