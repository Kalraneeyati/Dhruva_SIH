import type { CSSProperties } from "react";
import { Link } from "react-router-dom";
import { Hero } from "./components/Hero";
import { ProblemSection } from "./components/ProblemSection";
import { ArchitectureSection } from "./components/ArchitectureSection";
import { DifferentiationSection } from "./components/DifferentiationSection";
import { TrySection } from "./components/TrySection";

export function Landing() {
  return (
    <div>
      <Hero />
      <Divider />
      <ProblemSection />
      <Divider />
      <ArchitectureSection />
      <Divider />
      <DifferentiationSection />
      <Divider />
      <TrySection />

      <section style={{ padding: "var(--space-6) var(--space-4)", textAlign: "center" }}>
        <h2 style={{ fontSize: 24, margin: "0 0 var(--space-3)" }}>See it work end to end</h2>
        <p style={{ color: "var(--color-text-muted)", maxWidth: 560, margin: "0 auto var(--space-4)" }}>
          Boat surface for the fisherman, Shore Console for the coast guard, Study routes for the researcher —
          one backend, three surfaces, all built on the same evidence.
        </p>
        <div style={{ display: "flex", justifyContent: "center", gap: "var(--space-3)", flexWrap: "wrap" }}>
          <Link to="/boat" style={ctaStyle(true)}>
            🚤 Boat surface
          </Link>
          <Link to="/shore" style={ctaStyle(false)}>
            🗺️ Shore console
          </Link>
          <Link to="/study" style={ctaStyle(false)}>
            📊 Study routes
          </Link>
        </div>
      </section>

      <footer style={{ textAlign: "center", padding: "var(--space-5) var(--space-4)", fontSize: 12, color: "var(--color-text-muted)" }}>
        DHRUVA — ISRO PS 26176 (ORCA). Advisory only. Follow official INCOIS and IMD warnings.
      </footer>
    </div>
  );
}

function ctaStyle(primary: boolean): CSSProperties {
  return {
    background: primary ? "var(--color-accent)" : "transparent",
    color: primary ? "var(--color-accent-text)" : "var(--color-text)",
    border: primary ? "none" : "1px solid var(--color-border)",
    fontWeight: 700,
    padding: "12px 24px",
    borderRadius: "var(--radius-md)",
    textDecoration: "none",
    minHeight: "var(--touch-target)",
    display: "inline-flex",
    alignItems: "center",
  };
}

function Divider() {
  return <div style={{ height: 1, background: "var(--color-border)", maxWidth: 1000, margin: "0 auto" }} />;
}
