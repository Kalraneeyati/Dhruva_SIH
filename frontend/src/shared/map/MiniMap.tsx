import { useEffect, useRef } from "react";
import { Map as MapLibreMap, Marker, type GeoJSONSource } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { LatLon } from "../types/domain";

export interface MiniMapMarker extends LatLon {
  glyph: string;
  bg: string;
  fg: string;
  label?: string;
}

interface MiniMapProps {
  center: LatLon;
  zoom?: number;
  markers?: MiniMapMarker[];
  route?: LatLon[];
  /** A single line to draw as "indicative" (dashed amber) — the IMBL/MPA
   * distance line for whichever boundary answer is being shown. */
  boundaryLine?: LatLon[];
  height?: number;
}

/**
 * A lightweight, single-purpose MapLibre view for embedding a location
 * directly in an answer — the Boat surface's biggest visual gap before this
 * pass was that every answer was text-and-numbers even when the query was
 * inherently spatial ("nearest PFZ", "safest route", "which zones to
 * avoid"). Deliberately NOT the full layer-toggle console (see
 * shore/components/MapPanel.tsx for that) — this is the map's job when the
 * job is just "show me where."
 */
export function MiniMap({ center, zoom = 8, markers = [], route, boundaryLine, height = 240 }: MiniMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const markersRef = useRef<Marker[]>([]);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = new MapLibreMap({
      container: containerRef.current,
      style: "https://demotiles.maplibre.org/style.json",
      center: [center.lon, center.lat],
      zoom,
      attributionControl: { compact: true },
      interactive: true,
    });
    mapRef.current = map;

    const addLayers = () => {
      if (map.getSource("minimap-route") || !map.isStyleLoaded()) {
        if (!map.isStyleLoaded()) map.once("styledata", addLayers);
        return;
      }
      map.addSource("minimap-route", {
        type: "geojson",
        data: { type: "Feature", geometry: { type: "LineString", coordinates: route?.map((p) => [p.lon, p.lat]) ?? [] }, properties: {} },
      });
      map.addLayer({ id: "minimap-route-line", type: "line", source: "minimap-route", paint: { "line-color": "#37c26a", "line-width": 3 } });

      map.addSource("minimap-boundary", {
        type: "geojson",
        data: { type: "Feature", geometry: { type: "LineString", coordinates: boundaryLine?.map((p) => [p.lon, p.lat]) ?? [] }, properties: {} },
      });
      map.addLayer({ id: "minimap-boundary-line", type: "line", source: "minimap-boundary", paint: { "line-color": "#f4a340", "line-width": 2, "line-dasharray": [2, 2] } });
    };

    addLayers();
    map.once("load", addLayers);
    map.on("styledata", addLayers);

    return () => {
      map.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Keep center/zoom in sync when the answer (and thus the point) changes.
  useEffect(() => {
    mapRef.current?.jumpTo({ center: [center.lon, center.lat], zoom });
  }, [center.lat, center.lon, zoom]);

  // Update route/boundary geometry without recreating the map.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const routeSrc = map.getSource("minimap-route") as GeoJSONSource | undefined;
    routeSrc?.setData({ type: "Feature", geometry: { type: "LineString", coordinates: route?.map((p) => [p.lon, p.lat]) ?? [] }, properties: {} });
    const boundarySrc = map.getSource("minimap-boundary") as GeoJSONSource | undefined;
    boundarySrc?.setData({ type: "Feature", geometry: { type: "LineString", coordinates: boundaryLine?.map((p) => [p.lon, p.lat]) ?? [] }, properties: {} });
  }, [route, boundaryLine]);

  // Vessel/PFZ/location markers.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    markersRef.current.forEach((m) => m.remove());
    markersRef.current = markers.map((m) => {
      const el = document.createElement("div");
      el.textContent = m.glyph;
      if (m.label) el.title = m.label;
      Object.assign(el.style, {
        background: m.bg,
        color: m.fg,
        borderRadius: "50%",
        width: "26px",
        height: "26px",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: "13px",
        fontWeight: "700",
        boxShadow: "0 0 0 2px rgba(0,0,0,0.35)",
      } satisfies Partial<CSSStyleDeclaration>);
      return new Marker({ element: el }).setLngLat([m.lon, m.lat]).addTo(map);
    });
  }, [markers]);

  return <div ref={containerRef} style={{ height, width: "100%", borderRadius: "var(--radius-md)", overflow: "hidden" }} />;
}
