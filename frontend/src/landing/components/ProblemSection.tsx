import type { ReactNode } from "react";

const STAKEHOLDERS = [
  { icon: "\u{1F3A3}", label: "Fishermen", need: "Where is it safe? Where are the fish?" },
  { icon: "\u{1F6A2}", label: "Maritime operators", need: "Safe routes, boundary awareness" },
  { icon: "\u{1F3DB}", label: "Coastal authorities", need: "Disaster response, hazard alerts" },
  { icon: "\u{1F52C}", label: "Researchers", need: "Explainable trend analysis" },
];

export function ProblemSection() {
  return (
    <section id="problem" style={{ padding: "var(--space-6) var(--space-4)", maxWidth: 900, margin: "0 auto" }}>
      <SectionKicker>The problem</SectionKicker>
      <h2 style={{ fontSize: 28, margin: "0 0 var(--space-3)" }}>Ocean data exists. Understanding doesn't.</h2>
      <p style={{ fontSize: 16, color: "var(--color-text-muted)", lineHeight: 1.7, maxWidth: 720 }}>
        ISRO and global agencies generate huge volumes of satellite Earth Observation and oceanographic data
        every day — sea surface temperature, chlorophyll, wave forecasts, cyclone tracks. But a fisherman
        deciding whether to sail tomorrow morning can't query a NetCDF file. Existing tools (INCOIS SAMUDRA 2.0,
        academic chatbots) either push raw advisories or answer one narrow question — none <em>reason</em>{" "}
        across sources, in the user's own language, with evidence attached.
      </p>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: "var(--space-3)", marginTop: "var(--space-5)" }}>
        {STAKEHOLDERS.map((s) => (
          <div key={s.label} style={{ background: "var(--color-surface-raised)", borderRadius: "var(--radius-md)", padding: "var(--space-4)", textAlign: "center" }}>
            <div style={{ fontSize: 28, marginBottom: 6 }}>{s.icon}</div>
            <div style={{ fontWeight: 700, fontSize: 14 }}>{s.label}</div>
            <div style={{ fontSize: 12, color: "var(--color-text-muted)", marginTop: 4 }}>{s.need}</div>
          </div>
        ))}
      </div>

      <div style={{ marginTop: "var(--space-5)", background: "var(--color-surface)", borderRadius: "var(--radius-md)", padding: "var(--space-4)", borderLeft: "3px solid var(--color-caution)" }}>
        <strong style={{ fontSize: 13 }}>The brief (ISRO PS 26176):</strong>
        <p style={{ margin: "6px 0 0", fontSize: 14, color: "var(--color-text-muted)" }}>
          Build an agentic AI conversational platform that decomposes natural-language questions, coordinates
          specialist agents across heterogeneous marine datasets, performs spatial-temporal reasoning, and
          returns explainable, evidence-backed answers — in the user's own language, with proactive hazard
          alerts and geofencing near restricted waters.
        </p>
      </div>
    </section>
  );
}

export function SectionKicker({ children }: { children: ReactNode }) {
  return (
    <div style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: 1, color: "var(--color-accent)", fontWeight: 700, marginBottom: 8 }}>
      {children}
    </div>
  );
}
