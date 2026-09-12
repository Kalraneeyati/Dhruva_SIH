import { useEffect, useState } from "react";
import type { FleetVessel } from "../shared/types/domain";
import { fetchFleet, isUsingMockData } from "../shared/api/client";
import { FleetList } from "./components/FleetList";
import { BreachWatch } from "./components/BreachWatch";
import { MapPanel } from "./components/MapPanel";
import { BroadcastComposer } from "./components/BroadcastComposer";

export function ShoreConsole() {
  const [fleet, setFleet] = useState<FleetVessel[]>([]);
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    fetchFleet().then(setFleet).catch(() => setFleet([]));
  }, []);

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", padding: "var(--space-4)", display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
      {isUsingMockData() && (
        <p style={{ fontSize: 12, color: "var(--color-caution)", margin: 0 }}>
          Showing mock fleet data — set VITE_API_BASE_URL to point at the real backend.
        </p>
      )}
      <BreachWatch fleet={fleet} />
      <MapPanel fleet={fleet} />
      <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-4)" }}>
        <div style={{ flex: "1 1 320px", minWidth: 0 }}>
          <FleetList fleet={fleet} selected={selected} onSelect={setSelected} />
        </div>
        <div style={{ flex: "1 1 320px", minWidth: 0 }}>
          <BroadcastComposer />
        </div>
      </div>
    </div>
  );
}
