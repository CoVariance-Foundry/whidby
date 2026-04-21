export default function SavedSearchesBlock() {
  return (
    <section
      aria-labelledby="saved-heading"
      style={{
        background: "var(--card)",
        border: "1px solid var(--rule)",
        borderRadius: 12,
        padding: "18px 20px",
      }}
    >
      <h2
        id="saved-heading"
        style={{
          fontFamily: "var(--serif)",
          fontSize: 18,
          fontWeight: 600,
          color: "var(--ink)",
          margin: "0 0 12px",
        }}
      >
        Saved searches
      </h2>
      <p
        style={{
          fontFamily: "var(--sans)",
          fontSize: 13.5,
          color: "var(--ink-2)",
          margin: 0,
        }}
      >
        Coming soon. Pin a niche from the finder to see it here.
      </p>
    </section>
  );
}
