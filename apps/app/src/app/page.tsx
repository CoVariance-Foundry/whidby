export default function EvalDashboard() {
  return (
    <main style={{ maxWidth: 720, margin: "80px auto", fontFamily: "system-ui, sans-serif" }}>
      <h1>Widby Eval Dashboard</h1>
      <p>Internal tool for testing and evaluating scoring engine modules.</p>
      <ul>
        <li>
          <strong>M0</strong> — DataForSEO Client <span style={{ color: "#999" }}>(ready)</span>
        </li>
        <li>
          <strong>M1</strong> — Metro Database <span style={{ color: "#999" }}>(ready)</span>
        </li>
        <li>
          <strong>M2</strong> — Supabase Schema <span style={{ color: "#999" }}>(ready)</span>
        </li>
        <li>
          <strong>M3</strong> — LLM Client <span style={{ color: "#999" }}>(ready)</span>
        </li>
        <li>
          <strong>M4</strong> — Keyword Expansion{" "}
          <span style={{ color: "#ccc" }}>(Phase 2)</span>
        </li>
        <li>
          <strong>M5–M9</strong> — Scoring Pipeline{" "}
          <span style={{ color: "#ccc" }}>(Phase 2)</span>
        </li>
        <li>
          <strong>M10–M15</strong> — Experiment Framework{" "}
          <span style={{ color: "#ccc" }}>(Phase 3)</span>
        </li>
      </ul>
      <p style={{ marginTop: 40, color: "#666", fontSize: 14 }}>
        Module eval pages will be added here as each module is completed.
      </p>
    </main>
  );
}
