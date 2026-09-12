import { useState } from "react";
import { EXAMPLE_QUERIES, MOCK_ADVISORIES } from "../../shared/api/mock";
import { useLocale } from "../../shared/hooks/useLocale";
import type { QueryIntent } from "../../shared/types/domain";

/**
 * A local stand-in for the Langfuse trace inspector CLAUDE.md commits to
 * ("Observability: Langfuse, self-hosted — traces double as the
 * explainability record"). Running Langfuse itself needs its own Postgres
 * database and container — out of scope for a frontend-only Phase 5 pass —
 * so this reads the same `QueryTrace[]` shape the real Langfuse-backed
 * inspector will read, off the mock advisories. Swapping in real traces later
 * is a data-source change, not a UI rewrite.
 */
export function TraceInspector() {
  const { t } = useLocale();
  const [intent, setIntent] = useState<QueryIntent>("safe_to_venture");
  const advisory = MOCK_ADVISORIES[intent];

  return (
    <section style={{ background: "var(--color-surface-raised)", borderRadius: "var(--radius-lg)", padding: "var(--space-4)" }}>
      <h3 style={{ margin: "0 0 var(--space-3)", fontSize: 15 }}>{t("traceHeading")}</h3>
      <select
        value={intent}
        onChange={(e) => setIntent(e.target.value as QueryIntent)}
        style={{ minHeight: 40, marginBottom: "var(--space-3)", width: "100%", maxWidth: 420 }}
      >
        {EXAMPLE_QUERIES.map((q) => (
          <option key={q.intent} value={q.intent}>
            {q.text}
          </option>
        ))}
      </select>

      <ol style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
        {advisory.trace.map((step, i) => (
          <li
            key={i}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "var(--space-3)",
              background: "var(--color-surface)",
              borderRadius: "var(--radius-sm)",
              padding: "var(--space-2) var(--space-3)",
              fontSize: 13,
            }}
          >
            <span
              aria-hidden
              style={{
                width: 22,
                height: 22,
                borderRadius: "50%",
                background: step.ok ? "var(--color-safe)" : "var(--color-nogo)",
                color: step.ok ? "var(--color-safe-text)" : "var(--color-nogo-text)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 12,
                flexShrink: 0,
              }}
            >
              {i + 1}
            </span>
            <div>
              <strong>{step.agent}</strong>
              <div style={{ color: "var(--color-text-muted)", fontSize: 12 }}>{step.summary}</div>
            </div>
          </li>
        ))}
      </ol>

      <p style={{ fontSize: 11, color: "var(--color-text-muted)", marginTop: "var(--space-3)" }}>
        Backed by mock trace data. Once Phase 3's graph ships with real Langfuse spans, this reads the live trace for the same intent.
      </p>
    </section>
  );
}
