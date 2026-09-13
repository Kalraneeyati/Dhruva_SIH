import { useEffect, useState } from "react";
import type { QueryTrace } from "../../shared/types/domain";
import { useLocale } from "../../shared/hooks/useLocale";

const AGENT_GLYPH: Record<string, string> = {
  planner: "\u{1F9ED}", // compass
  discovery: "\u{1F30A}", // wave
  marine_data_discovery: "\u{1F30A}",
  weather_intelligence: "\u{26C8}", // storm cloud
  ocean_analytics: "\u{1F4C8}", // chart
  geospatial_reasoning: "\u{1F4CD}", // pin
  risk_assessment: "\u{2696}", // scale
  route: "\u{1F5FA}", // map
  evidence: "\u{1F4CE}",
  reporting: "\u{1F4DD}",
};

function glyphFor(agent: string): string {
  return AGENT_GLYPH[agent] ?? "\u{1F916}"; // robot fallback
}

function labelFor(agent: string): string {
  return agent.replaceAll("_", " ");
}

/**
 * Visualizes the orchestrator -> specialist-agent handoff live, instead of
 * a collapsed text list. This exists because the entire pitch for an
 * "agentic" system collapses if a judge can't SEE the multi-agent part
 * happening — a paragraph of prose that happens to be correct looks
 * identical to a single LLM call. Steps light up in sequence on mount so
 * the pipeline reads as something that just ran, not a static diagram.
 */
export function AgentPipeline({ trace }: { trace: QueryTrace[] }) {
  const { t } = useLocale();
  const [revealed, setRevealed] = useState(0);

  useEffect(() => {
    setRevealed(0);
    if (trace.length === 0) return;
    const timers = trace.map((_, i) => setTimeout(() => setRevealed(i + 1), 220 * (i + 1)));
    return () => timers.forEach(clearTimeout);
  }, [trace]);

  if (trace.length === 0) return null;

  return (
    <section
      aria-label="Multi-agent execution pipeline"
      style={{
        background: "var(--color-surface-raised)",
        borderRadius: "var(--radius-lg)",
        padding: "var(--space-4)",
        border: "1px solid var(--color-border)",
      }}
    >
      <h3 style={{ margin: "0 0 var(--space-1)", fontSize: 14, color: "var(--color-text-muted)", textTransform: "uppercase", letterSpacing: 0.5 }}>
        {t("traceHeading")}
      </h3>
      <p style={{ margin: "0 0 var(--space-3)", fontSize: 12, color: "var(--color-text-muted)" }}>
        Planner routed this query to {trace.length} specialist agent{trace.length !== 1 ? "s" : ""} — every figure below traces back to one of them.
      </p>
      <div style={{ display: "flex", alignItems: "center", overflowX: "auto", paddingBottom: 4 }}>
        {trace.map((step, i) => {
          const active = i < revealed;
          return (
            <div key={i} style={{ display: "flex", alignItems: "center", flex: "0 0 auto" }}>
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: 4,
                  minWidth: 84,
                  opacity: active ? 1 : 0.35,
                  transform: active ? "translateY(0)" : "translateY(4px)",
                  transition: "opacity 300ms ease, transform 300ms ease",
                }}
              >
                <div
                  aria-hidden
                  style={{
                    width: 40,
                    height: 40,
                    borderRadius: "50%",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: 18,
                    background: active ? (step.ok ? "var(--color-safe)" : "var(--color-nogo)") : "var(--color-surface)",
                    color: active ? (step.ok ? "var(--color-safe-text)" : "var(--color-nogo-text)") : "var(--color-text-muted)",
                    border: "2px solid var(--color-border)",
                    boxShadow: active ? "0 0 0 3px rgba(55,194,106,0.15)" : "none",
                  }}
                >
                  {glyphFor(step.agent)}
                </div>
                <span style={{ fontSize: 11, textAlign: "center", textTransform: "capitalize", color: "var(--color-text)" }}>{labelFor(step.agent)}</span>
              </div>
              {i < trace.length - 1 && (
                <div
                  aria-hidden
                  style={{
                    width: 28,
                    height: 2,
                    background: i < revealed - 1 ? "var(--color-safe)" : "var(--color-border)",
                    transition: "background 300ms ease",
                    flex: "0 0 auto",
                    marginBottom: 20,
                  }}
                />
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
