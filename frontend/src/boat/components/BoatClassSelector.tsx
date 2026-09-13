import { useLocale } from "../../shared/hooks/useLocale";
import type { BoatClass } from "../../shared/types/domain";

const OPTIONS: { value: BoatClass; icon: string; label: string }[] = [
  { value: "frp_country_craft", icon: "\u{1F6F6}", label: "Small boat" },
  { value: "mechanised_12_20m", icon: "\u{1F6A4}", label: "Medium boat" },
  { value: "deep_sea_20m_plus", icon: "\u{1F6A2}", label: "Large vessel" },
];

/**
 * Boat class changes the actual safety thresholds used (risk/thresholds.py)
 * — a wave height that's a NO-GO for a country craft can be a mere caution
 * for a deep-sea vessel. Without this control every user silently got the
 * smallest boat's thresholds regardless of what they actually operate,
 * which is either overly conservative or actively unsafe depending which
 * way the mismatch goes. Persisted locally so a fisherman sets it once.
 */
export function BoatClassSelector({ value, onChange }: { value: BoatClass; onChange: (v: BoatClass) => void }) {
  const { t } = useLocale();
  return (
    <div role="radiogroup" aria-label={t("boatClassLabel")} style={{ display: "flex", gap: "var(--space-2)", flexWrap: "wrap" }}>
      {OPTIONS.map((opt) => {
        const selected = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            role="radio"
            aria-checked={selected}
            onClick={() => onChange(opt.value)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              minHeight: "var(--touch-target)",
              padding: "0 14px",
              borderRadius: "var(--radius-md)",
              border: selected ? "2px solid var(--color-accent)" : "1px solid var(--color-border)",
              background: selected ? "var(--color-surface-raised)" : "var(--color-surface)",
              color: "var(--color-text)",
              fontWeight: selected ? 700 : 400,
            }}
          >
            <span aria-hidden style={{ fontSize: 18 }}>
              {opt.icon}
            </span>
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}

const STORAGE_KEY = "dhruva.boatClass";

export function loadSavedBoatClass(): BoatClass {
  try {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    if (saved === "frp_country_craft" || saved === "mechanised_12_20m" || saved === "deep_sea_20m_plus") return saved;
  } catch {
    // localStorage unavailable — fall through to the default.
  }
  return "frp_country_craft";
}

export function saveBoatClass(value: BoatClass): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, value);
  } catch {
    // best-effort persistence only
  }
}
