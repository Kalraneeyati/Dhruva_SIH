import { AnomalyExplorer } from "./components/AnomalyExplorer";
import { HeatwaveView } from "./components/HeatwaveView";
import { TraceInspector } from "./components/TraceInspector";

export function StudyRoutes() {
  return (
    <div style={{ maxWidth: 720, margin: "0 auto", padding: "var(--space-4)", display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
      <AnomalyExplorer />
      <HeatwaveView />
      <TraceInspector />
    </div>
  );
}
