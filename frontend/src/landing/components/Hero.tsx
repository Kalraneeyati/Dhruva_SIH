import { Link } from "react-router-dom";

export function Hero() {
  return (
    <section
      style={{
        padding: "var(--space-6) var(--space-4) var(--space-5)",
        textAlign: "center",
        background: "radial-gradient(ellipse at top, rgba(28,110,164,0.35), transparent 60%)",
      }}
    >
      <span
        style={{
          display: "inline-block",
          fontSize: 12,
          letterSpacing: 1,
          textTransform: "uppercase",
          color: "var(--color-accent)",
          border: "1px solid var(--color-accent)",
          borderRadius: 999,
          padding: "4px 14px",
          marginBottom: "var(--space-4)",
        }}
      >
        Smart India Hackathon 2026 · ISRO PS 26176 · ORCA
      </span>

      <h1 style={{ fontSize: "clamp(32px, 6vw, 56px)", margin: "0 0 var(--space-3)", lineHeight: 1.1 }}>
        DHRUVA
      </h1>
      <p style={{ fontSize: "clamp(15px, 2.2vw, 20px)", color: "var(--color-text-muted)", maxWidth: 640, margin: "0 auto var(--space-2)" }}>
        Deep-sea Hazard, Routing &amp; Understanding via Vernacular Agents
      </p>
      <p style={{ fontSize: 15, color: "var(--color-accent)", maxWidth: 560, margin: "0 auto var(--space-5)", fontStyle: "italic" }}>
        "Reasoning runs onshore. Answers survive offshore."
      </p>

      <div style={{ display: "flex", justifyContent: "center", gap: "var(--space-3)", flexWrap: "wrap" }}>
        <Link
          to="/boat"
          style={{
            background: "var(--color-accent)",
            color: "var(--color-accent-text)",
            fontWeight: 700,
            padding: "14px 32px",
            borderRadius: "var(--radius-md)",
            textDecoration: "none",
            fontSize: 16,
            minHeight: "var(--touch-target)",
            display: "inline-flex",
            alignItems: "center",
          }}
        >
          Launch the live demo →
        </Link>
        <a
          href="#problem"
          style={{
            border: "1px solid var(--color-border)",
            color: "var(--color-text)",
            padding: "14px 28px",
            borderRadius: "var(--radius-md)",
            textDecoration: "none",
            fontSize: 16,
            minHeight: "var(--touch-target)",
            display: "inline-flex",
            alignItems: "center",
          }}
        >
          The problem &amp; approach ↓
        </a>
      </div>
    </section>
  );
}
