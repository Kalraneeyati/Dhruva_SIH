import type { Conditions, Observation } from "../../shared/types/domain";
import { useLocale } from "../../shared/hooks/useLocale";
import { ageLabel, formatCoord, observationOffsetKm } from "../../shared/format";

const VARIABLE_LABELS: Record<string, string> = {
  wave_height: "Wave height",
  wave_period: "Wave period",
  wave_direction: "Wave direction",
  wind_speed: "Wind speed",
  wind_direction: "Wind direction",
  current_speed: "Current speed",
  current_direction: "Current direction",
  sst: "Sea surface temp.",
  chlorophyll: "Chlorophyll",
};

/** Every value here IS an Observation, never a bare number — this component
 * cannot render a figure without a source and a timestamp because the prop
 * type does not allow it. That is the numeric firewall enforced at the type
 * level on the online path. */
function ObservationRow({ obs }: { obs: Observation }) {
  const { t } = useLocale();
  const offsetKm = observationOffsetKm(obs);
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "baseline",
        padding: "var(--space-2) 0",
        borderBottom: "1px solid var(--color-border)",
        gap: "var(--space-2)",
      }}
    >
      <span style={{ color: "var(--color-text-muted)" }}>{VARIABLE_LABELS[obs.variable] ?? obs.variable}</span>
      <span style={{ textAlign: "right" }}>
        <strong>
          {obs.value.toFixed(obs.value < 10 ? 2 : 1)} {obs.unit}
        </strong>
        <div style={{ fontSize: 11, color: "var(--color-text-muted)" }}>
          {obs.isForecast ? t("forecastLabel") : t("sourceLabel")} · {obs.datasetId} · {ageLabel(obs.fetchedAt)}
          {offsetKm > 5 ? ` · cell ${offsetKm.toFixed(0)}km away` : ""}
        </div>
      </span>
    </div>
  );
}

export function Readout({ conditions }: { conditions: Conditions }) {
  const { t } = useLocale();
  const entries = Object.entries(conditions.primary) as [string, Observation][];

  return (
    <section
      aria-label="Sea condition readout"
      style={{
        background: "var(--color-surface-raised)",
        borderRadius: "var(--radius-lg)",
        padding: "var(--space-4)",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "var(--space-2)", fontSize: 13, color: "var(--color-text-muted)" }}>
        <span>{formatCoord(conditions.requestedLat, conditions.requestedLon)}</span>
        <span>{ageLabel(conditions.when)}</span>
      </div>
      {entries.map(([variable, obs]) => (
        <ObservationRow key={variable} obs={obs} />
      ))}
      {conditions.missing.length > 0 && (
        <p style={{ fontSize: 12, color: "var(--color-caution)", marginTop: "var(--space-2)" }}>
          {t("noEvidence")} ({conditions.missing.join(", ")})
        </p>
      )}
      {conditions.disagreements.length > 0 && (
        <p style={{ fontSize: 12, color: "var(--color-text-muted)", marginTop: "var(--space-2)" }}>
          {conditions.disagreements.length} source disagreement(s) — see Study for detail.
        </p>
      )}
    </section>
  );
}
