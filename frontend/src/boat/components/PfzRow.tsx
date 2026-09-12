import type { PfzRecord } from "../../shared/types/domain";
import { useLocale } from "../../shared/hooks/useLocale";

/** CLAUDE.md: "PFZ has no API — it is scraped and attributed. Never imply a
 * feed exists." This row cannot render a PfzRecord without sourceUrl — the
 * type requires it — and always shows the attribution line, never just the
 * bearing/distance. */
export function PfzRow({ records }: { records: PfzRecord[] }) {
  const { t } = useLocale();
  if (records.length === 0) {
    return (
      <section style={{ background: "var(--color-surface-raised)", borderRadius: "var(--radius-lg)", padding: "var(--space-4)" }}>
        <h3 style={{ margin: "0 0 var(--space-2)", fontSize: 15 }}>{t("pfzHeading")}</h3>
        <p style={{ margin: 0, fontSize: 13, color: "var(--color-text-muted)" }}>No confident PFZ found nearby today.</p>
      </section>
    );
  }

  return (
    <section style={{ background: "var(--color-surface-raised)", borderRadius: "var(--radius-lg)", padding: "var(--space-4)" }}>
      <h3 style={{ margin: "0 0 var(--space-2)", fontSize: 15 }}>{t("pfzHeading")}</h3>
      {records.map((rec, i) => (
        <div key={i} style={{ padding: "var(--space-2) 0", borderBottom: i < records.length - 1 ? "1px solid var(--color-border)" : "none" }}>
          <div style={{ fontSize: 16, fontWeight: 600 }}>
            {rec.distanceNm != null ? `${rec.distanceNm.toFixed(0)} nm` : "distance unknown"}{" "}
            {rec.bearingDeg != null ? `bearing ${rec.bearingDeg.toFixed(0)}°` : ""} of {rec.landingCentre}
          </div>
          {rec.depthM != null && <div style={{ fontSize: 13, color: "var(--color-text-muted)" }}>Depth ~{rec.depthM.toFixed(0)} m</div>}
          <div style={{ fontSize: 11, color: "var(--color-text-muted)" }}>
            {t("scrapedNotice")} ·{" "}
            <a href={rec.sourceUrl} target="_blank" rel="noreferrer">
              {rec.sourceUrl}
            </a>{" "}
            · issued {rec.issuedFor}
          </div>
        </div>
      ))}
    </section>
  );
}
