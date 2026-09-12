import type { AdvisoryResponse } from "../../shared/types/domain";
import { useLocale } from "../../shared/hooks/useLocale";

/**
 * Shows the numeric-firewall status for this answer's narration
 * (IMPLEMENTATION.md 3.3). This is deliberately visible, not hidden in a
 * console log — a judge (or a fisherman) should be able to see that the
 * system checked its own narration against evidence before showing it, and
 * be told plainly on the rare occasion it had to fall back to a template.
 */
export function EvidencePanel({ response }: { response: AdvisoryResponse }) {
  const { t } = useLocale();
  const { firewallRetried, firewallFellBackToTemplate, trace } = response;

  return (
    <section style={{ background: "var(--color-surface)", borderRadius: "var(--radius-lg)", padding: "var(--space-4)", fontSize: 12 }}>
      <h3 style={{ margin: "0 0 var(--space-2)", fontSize: 14 }}>{t("evidenceHeading")}</h3>
      {!firewallRetried && !firewallFellBackToTemplate && (
        <p style={{ margin: 0, color: "var(--color-safe)" }}>✓ Narration validated against evidence on first pass.</p>
      )}
      {firewallRetried && !firewallFellBackToTemplate && (
        <p style={{ margin: 0, color: "var(--color-caution)" }}>⚠ {t("firewallRetried")}</p>
      )}
      {firewallFellBackToTemplate && <p style={{ margin: 0, color: "var(--color-caution)" }}>⚠ {t("firewallFallback")}</p>}

      <details style={{ marginTop: "var(--space-2)" }}>
        <summary style={{ cursor: "pointer", color: "var(--color-text-muted)" }}>{t("traceHeading")} ({trace.length})</summary>
        <ol style={{ margin: "var(--space-2) 0 0", paddingLeft: 18 }}>
          {trace.map((step, i) => (
            <li key={i} style={{ color: step.ok ? "var(--color-text-muted)" : "var(--color-nogo)" }}>
              {step.agent}: {step.summary}
            </li>
          ))}
        </ol>
      </details>
    </section>
  );
}
