import { useEffect } from "react";
import type { LatLon } from "../../shared/types/domain";
import { useGeolocation } from "../../shared/hooks/useGeolocation";
import { formatCoord } from "../../shared/format";

/** Shows exactly which location a query will use and lets a fisherman
 * override the gazetteer/default with one tap on their real position —
 * plain language, no coordinate typing required. */
export function LocationControl({ onLocation }: { onLocation: (loc: LatLon) => void }) {
  const { location, status, request } = useGeolocation();

  useEffect(() => {
    if (location) onLocation(location);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location]);

  if (location) {
    return (
      <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: "var(--color-safe)" }}>
        <span aria-hidden>📍</span>
        Using your location ({formatCoord(location.lat, location.lon)})
      </div>
    );
  }

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, flexWrap: "wrap" }}>
      <button
        type="button"
        onClick={() => request()}
        style={{
          minHeight: 40,
          padding: "0 14px",
          borderRadius: "var(--radius-md)",
          border: "1px solid var(--color-border)",
          background: "var(--color-surface)",
          color: "var(--color-text)",
          display: "flex",
          alignItems: "center",
          gap: 6,
        }}
      >
        <span aria-hidden>📍</span>
        {status === "locating" ? "Finding you…" : "Use my location"}
      </button>
      {status === "denied" && (
        <span style={{ color: "var(--color-caution)" }}>Location denied — mention a place name instead (e.g. "near Kochi").</span>
      )}
      {status === "unsupported" && <span style={{ color: "var(--color-text-muted)" }}>Not supported on this browser.</span>}
      {status === "idle" && <span style={{ color: "var(--color-text-muted)" }}>Defaults to Kochi unless you name a place.</span>}
    </div>
  );
}
