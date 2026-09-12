import type { RiskVerdict } from "../../shared/types/domain";
import { useLocale } from "../../shared/hooks/useLocale";
import { RISK_VISUALS, riskLabel } from "../../shared/theme/risk";
import { formatAgeSeconds } from "../../shared/format";

/**
 * The verdict card. IMPLEMENTATION.md: "NO-GO outranks everything. A
 * favourable fishing zone never renders above an active hazard" — BoatApp
 * enforces the render ORDER (this component always mounts before PfzRow);
 * this component enforces the visual weight (an active override gets a
 * full-width banner, not just a coloured chip, so it cannot be missed even at
 * a glance).
 */
export function VerdictCard({ verdict }: { verdict: RiskVerdict }) {
  const { locale, t } = useLocale();
  const visual = RISK_VISUALS[verdict.riskClass];
  const label = riskLabel(verdict.riskClass, locale);

  return (
    <section
      aria-label="Risk verdict"
      style={{
        background: "var(--color-surface-raised)",
        border: `2px solid ${visual.bgVar}`,
        borderRadius: "var(--radius-lg)",
        padding: "var(--space-5)",
        display: "flex",
        flexDirection: "column",
        gap: "var(--space-3)",
      }}
    >
      {verdict.overrideActive && (
        <div
          role="alert"
          style={{
            background: "var(--color-nogo)",
            color: "var(--color-nogo-text)",
            borderRadius: "var(--radius-md)",
            padding: "var(--space-3) var(--space-4)",
            fontWeight: 700,
          }}
        >
          {"✕"} {t("verdictNoGo")} — {verdict.overrideReason}
        </div>
      )}

      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-4)" }}>
        <div
          aria-hidden
          style={{
            background: visual.bgVar,
            color: visual.textVar,
            borderRadius: "999px",
            width: 64,
            height: 64,
            minWidth: 64,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 28,
            fontWeight: 700,
          }}
        >
          {visual.glyph}
        </div>
        <div>
          <div style={{ fontSize: 22, fontWeight: 700, color: visual.bgVar }}>{label}</div>
          <div style={{ color: "var(--color-text-muted)", fontSize: 13 }}>
            {t("boatClassLabel")}: {verdict.boatClass.replaceAll("_", " ")}
          </div>
        </div>
      </div>

      <div style={{ fontSize: 13, color: "var(--color-text-muted)" }}>
        {t("dataAge")}: {formatAgeSeconds(verdict.dataAgeSeconds)}
      </div>

      <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
        {verdict.factors.map((factor) => (
          <li
            key={factor.ruleId}
            style={{
              background: "var(--color-surface)",
              borderRadius: "var(--radius-sm)",
              padding: "var(--space-3)",
              fontSize: 14,
            }}
          >
            <strong style={{ textTransform: "capitalize" }}>{factor.hazard}</strong>: {factor.narrative}
          </li>
        ))}
      </ul>

      <p style={{ margin: 0, fontSize: 12, color: "var(--color-text-muted)" }}>{verdict.advisoryNotice}</p>
    </section>
  );
}
