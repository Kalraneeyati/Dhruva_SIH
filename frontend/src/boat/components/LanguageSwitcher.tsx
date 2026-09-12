import { useLocale } from "../../shared/hooks/useLocale";
import { UI_LOCALES } from "../../shared/i18n/strings";

export function LanguageSwitcher() {
  const { locale, setLocale, t } = useLocale();
  return (
    <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--color-text-muted)" }}>
      <span className="sr-only-inline">{t("languageLabel")}</span>
      <select
        aria-label={t("languageLabel")}
        value={locale}
        onChange={(e) => setLocale(e.target.value as (typeof UI_LOCALES)[number]["code"])}
        style={{
          background: "var(--color-surface-raised)",
          color: "var(--color-text)",
          border: "1px solid var(--color-border)",
          borderRadius: "var(--radius-sm)",
          padding: "6px 10px",
          minHeight: 40,
        }}
      >
        {UI_LOCALES.map((l) => (
          <option key={l.code} value={l.code}>
            {l.nativeLabel}
          </option>
        ))}
      </select>
    </label>
  );
}
