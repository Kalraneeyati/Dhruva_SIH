import type { FleetVessel } from "../../shared/types/domain";
import { RISK_VISUALS } from "../../shared/theme/risk";
import { ageLabel } from "../../shared/format";
import { useLocale } from "../../shared/hooks/useLocale";

const STATUS_LABELS: Record<FleetVessel["status"], string> = {
  underway: "Underway",
  at_port: "At port",
  no_report: "No report",
  breach_warning: "Breach warning",
};

export function FleetList({ fleet, selected, onSelect }: { fleet: FleetVessel[]; selected: string | null; onSelect: (id: string) => void }) {
  const { t } = useLocale();
  return (
    <section style={{ background: "var(--color-surface-raised)", borderRadius: "var(--radius-lg)", padding: "var(--space-4)" }}>
      <h3 style={{ margin: "0 0 var(--space-3)", fontSize: 15 }}>
        {t("fleetHeading")} ({fleet.length})
      </h3>
      <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
        {fleet.map((v) => {
          const visual = v.verdict ? RISK_VISUALS[v.verdict.riskClass] : RISK_VISUALS.unknown;
          const isSelected = v.vesselId === selected;
          return (
            <button
              key={v.vesselId}
              onClick={() => onSelect(v.vesselId)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "var(--space-3)",
                textAlign: "left",
                padding: "var(--space-2) var(--space-3)",
                borderRadius: "var(--radius-md)",
                border: isSelected ? "1px solid var(--color-accent)" : "1px solid var(--color-border)",
                background: v.status === "breach_warning" ? "rgba(255,90,90,0.08)" : "var(--color-surface)",
                color: "var(--color-text)",
                minHeight: "var(--touch-target)",
              }}
            >
              <span
                aria-hidden
                style={{
                  background: visual.bgVar,
                  color: visual.textVar,
                  borderRadius: "50%",
                  width: 28,
                  height: 28,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 14,
                  flexShrink: 0,
                }}
              >
                {visual.glyph}
              </span>
              <span style={{ flex: 1 }}>
                <div style={{ fontWeight: 600 }}>{v.name}</div>
                <div style={{ fontSize: 12, color: "var(--color-text-muted)" }}>
                  {v.vesselId} · {v.boatClass.replaceAll("_", " ")} · {STATUS_LABELS[v.status]}
                </div>
              </span>
              <span style={{ fontSize: 11, color: "var(--color-text-muted)", textAlign: "right" }}>
                {v.lastCapsuleAt ? `capsule ${ageLabel(v.lastCapsuleAt)}` : "no capsule"}
              </span>
            </button>
          );
        })}
      </div>
    </section>
  );
}
