/**
 * Shared domain contract — Phase 5 frontend.
 *
 * These types mirror the Pydantic models already locked in the Phase 0-2 backend
 * (backend/dhruva/sources/base.py, sources/registry.py) field-for-field, plus the
 * Verdict/EvidenceBundle/Capsule shapes CLAUDE.md and IMPLEMENTATION.md commit the
 * Phase 3/4 backend to. Nothing here is invented independently of those documents:
 * where the backend has not been written yet (risk/, evidence/, codec/, graph/),
 * the shape below IS the spec those modules must satisfy, transcribed from
 * IMPLEMENTATION.md section 3.2/3.3 and CLAUDE.md's capsule field table.
 *
 * When Phase 3/4 land, `shared/api/client.ts` is the only file that needs to
 * change — every component here consumes these types, never a raw fetch response.
 */

// ---------------------------------------------------------------- registry ----
// Mirrors backend/dhruva/sources/registry.py::Variable exactly (same string values,
// so a capsule/evidence payload round-trips through both languages unchanged).
export type Variable =
  | "wave_height"
  | "wave_period"
  | "wave_direction"
  | "wind_speed"
  | "wind_direction"
  | "current_speed"
  | "current_direction"
  | "sst"
  | "chlorophyll";

export type SourceKind = "erddap" | "copernicus" | "open_meteo" | "scrape";

// ----------------------------------------------------------------- sources ----
// Mirrors backend/dhruva/sources/base.py::Observation. A number with no
// provenance cannot exist in this type — every numeric field sits next to the
// fields that defend it. UI components must not accept a bare `number` for
// anything a user can see; they accept an Observation.
export interface Observation {
  variable: Variable;
  value: number;
  unit: string;
  datasetId: string;
  upstreamDatasetId: string;
  validTime: string; // ISO 8601 UTC — the instant the value describes
  cellLat: number;
  cellLon: number;
  requestedLat: number;
  requestedLon: number;
  gridResolutionDeg: number;
  isForecast: boolean;
  fetchedAt: string; // ISO 8601 UTC
}

export interface FetchError {
  datasetId: string;
  variable: Variable | null;
  error: string;
}

export interface Disagreement {
  variable: Variable;
  primary: Observation;
  other: Observation;
  delta: number;
  tolerance: number;
}

// Mirrors backend/dhruva/sources/conditions.py::Conditions.
export interface Conditions {
  requestedLat: number;
  requestedLon: number;
  when: string;
  primary: Partial<Record<Variable, Observation>>;
  crossChecks: Observation[];
  errors: FetchError[];
  elapsedMs: number;
  notice: string;
  datasetsUsed: string[];
  missing: Variable[];
  disagreements: Disagreement[];
}

// -------------------------------------------------------------- boundaries ----
// Mirrors backend/dhruva/geo/boundaries.py::BoundaryDistance. `indicative` is
// non-optional and always true — CLAUDE.md: "Boundaries are indicative, never
// legal." No component may render a boundary line without this flag visible.
export interface BoundaryDistance {
  name: string;
  lineType: string;
  territory1: string | null;
  territory2: string | null;
  distanceM: number;
  distanceNm: number;
  indicative: true;
  sourceUrl: string | null;
}

export type ZoneType =
  | "internal_waters"
  | "territorial_sea_12nm"
  | "contiguous_24nm"
  | "eez"
  | "mpa"
  | "closed";

export interface MaritimeZone {
  name: string;
  zoneType: ZoneType;
  territory: string | null;
  sovereign: string | null;
  indicative: true;
  sourceUrl: string | null;
}

// -------------------------------------------------------------------- pfz ----
// Mirrors backend/dhruva/sources/pfz_scraper.py::PfzRecord. sourceUrl is
// required at the type level, matching the backend's `pfz_attribution_present`
// CHECK constraint — this must be impossible to construct without attribution.
export interface PfzRecord {
  landingCentre: string;
  sourceUrl: string;
  issuedFor: string; // date, ISO 8601
  bearingDeg: number | null;
  distanceNm: number | null;
  depthM: number | null;
  lat: number | null;
  lon: number | null;
  region: string | null;
  confidence: PfzConfidence;
}

export type PfzConfidence = "official" | "stale" | "unavailable";

// ------------------------------------------------------- risk / evidence -----
// IMPLEMENTATION.md 3.2 — risk_class values, in the capsule's own encoding order.
export type RiskClass = "safe" | "caution" | "no_go" | "unknown";

// CLAUDE.md capsule field table, offset 59 width 8: bitmap order fixed here so
// the frontend and the eventual codec never disagree on which bit means what.
export type HazardFlag =
  | "wave"
  | "wind"
  | "squall"
  | "lightning"
  | "cyclone"
  | "current"
  | "fog"
  | "tsunami";

export type BoatClass = "frp_country_craft" | "mechanised_12_20m" | "deep_sea_20m_plus";

// One line of the risk narrative: a rule that fired, and the evidence it fired
// on. This is what a "why" answer (query #7 style) is built out of, and what
// the numeric firewall (IMPLEMENTATION.md 3.3) validates narration against.
export interface EvidenceBundleEntry {
  key: string;
  value: number;
  unit: string;
  datasetId: string;
  cellLat: number;
  cellLon: number;
  validTime: string;
  threshold?: number;
  ruleId?: string;
}

export interface RiskFactor {
  hazard: HazardFlag;
  ruleId: string;
  severity: RiskClass;
  narrative: string; // template-rendered, every number in it traces to `evidence`
  evidence: EvidenceBundleEntry[];
}

// The verdict a boat crew acts on. `overrideActive` is set when an absolute
// override fired (cyclone within 300km / lightning within 50km / tsunami) —
// CLAUDE.md: "NO-GO outranks everything. A favourable fishing zone never
// renders above an active hazard." The boat UI must check this before it ever
// renders a PFZ row above the verdict card.
export interface RiskVerdict {
  riskClass: RiskClass;
  boatClass: BoatClass;
  factors: RiskFactor[];
  overrideActive: boolean;
  overrideReason: string | null;
  computedAt: string;
  dataAgeSeconds: number; // freshest contributing observation's age — always shown
  advisoryNotice: string; // "Advisory only. Follow official INCOIS and IMD warnings."
}

// ---------------------------------------------------------------- capsule ----
// CLAUDE.md capsule field table — 145 bits total, 75 free inside a 220-bit
// NavIC segment. This is the decoded/pre-encode shape; shared/capsule/codec.ts
// is the only place that touches bit offsets.
export interface Capsule {
  msgType: "advisory" | "alert" | "all_clear" | "test";
  schemaVer: number;
  issueSlot: number; // 15-min slot, 0-671, 7-day wrap
  validHours: number; // 0-15
  zoneId: number; // lat_idx * 560 + lon_idx, bbox 6-24N/66-94E, 0.05deg step
  latOffset: number; // 0-255, position within cell
  lonOffset: number;
  riskClass: RiskClass;
  hazardFlags: HazardFlag[];
  waveHs: number; // metres, quantised to 0.25, saturating at 7.75
  windKt: number; // 0-63, saturating
  windDir16: number; // 16-point compass index
  currKt: number; // 0-3.1, quantised to 0.1
  currDir16: number;
  sstC: number; // 18-33.5, quantised to 0.5
  chlClass: "low" | "moderate" | "high" | "very_high";
  pfzBearing16: number;
  pfzDistNm: number; // 0-63
  pfzConfidence: 0 | 1 | 2 | 3;
  bndDistNm: number; // 0-31
  bndType: "none" | "imbl" | "mpa" | "closed";
  bndEtaMin: number; // 0-255, drift-projected
  reasonCode: number; // 0-255, codebook index
  evidenceHash: string; // truncated SHA-256 hex, 12 bits worth
}

// -------------------------------------------------------------------- pos ----
export interface LatLon {
  lat: number;
  lon: number;
}

// Quantised to the 0.05deg grid at rest per CLAUDE.md; tracks purge after 7
// days. The frontend never persists a vessel position longer than that either
// (see shared/offline/db.ts).
export interface VesselPosition extends LatLon {
  vesselId: string;
  headingDeg: number | null;
  speedKt: number | null;
  observedAt: string;
}

export type FleetStatus = "underway" | "at_port" | "no_report" | "breach_warning";

export interface FleetVessel {
  vesselId: string;
  name: string;
  boatClass: BoatClass;
  status: FleetStatus;
  position: VesselPosition | null;
  verdict: RiskVerdict | null;
  lastCapsuleAt: string | null;
}

// ------------------------------------------------------------------ query ----
// The 8 official PS query types (SIH26176 brief) — the acceptance test suite.
export type QueryIntent =
  | "nearest_pfz"
  | "safe_to_venture"
  | "conditions_at_location"
  | "hazard_alerts"
  | "chlorophyll_sst_zones"
  | "safe_route"
  | "productivity_decline"
  | "geofence_avoidance";

export interface QueryTrace {
  agent: string;
  startedAt: string;
  finishedAt: string;
  ok: boolean;
  summary: string;
}

export interface AdvisoryResponse {
  queryText: string;
  detectedLanguage: string;
  intent: QueryIntent;
  narrative: string; // numeric-firewall-validated prose in the response language
  verdict: RiskVerdict | null;
  conditions: Conditions | null;
  pfz: PfzRecord[];
  boundaries: BoundaryDistance[];
  route: LatLon[] | null;
  capsule: Capsule | null;
  trace: QueryTrace[]; // the agent-by-agent execution trace, shown in Study
  firewallRetried: boolean; // true if narration failed validation once and was retried
  firewallFellBackToTemplate: boolean; // true if it failed twice and was templated
}
