import type { AdvisoryResponse } from "../../shared/types/domain";
import { useLocale } from "../../shared/hooks/useLocale";

/**
 * Shows the numeric-firewall status for this answer's narration
 * (IMPLEMENTATION.md 3.3). This is deliberately visible, not hidden in a
 * console log — a judge (or a fisherman) should be able to see that the
 * system checked its own narration against evidence before showing it, and
 * be told plainly on the rare occasion it had to fall back to a template.
 *
 * The agent-by-agent trace itself lives in AgentPipeline (a visual pipeline,
 * shown above this panel) — this stays focused on the one claim that matters
 * here: did the narration you're reading pass validation.
 */
export function EvidencePanel({ response }: { response: AdvisoryResponse }) {
  const { t } = useLocale();
  const { firewallRetried, firewallFellBackToTemplate } = response;

  return (
    <section style={{ background: "var(--color-surface)", borderRadius: "var(--radius-lg)", padding: "var(--space-4)", fontSize: 13 }}>
      <h3 style={{ margin: "0 0 var(--space-2)", fontSize: 14 }}>{t("evidenceHeading")}</h3>
      {!firewallRetried && !firewallFellBackToTemplate && (
        <p style={{ margin: 0, color: "var(--color-safe)" }}>✓ Narration validated against evidence on first pass — every number above traces to a source.</p>
      )}
      {firewallRetried && !firewallFellBackToTemplate && (
        <p style={{ margin: 0, color: "var(--color-caution)" }}>⚠ {t("firewallRetried")}</p>
      )}
      {firewallFellBackToTemplate && <p style={{ margin: 0, color: "var(--color-caution)" }}>⚠ {t("firewallFallback")}</p>}
    </section>
  );
}
