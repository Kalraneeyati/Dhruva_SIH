import type { FleetVessel } from "../../shared/types/domain";
import { ageLabel } from "../../shared/format";
import { useLocale } from "../../shared/hooks/useLocale";

/** Vessels with an active override or a breach_warning status, surfaced
 * separately from the full fleet list so shore staff do not have to scan the
 * whole roster to find the one boat that matters right now. */
export function BreachWatch({ fleet }: { fleet: FleetVessel[] }) {
  const { t } = useLocale();
  const flagged = fleet.filter((v) => v.status === "breach_warning" || v.verdict?.overrideActive);

  return (
    <section style={{ background: "var(--color-surface-raised)", borderRadius: "var(--radius-lg)", padding: "var(--space-4)", border: flagged.length > 0 ? "1px solid var(--color-nogo)" : "1px solid var(--color-border)" }}>
      <h3 style={{ margin: "0 0 var(--space-2)", fontSize: 15 }}>
        {t("breachWatchHeading")} ({flagged.length})
      </h3>
      {flagged.length === 0 ? (
        <p style={{ margin: 0, fontSize: 13, color: "var(--color-text-muted)" }}>No active breach warnings.</p>
      ) : (
        flagged.map((v) => (
          <div key={v.vesselId} style={{ padding: "var(--space-2) 0", borderBottom: "1px solid var(--color-border)", fontSize: 13 }}>
            <strong style={{ color: "var(--color-nogo)" }}>{v.name}</strong> ({v.vesselId})
            <div style={{ color: "var(--color-text-muted)" }}>
              {v.verdict?.overrideReason ?? "No report received"} — last seen {v.position ? ageLabel(v.position.observedAt) : "unknown"}
            </div>
          </div>
        ))
      )}
    </section>
  );
}
