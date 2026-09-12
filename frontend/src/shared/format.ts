/**
 * Data-age formatting. IMPLEMENTATION.md: "data age visible on every screen"
 * is a binding constraint, not a nice-to-have — every surface that shows a
 * number derived from an Observation routes its timestamp through this so
 * "how old is this" always reads the same way.
 */
export function ageLabel(iso: string, now: Date = new Date()): string {
  const ageMs = now.getTime() - new Date(iso).getTime();
  const ageMin = Math.max(0, Math.round(ageMs / 60_000));
  if (ageMin < 1) return "just now";
  if (ageMin < 60) return `${ageMin} min ago`;
  const hours = Math.floor(ageMin / 60);
  const mins = ageMin % 60;
  if (hours < 24) return mins > 0 ? `${hours}h ${mins}m ago` : `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function ageSeconds(iso: string, now: Date = new Date()): number {
  return Math.max(0, Math.round((now.getTime() - new Date(iso).getTime()) / 1000));
}

/** Formats an already-known age in seconds (e.g. `RiskVerdict.dataAgeSeconds`,
 * a value fixed at computation time) without re-deriving it from the current
 * clock — keeps components that just need to display a stored duration pure. */
export function formatAgeSeconds(totalSeconds: number): string {
  const minutes = Math.round(totalSeconds / 60);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
}

import type { Observation } from "./types/domain";

/** Mirrors backend/dhruva/sources/base.py::Observation.offset_km exactly —
 * how far the cell that actually answered sits from the point requested. */
export function observationOffsetKm(obs: Observation): number {
  const meanLat = ((obs.cellLat + obs.requestedLat) / 2) * (Math.PI / 180);
  const dy = (obs.cellLat - obs.requestedLat) * 111.32;
  const dx = (obs.cellLon - obs.requestedLon) * 111.32 * Math.cos(meanLat);
  return Math.hypot(dx, dy);
}

export function formatCoord(lat: number, lon: number): string {
  const latLabel = `${Math.abs(lat).toFixed(4)}°${lat >= 0 ? "N" : "S"}`;
  const lonLabel = `${Math.abs(lon).toFixed(4)}°${lon >= 0 ? "E" : "W"}`;
  return `${latLabel}, ${lonLabel}`;
}
