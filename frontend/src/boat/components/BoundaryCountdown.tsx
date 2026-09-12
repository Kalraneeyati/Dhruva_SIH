import type { BoundaryDistance } from "../../shared/types/domain";
import { useLocale } from "../../shared/hooks/useLocale";

/** CLAUDE.md: "Boundaries are indicative, never legal. Every rendered
 * EEZ/IMBL/MPA line carries the flag." `indicative` is `true` at the type
 * level (see domain.ts) so this component cannot be handed a boundary that
 * lacks the flag — and it renders the notice unconditionally, not from the
 * flag's value. */
export function BoundaryCountdown({ boundaries }: { boundaries: BoundaryDistance[] }) {
  const { t } = useLocale();
  if (boundaries.length === 0) return null;

  return (
    <section style={{ background: "var(--color-surface-raised)", borderRadius: "var(--radius-lg)", padding: "var(--space-4)" }}>
      <h3 style={{ margin: "0 0 var(--space-2)", fontSize: 15 }}>{t("boundaryHeading")}</h3>
      {boundaries.map((b, i) => (
        <div key={i} style={{ padding: "var(--space-2) 0" }}>
          <div style={{ fontSize: 16, fontWeight: 600 }}>
            {b.name} — {b.distanceNm.toFixed(1)} nm
          </div>
          <div style={{ fontSize: 12, color: "var(--color-caution)" }}>{t("indicativeNotice")}</div>
          {b.sourceUrl && (
            <div style={{ fontSize: 11, color: "var(--color-text-muted)" }}>
              {t("sourceLabel")}:{" "}
              <a href={b.sourceUrl} target="_blank" rel="noreferrer">
                {b.sourceUrl}
              </a>
            </div>
          )}
        </div>
      ))}
    </section>
  );
}
