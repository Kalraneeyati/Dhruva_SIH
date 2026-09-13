import { SectionKicker } from "./ProblemSection";

const DIFFERENTIATORS = [
  {
    icon: "\u{1F6AB}",
    title: "The numeric firewall",
    desc: "The LLM narrates, but every number it writes is checked against an evidence bundle before it ships. A fabricated wave height simply cannot reach the screen — the string gets replaced with a safe template instead.",
  },
  {
    icon: "\u{1F4E1}",
    title: "Works with zero network",
    desc: "A full advisory compresses to 145 bits — smaller than a single NavIC message segment. Scan a QR (or receive it over Bluetooth/SMS) in airplane mode and the phone reconstructs a spoken, in-language advisory. No other marine-advisory system on this brief does this.",
  },
  {
    icon: "⚖",
    title: "Honest about its own limits",
    desc: "Boundaries are always labelled indicative, never legal. PFZ data is scraped and attributed, never implied to be a live feed. Stale data is shown with its age, not silently served as current.",
  },
  {
    icon: "\u{1F5E3}",
    title: "Reasons, doesn't just retrieve",
    desc: "“Why has productivity declined” needs correlation across satellite chlorophyll and SST trends, not a lookup — the hardest of the 8 official queries, and the one that actually proves the multi-agent architecture earns its complexity.",
  },
  {
    icon: "\u{1F310}",
    title: "Vernacular by default",
    desc: "Detects the query language automatically and answers in it — starting with Hindi and Tamil, architected for Bhashini's full 22-language set.",
  },
  {
    icon: "\u{1F441}",
    title: "Explainable by construction",
    desc: "Every answer shows which agents ran, what evidence they found, and where it came from — not a black box that happens to be right.",
  },
];

const COMPARISON = [
  { row: "Conversational, multi-turn", dhruva: true, samudra: false, jal: true },
  { row: "Multi-agent reasoning (not lookup)", dhruva: true, samudra: false, jal: false },
  { row: "Numeric hallucination firewall", dhruva: true, samudra: "n/a", jal: false },
  { row: "Works fully offline (QR/BT/SMS)", dhruva: true, samudra: false, jal: false },
  { row: "Multilingual", dhruva: true, samudra: true, jal: false },
  { row: "Explainable evidence trail", dhruva: true, samudra: false, jal: "partial" },
];

export function DifferentiationSection() {
  return (
    <section style={{ padding: "var(--space-6) var(--space-4)", maxWidth: 1000, margin: "0 auto" }}>
      <SectionKicker>Why this, and not another chatbot</SectionKicker>
      <h2 style={{ fontSize: 28, margin: "0 0 var(--space-3)" }}>Built on what exists. Different where it counts.</h2>
      <p style={{ fontSize: 16, color: "var(--color-text-muted)", lineHeight: 1.7, maxWidth: 720, marginBottom: "var(--space-5)" }}>
        No single existing product does exactly this. The individual pieces — satellite-based PFZ services,
        agentic AI assistants, multilingual government AI infrastructure — all exist separately. DHRUVA's
        contribution is the synthesis, plus the parts nobody else has shipped: the numeric firewall and the
        offline capsule.
      </p>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "var(--space-3)", marginBottom: "var(--space-6)" }}>
        {DIFFERENTIATORS.map((d) => (
          <div key={d.title} style={{ background: "var(--color-surface-raised)", borderRadius: "var(--radius-md)", padding: "var(--space-4)" }}>
            <div style={{ fontSize: 24, marginBottom: 6 }}>{d.icon}</div>
            <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 6 }}>{d.title}</div>
            <div style={{ fontSize: 13, color: "var(--color-text-muted)", lineHeight: 1.5 }}>{d.desc}</div>
          </div>
        ))}
      </div>

      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13, minWidth: 480 }}>
          <thead>
            <tr style={{ textAlign: "left", borderBottom: "1px solid var(--color-border)" }}>
              <th style={{ padding: "var(--space-2)" }}></th>
              <th style={{ padding: "var(--space-2)", color: "var(--color-accent)" }}>DHRUVA</th>
              <th style={{ padding: "var(--space-2)", color: "var(--color-text-muted)" }}>INCOIS SAMUDRA 2.0</th>
              <th style={{ padding: "var(--space-2)", color: "var(--color-text-muted)" }}>Jal Anveshak</th>
            </tr>
          </thead>
          <tbody>
            {COMPARISON.map((row) => (
              <tr key={row.row} style={{ borderBottom: "1px solid var(--color-border)" }}>
                <td style={{ padding: "var(--space-2)", color: "var(--color-text-muted)" }}>{row.row}</td>
                <Cell value={row.dhruva} />
                <Cell value={row.samudra} />
                <Cell value={row.jal} />
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p style={{ fontSize: 11, color: "var(--color-text-muted)", marginTop: 8 }}>
        SAMUDRA 2.0 (INCOIS, 2026): official multilingual advisory app — static, not conversational. Jal Anveshak
        (academic, arXiv:2411.10050): fine-tuned chatbot over PFZ data, single-turn, no cross-source reasoning.
      </p>
    </section>
  );
}

function Cell({ value }: { value: boolean | string }) {
  if (value === true) return <td style={{ padding: "var(--space-2)", color: "var(--color-safe)", fontWeight: 700 }}>✓</td>;
  if (value === false) return <td style={{ padding: "var(--space-2)", color: "var(--color-nogo)" }}>✕</td>;
  return <td style={{ padding: "var(--space-2)", color: "var(--color-caution)" }}>{value}</td>;
}
