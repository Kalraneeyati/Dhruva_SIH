import { DivergingBarChart } from "../../shared/charts/DivergingBarChart";
import { MOCK_SST_ANOMALY_SERIES } from "../../shared/api/mock";
import { useLocale } from "../../shared/hooks/useLocale";

/**
 * Marine heatwave view — SST anomaly against the Hobday-style seasonal
 * baseline IMPLEMENTATION.md's INCOIS-archive data strategy targets (9 years
 * of daily SST for a 90th-percentile climatology). This chart shows the
 * derived anomaly, not raw SST, because sign-relative-to-baseline is the
 * entire analytical point of a heatwave view.
 */
export function HeatwaveView() {
  const { t } = useLocale();
  return (
    <section style={{ background: "var(--color-surface-raised)", borderRadius: "var(--radius-lg)", padding: "var(--space-4)" }}>
      <h3 style={{ margin: "0 0 var(--space-3)", fontSize: 15 }}>{t("heatwaveHeading")}</h3>
      <DivergingBarChart title="SST anomaly" unit="°C" points={MOCK_SST_ANOMALY_SERIES} />
      <p style={{ fontSize: 11, color: "var(--color-text-muted)", marginTop: "var(--space-2)" }}>
        Baseline: INCOIS NOAA AVHRR/AMSR archive (2002–2011), 90th-percentile seasonal climatology per Hobday et al. Illustrative demo values — see IMPLEMENTATION.md Phase 3.
      </p>
    </section>
  );
}
