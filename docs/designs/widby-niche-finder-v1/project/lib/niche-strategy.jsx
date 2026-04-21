// ── Strategy pickers (shared across variations via window) ──
// Three styles: presets (cards), chips, matrix. Tweakable at runtime.

function StrategyPresets({ selected = "PACK_VULN", onSelect, compact = false }) {
  const show = ARCHETYPES.slice(0, compact ? 6 : 6); // show 6 of 8 at a time
  return (
    <div className="preset-grid">
      {show.map((a) => (
        <button
          key={a.id}
          className={"preset" + (selected === a.id ? " selected" : "")}
          onClick={() => onSelect && onSelect(a.id)}
        >
          <div className="preset-head">
            <div className={"preset-glyph " + a.glyph}>{a.icon}</div>
            <div className="preset-check"><Icon d={I.check} size={11} sw={3}/></div>
          </div>
          <div>
            <div className="preset-title">{a.title}</div>
            <div className="preset-desc">{a.hint}</div>
          </div>
          <div className="preset-meta">
            <span>{a.strat}</span>
          </div>
        </button>
      ))}
    </div>
  );
}

function StrategyChips({ selected = ["PACK_VULN"], scoreMin = 70 }) {
  return (
    <div style={{display:"flex", flexDirection:"column", gap:14}}>
      <div>
        <div className="field-label">Archetype</div>
        <div className="chip-row">
          {ARCHETYPES.map((a) => {
            const on = selected.includes(a.id);
            return (
              <button key={a.id}
                className="chip"
                style={on ? {
                  background: "var(--accent-soft)",
                  borderColor: "var(--accent)",
                  color: "var(--accent-ink)",
                } : {}}
              >
                <span className={"badge-dot"} style={{
                  width:6, height:6, borderRadius:3,
                  background: on ? "var(--accent)" : "var(--ink-3)"
                }}/>
                {a.short}
              </button>
            );
          })}
        </div>
      </div>
      <div style={{display:"grid", gridTemplateColumns:"1fr 1fr", gap:16}}>
        <div>
          <div className="field-label">Opportunity score ≥</div>
          <div style={{display:"flex", alignItems:"center", gap:12}}>
            <div style={{flex:1, height:4, background:"var(--rule)", borderRadius:3, position:"relative"}}>
              <div style={{position:"absolute", left:0, top:0, bottom:0, width:scoreMin+"%", background:"var(--accent)", borderRadius:3}}/>
              <div style={{position:"absolute", left:scoreMin+"%", top:-5, width:14, height:14, borderRadius:"50%", background:"#fff", border:"2px solid var(--accent)", transform:"translateX(-50%)"}}/>
            </div>
            <div style={{fontVariantNumeric:"tabular-nums", fontWeight:600, fontSize:13, minWidth:30}}>{scoreMin}</div>
          </div>
        </div>
        <div>
          <div className="field-label">AI exposure</div>
          <div className="chip-row">
            {["Shielded", "Minimal", "Moderate", "Exposed"].map((l, i) => (
              <button key={l} className="chip" style={i<2 ? {
                background:"var(--accent-soft)", borderColor:"var(--accent)", color:"var(--accent-ink)"
              } : {}}>{l}</button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function StrategyMatrix({ selected = "PACK_VULN_MID" }) {
  const tiers = ["Major", "Mid‑tier", "Small"];
  const archs = ARCHETYPES.slice(0, 6);
  return (
    <div>
      <div style={{display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:10}}>
        <div className="field-label" style={{margin:0}}>Archetype × Metro tier</div>
        <div style={{fontSize:11, color:"var(--ink-3)"}}>
          click a cell to pick a combined strategy
        </div>
      </div>
      <div style={{
        display:"grid",
        gridTemplateColumns: "140px repeat(3, 1fr)",
        border:"1px solid var(--rule)",
        borderRadius:10,
        overflow:"hidden",
        background:"var(--card)",
        fontSize:12,
      }}>
        <div style={{padding:"10px 12px", fontSize:10, textTransform:"uppercase", letterSpacing:"0.06em", color:"var(--ink-3)", background:"var(--paper-alt)"}}></div>
        {tiers.map((t) => (
          <div key={t} style={{padding:"10px 12px", fontSize:10, textTransform:"uppercase", letterSpacing:"0.06em", color:"var(--ink-3)", background:"var(--paper-alt)", borderLeft:"1px solid var(--rule)"}}>
            {t}
          </div>
        ))}
        {archs.map((a) => (
          <React.Fragment key={a.id}>
            <div style={{padding:"10px 12px", borderTop:"1px solid var(--rule)", display:"flex", alignItems:"center", gap:8}}>
              <div className={"preset-glyph " + a.glyph} style={{width:20, height:20, fontSize:10, borderRadius:5}}>{a.icon}</div>
              <span style={{fontSize:12}}>{a.short}</span>
            </div>
            {tiers.map((t) => {
              const cellId = a.id + "_" + t.replace(/\W/g,"").slice(0,3).toUpperCase();
              const isSel = cellId === selected;
              // simulated density
              const heat = {
                "AGG_MAJ": 32, "AGG_MID": 48, "AGG_SMA": 26,
                "PACK_FORT_MAJ": 22, "PACK_FORT_MID": 30, "PACK_FORT_SMA": 18,
                "PACK_EST_MAJ": 40,  "PACK_EST_MID": 55, "PACK_EST_SMA": 44,
                "PACK_VULN_MAJ": 28, "PACK_VULN_MID": 72, "PACK_VULN_SMA": 60,
                "FRAG_WEAK_MAJ": 18, "FRAG_WEAK_MID": 50, "FRAG_WEAK_SMA": 68,
                "FRAG_COMP_MAJ": 35, "FRAG_COMP_MID": 38, "FRAG_COMP_SMA": 20,
              }[cellId] || 0;
              return (
                <button key={cellId}
                  style={{
                    padding:"10px 12px",
                    borderTop:"1px solid var(--rule)",
                    borderLeft:"1px solid var(--rule)",
                    background: isSel ? "var(--accent-soft)" : "transparent",
                    boxShadow: isSel ? "inset 0 0 0 1px var(--accent)" : "none",
                    textAlign:"left",
                    display:"flex", alignItems:"center", justifyContent:"space-between",
                    minHeight:44,
                  }}>
                  <div style={{display:"flex", alignItems:"center", gap:8}}>
                    <div style={{
                      width:26, height:5, borderRadius:3,
                      background:`linear-gradient(to right, var(--accent) ${heat}%, var(--rule) ${heat}%)`
                    }}/>
                    <span style={{fontVariantNumeric:"tabular-nums", color: isSel ? "var(--accent-ink)" : "var(--ink-2)"}}>
                      {heat} metros
                    </span>
                  </div>
                  {isSel && <Icon d={I.check} size={12} sw={3}/>}
                </button>
              );
            })}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}

function StrategyPicker({ style = "presets", selected, onSelect }) {
  if (style === "chips")  return <StrategyChips />;
  if (style === "matrix") return <StrategyMatrix />;
  return <StrategyPresets selected={selected || "PACK_VULN"} onSelect={onSelect} />;
}

Object.assign(window, { StrategyPresets, StrategyChips, StrategyMatrix, StrategyPicker });
