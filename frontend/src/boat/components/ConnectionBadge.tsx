import { useOnlineStatus } from "../../shared/hooks/useOnlineStatus";
import { useLocale } from "../../shared/hooks/useLocale";

export function ConnectionBadge() {
  const online = useOnlineStatus();
  const { t } = useLocale();
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        fontSize: 12,
        padding: "4px 10px",
        borderRadius: 999,
        background: online ? "var(--color-safe)" : "var(--color-caution)",
        color: online ? "var(--color-safe-text)" : "var(--color-caution-text)",
      }}
    >
      <span aria-hidden style={{ width: 7, height: 7, borderRadius: "50%", background: "currentColor" }} />
      {online ? t("connectionOnline") : t("connectionOffline")}
    </span>
  );
}
