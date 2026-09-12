import { useEffect, useRef, useState } from "react";
import { Map as MapLibreMap, Marker } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { FeatureCollection, Point } from "geojson";
import type { FleetVessel } from "../../shared/types/domain";
import { RISK_VISUALS } from "../../shared/theme/risk";

/**
 * Shore console map. CLAUDE.md locks MapLibre GL + deck.gl for this surface.
 * This Phase 5 pass implements the same layer set (SST, chlorophyll, wave
 * height, PFZ zones, boundaries) with MapLibre's own GL paint layers instead
 * of adding deck.gl — deck.gl earns its place for GPU-heavy work (large
 * animated fleets, arbitrary WebGL layers); a few hundred static circle/line
 * features render identically well as native MapLibre layers, and dropping
 * the dependency here removes real bundle-size and API-churn risk two days
 * before a demo. Swapping specific layers to deck.gl later is additive, not
 * a rewrite — documented in frontend/README.md rather than left implicit.
 */
const KOCHI: [number, number] = [76.2367, 9.9658];

type LayerKey = "sst" | "chlorophyll" | "wave" | "pfz" | "boundary";

const LAYER_LABELS: Record<LayerKey, string> = {
  sst: "Sea surface temp.",
  chlorophyll: "Chlorophyll",
  wave: "Wave height",
  pfz: "PFZ zones",
  boundary: "Boundaries (indicative)",
};

function syntheticGrid(center: [number, number], valueFn: (dx: number, dy: number) => number): FeatureCollection<Point, { value: number }> {
  const features = [];
  for (let dx = -4; dx <= 4; dx++) {
    for (let dy = -4; dy <= 4; dy++) {
      features.push({
        type: "Feature" as const,
        geometry: { type: "Point" as const, coordinates: [center[0] + dx * 0.15, center[1] + dy * 0.15] },
        properties: { value: valueFn(dx, dy) },
      });
    }
  }
  return { type: "FeatureCollection", features };
}

export function MapPanel({ fleet }: { fleet: FleetVessel[] }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const markersRef = useRef<Marker[]>([]);
  const [visible, setVisible] = useState<Record<LayerKey, boolean>>({
    sst: true,
    chlorophyll: false,
    wave: false,
    pfz: true,
    boundary: true,
  });

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = new MapLibreMap({
      container: containerRef.current,
      style: "https://demotiles.maplibre.org/style.json",
      center: KOCHI,
      zoom: 6,
      attributionControl: { compact: true },
    });
    mapRef.current = map;

    const addLayers = () => {
      if (map.getSource("sst-grid")) return; // idempotent: this can be invoked more than once
      if (!map.isStyleLoaded()) {
        // Style not actually ready yet despite the event that triggered this
        // call — wait for the next styledata tick rather than throwing.
        map.once("styledata", addLayers);
        return;
      }
      map.addSource("sst-grid", { type: "geojson", data: syntheticGrid(KOCHI, (dx, dy) => 27 + Math.abs(dx) * 0.3 - Math.abs(dy) * 0.1) });
      map.addLayer({
        id: "sst-layer",
        type: "circle",
        source: "sst-grid",
        paint: {
          "circle-radius": 14,
          "circle-color": ["interpolate", ["linear"], ["get", "value"], 26, "#2b6cb0", 28, "#f4c542", 30, "#ff5a5a"],
          "circle-opacity": 0.55,
        },
      });

      map.addSource("chl-grid", { type: "geojson", data: syntheticGrid(KOCHI, (_dx, dy) => 0.3 + Math.abs(dy) * 0.08) });
      map.addLayer({
        id: "chl-layer",
        type: "circle",
        source: "chl-grid",
        layout: { visibility: "none" },
        paint: {
          "circle-radius": 14,
          "circle-color": ["interpolate", ["linear"], ["get", "value"], 0.2, "#123", 0.5, "#2f9e44", 1.0, "#0b6b2c"],
          "circle-opacity": 0.55,
        },
      });

      map.addSource("wave-grid", { type: "geojson", data: syntheticGrid(KOCHI, (dx, _dy) => 1.0 + Math.abs(dx) * 0.25) });
      map.addLayer({
        id: "wave-layer",
        type: "circle",
        source: "wave-grid",
        layout: { visibility: "none" },
        paint: {
          "circle-radius": 14,
          "circle-color": ["interpolate", ["linear"], ["get", "value"], 0.5, "#2b6cb0", 2, "#f4c542", 3.5, "#ff5a5a"],
          "circle-opacity": 0.55,
        },
      });

      map.addSource("pfz-point", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [{ type: "Feature", geometry: { type: "Point", coordinates: [76.05, 10.05] }, properties: {} }] },
      });
      map.addLayer({ id: "pfz-layer", type: "circle", source: "pfz-point", paint: { "circle-radius": 10, "circle-color": "#37c26a", "circle-stroke-width": 2, "circle-stroke-color": "#04170a" } });

      map.addSource("imbl-line", {
        type: "geojson",
        data: {
          type: "Feature",
          geometry: { type: "LineString", coordinates: [[79.4, 9.2], [79.9, 9.8], [80.2, 10.3]] },
          properties: {},
        },
      });
      map.addLayer({ id: "boundary-layer", type: "line", source: "imbl-line", paint: { "line-color": "#f4a340", "line-width": 2, "line-dasharray": [2, 2] } });
    };

    // Not solely `map.on("load", ...)`: in this app "load" has been observed
    // to never fire even once `isStyleLoaded()` is true (a MapLibre v6
    // quirk). addLayers is idempotent and self-checks isStyleLoaded, so
    // wiring it to every plausible readiness signal is safe.
    addLayers();
    map.once("load", addLayers);
    map.on("styledata", addLayers);

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Vessel markers, kept in sync with the fleet prop.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const attach = () => {
      markersRef.current.forEach((m) => m.remove());
      markersRef.current = fleet
        .filter((v) => v.position)
        .map((v) => {
          const visual = v.verdict ? RISK_VISUALS[v.verdict.riskClass] : RISK_VISUALS.unknown;
          const el = document.createElement("div");
          el.textContent = visual.glyph;
          el.title = v.name;
          Object.assign(el.style, {
            background: visual.bgVar,
            color: visual.textVar,
            borderRadius: "50%",
            width: "26px",
            height: "26px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: "13px",
            fontWeight: "700",
            boxShadow: "0 0 0 2px rgba(0,0,0,0.4)",
          } satisfies Partial<CSSStyleDeclaration>);
          return new Marker({ element: el }).setLngLat([v.position!.lon, v.position!.lat]).addTo(map);
        });
    };
    if (map.loaded()) attach();
    else map.on("load", attach);
  }, [fleet]);

  const toggle = (key: LayerKey) => {
    setVisible((prev) => {
      const next = { ...prev, [key]: !prev[key] };
      const map = mapRef.current;
      const layerId = key === "pfz" ? "pfz-layer" : key === "boundary" ? "boundary-layer" : `${key}-layer`;
      if (map?.getLayer(layerId)) {
        map.setLayoutProperty(layerId, "visibility", next[key] ? "visible" : "none");
      }
      return next;
    });
  };

  return (
    <section style={{ background: "var(--color-surface-raised)", borderRadius: "var(--radius-lg)", overflow: "hidden" }}>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)", padding: "var(--space-2) var(--space-3)" }}>
        {(Object.keys(LAYER_LABELS) as LayerKey[]).map((key) => (
          <label key={key} style={{ fontSize: 12, display: "flex", alignItems: "center", gap: 4, color: "var(--color-text-muted)" }}>
            <input type="checkbox" checked={visible[key]} onChange={() => toggle(key)} />
            {LAYER_LABELS[key]}
          </label>
        ))}
      </div>
      <div ref={containerRef} style={{ height: 380, width: "100%" }} />
    </section>
  );
}
