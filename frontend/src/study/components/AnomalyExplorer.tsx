import { LineChart } from "../../shared/charts/LineChart";
import { MOCK_CHLOROPHYLL_SERIES, MOCK_SST_SERIES } from "../../shared/api/mock";
import { useLocale } from "../../shared/hooks/useLocale";

/**
 * Two small-multiple charts, not one dual-axis chart — chlorophyll (mg/m3)
 * and SST (degC) are different scales, and the dataviz skill's #1 rule is
 * "never a dual-axis chart." This is also the visual evidence behind the
 * productivity_decline narrative shown on the boat surface for that query.
 */
export function AnomalyExplorer() {
  const { t } = useLocale();
  return (
    <section style={{ background: "var(--color-surface-raised)", borderRadius: "var(--radius-lg)", padding: "var(--space-4)", display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
      <h3 style={{ margin: 0, fontSize: 15 }}>{t("anomalyHeading")}</h3>
      <LineChart title="Chlorophyll" unit="mg/m3" points={MOCK_CHLOROPHYLL_SERIES} color="#3987e5" />
      <LineChart title="Sea surface temperature" unit="°C" points={MOCK_SST_SERIES} color="#d95926" />
    </section>
  );
}
