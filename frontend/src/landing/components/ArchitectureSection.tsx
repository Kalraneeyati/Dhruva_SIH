import { SectionKicker } from "./ProblemSection";

const SPECIALISTS = [
  { icon: "\u{1F30A}", name: "Marine Data Discovery", desc: "Finds the right dataset for the query's place and time" },
  { icon: "\u{26C8}", name: "Weather Intelligence", desc: "Wind, waves, lightning, cyclone forecasts" },
  { icon: "\u{1F4C8}", name: "Ocean Analytics", desc: "SST/chlorophyll trends, productivity-decline reasoning" },
  { icon: "\u{1F4CD}", name: "Geospatial Reasoning", desc: "Nearest-PFZ, distances, spatial joins" },
  { icon: "\u{2696}", name: "Risk Assessment", desc: "Combines every hazard into one safe/caution/no-go verdict" },
  { icon: "\u{1F5FA}", name: "Visualization", desc: "Maps and charts to accompany the answer" },
];

const NUMBERED_STEPS = [
  { n: "1", title: "Understand", desc: "Detect language, decompose the question into sub-tasks" },
  { n: "2", title: "Reason", desc: "Route to specialist agents in parallel, cross-check disagreeing sources" },
  { n: "3", title: "Validate", desc: "The numeric firewall checks every figure against its evidence before it ships" },
  { n: "4", title: "Answer", desc: "Explainable narration, in-language, with a map and a capsule for offline reach" },
];

export function ArchitectureSection() {
  return (
    <section style={{ padding: "var(--space-6) var(--space-4)", maxWidth: 1000, margin: "0 auto" }}>
      <SectionKicker>The approach</SectionKicker>
      <h2 style={{ fontSize: 28, margin: "0 0 var(--space-3)" }}>A planner, six specialists, and a rule the LLM can't break</h2>
      <p style={{ fontSize: 16, color: "var(--color-text-muted)", lineHeight: 1.7, maxWidth: 720, marginBottom: "var(--space-5)" }}>
        DHRUVA decomposes every question into a plan, runs the relevant specialist agents in parallel, and
        synthesizes one answer — exactly ISRO's suggested org chart. The user-interaction layer wraps the whole
        graph, so everything inside reasons in English while the person asking never has to.
      </p>

      {/* Flow: user -> planner -> specialists (parallel) -> risk/reporting -> user */}
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "var(--space-2)", marginBottom: "var(--space-6)" }}>
        <PipelineNode icon="🧭" label="Planning Agent" sub="decomposes the query, never calls a tool itself" accent />
        <Arrow />
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: "var(--space-3)", width: "100%" }}>
          {SPECIALISTS.map((s) => (
            <div key={s.name} style={{ background: "var(--color-surface-raised)", borderRadius: "var(--radius-md)", padding: "var(--space-3)", textAlign: "center", border: "1px solid var(--color-border)" }}>
              <div style={{ fontSize: 22 }}>{s.icon}</div>
              <div style={{ fontWeight: 700, fontSize: 13, margin: "4px 0" }}>{s.name}</div>
              <div style={{ fontSize: 11, color: "var(--color-text-muted)" }}>{s.desc}</div>
            </div>
          ))}
        </div>
        <Arrow />
        <PipelineNode icon="📝" label="Reporting &amp; Citation Agent" sub="assembles the final answer with evidence links" accent />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "var(--space-4)" }}>
        {NUMBERED_STEPS.map((step) => (
          <div key={step.n}>
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: "50%",
                background: "var(--color-accent)",
                color: "var(--color-accent-text)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontWeight: 700,
                marginBottom: 8,
              }}
            >
              {step.n}
            </div>
            <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 4 }}>{step.title}</div>
            <div style={{ fontSize: 13, color: "var(--color-text-muted)" }}>{step.desc}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

function PipelineNode({ icon, label, sub, accent }: { icon: string; label: string; sub: string; accent?: boolean }) {
  return (
    <div
      style={{
        background: accent ? "var(--color-accent)" : "var(--color-surface-raised)",
        color: accent ? "var(--color-accent-text)" : "var(--color-text)",
        borderRadius: "var(--radius-md)",
        padding: "var(--space-3) var(--space-5)",
        textAlign: "center",
      }}
    >
      <div style={{ fontSize: 20 }}>{icon}</div>
      <div style={{ fontWeight: 700, fontSize: 14 }}>{label}</div>
      <div style={{ fontSize: 11, opacity: 0.85 }}>{sub}</div>
    </div>
  );
}

function Arrow() {
  return (
    <div aria-hidden style={{ fontSize: 20, color: "var(--color-text-muted)" }}>
      ↓
    </div>
  );
}
