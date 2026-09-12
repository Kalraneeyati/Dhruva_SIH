/**
 * Mock fixtures for all 8 official PS26176 query types plus a demo fleet.
 *
 * This is the ONLY file that needs deleting once the real Phase 3/4 backend
 * ships a /query endpoint — client.ts already branches on
 * `import.meta.env.VITE_API_BASE_URL` being set, so wiring the real backend
 * is: set that env var, delete the mock branch in client.ts. Every component
 * in boat/, shore/ and study/ consumes `AdvisoryResponse` etc. from
 * shared/types/domain.ts, never this file directly.
 *
 * Figures here are illustrative demo values, not live readings — every
 * Observation still carries a dataset id and a timestamp because the UI
 * components are written to require that field, and the whole point of the
 * demo is to show the UI can't render a number that skips provenance.
 */
import type {
  AdvisoryResponse,
  BoundaryDistance,
  Conditions,
  FleetVessel,
  Observation,
  PfzRecord,
  QueryIntent,
  QueryTrace,
  RiskVerdict,
  Capsule,
} from "../types/domain";

const KOCHI = { lat: 9.9658, lon: 76.2367 };

function minutesAgoIso(minutes: number): string {
  return new Date(Date.now() - minutes * 60_000).toISOString();
}

let obsSeq = 0;
function observation(partial: Partial<Observation> & Pick<Observation, "variable" | "value" | "unit" | "datasetId">): Observation {
  obsSeq += 1;
  return {
    upstreamDatasetId: partial.datasetId,
    validTime: minutesAgoIso(20),
    cellLat: KOCHI.lat + 0.01 * (obsSeq % 3),
    cellLon: KOCHI.lon + 0.01 * (obsSeq % 2),
    requestedLat: KOCHI.lat,
    requestedLon: KOCHI.lon,
    gridResolutionDeg: 0.083,
    isForecast: true,
    fetchedAt: minutesAgoIso(5),
    ...partial,
  };
}

function baseConditions(overrides: Partial<Record<string, Observation>> = {}): Conditions {
  const primary: Conditions["primary"] = {
    wave_height: observation({ variable: "wave_height", value: 1.5, unit: "m", datasetId: "open_meteo_marine" }),
    wave_period: observation({ variable: "wave_period", value: 6.2, unit: "s", datasetId: "open_meteo_marine" }),
    wind_speed: observation({ variable: "wind_speed", value: 18, unit: "kt", datasetId: "open_meteo_forecast" }),
    wind_direction: observation({ variable: "wind_direction", value: 245, unit: "degree", datasetId: "open_meteo_forecast" }),
    current_speed: observation({ variable: "current_speed", value: 0.6, unit: "kt", datasetId: "copernicus_phy_hourly" }),
    current_direction: observation({ variable: "current_direction", value: 190, unit: "degree", datasetId: "copernicus_phy_hourly" }),
    sst: observation({ variable: "sst", value: 29.1, unit: "degC", datasetId: "copernicus_phy_hourly" }),
    chlorophyll: observation({ variable: "chlorophyll", value: 0.42, unit: "mg m-3", datasetId: "copernicus_bgc_pft" }),
    ...overrides,
  };
  return {
    requestedLat: KOCHI.lat,
    requestedLon: KOCHI.lon,
    when: minutesAgoIso(0),
    primary,
    crossChecks: [
      observation({ variable: "wave_height", value: 1.6, unit: "m", datasetId: "copernicus_wav", isForecast: true }),
    ],
    errors: [],
    elapsedMs: 842,
    notice: "Advisory only. Follow official INCOIS and IMD warnings.",
    datasetsUsed: ["open_meteo_marine", "open_meteo_forecast", "copernicus_phy_hourly", "copernicus_bgc_pft", "copernicus_wav"],
    missing: [],
    disagreements: [],
  };
}

function trace(...agents: string[]): QueryTrace[] {
  let cursor = 0;
  return agents.map((agent) => {
    const startedAt = minutesAgoIso(2 - cursor * 0.1);
    cursor += 1;
    const finishedAt = minutesAgoIso(2 - cursor * 0.1);
    return { agent, startedAt, finishedAt, ok: true, summary: `${agent} completed` };
  });
}

function safeVerdict(): RiskVerdict {
  return {
    riskClass: "caution",
    boatClass: "frp_country_craft",
    overrideActive: false,
    overrideReason: null,
    computedAt: minutesAgoIso(2),
    dataAgeSeconds: 20 * 60,
    advisoryNotice: "Advisory only. Follow official INCOIS and IMD warnings.",
    factors: [
      {
        hazard: "wave",
        ruleId: "wave_hs_caution_frp",
        severity: "caution",
        narrative: "Wave height 1.5 m is below the 2.0 m country-craft caution line, but combined with wind it adds risk.",
        evidence: [
          { key: "wave_height", value: 1.5, unit: "m", datasetId: "open_meteo_marine", cellLat: KOCHI.lat, cellLon: KOCHI.lon, validTime: minutesAgoIso(20), threshold: 2.0, ruleId: "wave_hs_caution_frp" },
        ],
      },
      {
        hazard: "wind",
        ruleId: "wind_kt_caution_frp",
        severity: "caution",
        narrative: "Wind 18 kt approaches the 20 kt country-craft caution threshold.",
        evidence: [
          { key: "wind_speed", value: 18, unit: "kt", datasetId: "open_meteo_forecast", cellLat: KOCHI.lat, cellLon: KOCHI.lon, validTime: minutesAgoIso(20), threshold: 20, ruleId: "wind_kt_caution_frp" },
        ],
      },
    ],
  };
}

function demoCapsule(): Capsule {
  return {
    msgType: "advisory",
    schemaVer: 1,
    issueSlot: 300,
    validHours: 6,
    zoneId: 0,
    latOffset: 0,
    lonOffset: 0,
    riskClass: "caution",
    hazardFlags: ["wave", "wind"],
    waveHs: 1.5,
    windKt: 18,
    windDir16: 11,
    currKt: 0.6,
    currDir16: 8,
    sstC: 29.1,
    chlClass: "moderate",
    pfzBearing16: 5,
    pfzDistNm: 12,
    pfzConfidence: 2,
    bndDistNm: 21,
    bndType: "imbl",
    bndEtaMin: 96,
    reasonCode: 1,
    evidenceHash: "b7e2a1",
  };
}

const PFZ_FIXTURE: PfzRecord[] = [
  {
    landingCentre: "Munambam",
    sourceUrl: "https://incois.gov.in/MarineFisheries/TextDataHome",
    issuedFor: new Date().toISOString().slice(0, 10),
    bearingDeg: 255,
    distanceNm: 12,
    depthM: 45,
    lat: 10.05,
    lon: 76.05,
    region: "Kerala",
    confidence: "official",
  },
];

const BOUNDARY_FIXTURE: BoundaryDistance[] = [
  {
    name: "India–Sri Lanka IMBL",
    lineType: "imbl",
    territory1: "India",
    territory2: "Sri Lanka",
    distanceM: 39_000,
    distanceNm: 21.1,
    indicative: true,
    sourceUrl: "https://marineregions.org",
  },
];

function make(intent: QueryIntent, queryText: string, narrative: string, opts: Partial<AdvisoryResponse> = {}): AdvisoryResponse {
  return {
    queryText,
    detectedLanguage: "en",
    intent,
    narrative,
    verdict: null,
    conditions: null,
    pfz: [],
    boundaries: [],
    route: null,
    capsule: null,
    trace: trace("planner", "discovery", "reporting"),
    firewallRetried: false,
    firewallFellBackToTemplate: false,
    ...opts,
  };
}

export const MOCK_ADVISORIES: Record<QueryIntent, AdvisoryResponse> = {
  nearest_pfz: make(
    "nearest_pfz",
    "Where is the nearest Potential Fishing Zone (PFZ) today?",
    "The nearest advised PFZ is 12 nm WSW of Munambam landing centre, depth around 45 m, per today's INCOIS bulletin.",
    { pfz: PFZ_FIXTURE, conditions: baseConditions(), trace: trace("planner", "marine_data_discovery", "geospatial_reasoning", "reporting") },
  ),
  safe_to_venture: make(
    "safe_to_venture",
    "Is it safe to venture into the sea tomorrow morning?",
    "Caution: wave height 1.5 m and wind 18 kt are both approaching the country-craft caution line. No absolute override is active.",
    { verdict: safeVerdict(), conditions: baseConditions(), capsule: demoCapsule(), trace: trace("planner", "weather_intelligence", "ocean_analytics", "risk_assessment", "reporting") },
  ),
  conditions_at_location: make(
    "conditions_at_location",
    "What are the tide, weather, and sea conditions near my fishing location?",
    "Near Kochi: wave 1.5 m (8 s period), wind 18 kt from WSW, current 0.6 kt, SST 29.1°C, chlorophyll 0.42 mg/m3.",
    { conditions: baseConditions(), trace: trace("planner", "marine_data_discovery", "weather_intelligence", "ocean_analytics", "reporting") },
  ),
  hazard_alerts: make(
    "hazard_alerts",
    "Are there any lightning or cyclone alerts in my area?",
    "No active cyclone or lightning bulletin for this zone. This is a derived severe-weather indicator, not an official IMD cyclone bulletin.",
    { conditions: baseConditions(), trace: trace("planner", "weather_intelligence", "risk_assessment", "reporting") },
  ),
  chlorophyll_sst_zones: make(
    "chlorophyll_sst_zones",
    "Which regions show high chlorophyll concentration and favourable sea surface temperature?",
    "Chlorophyll is moderate (0.42 mg/m3) with SST 29.1°C near Kochi — within the favourable band for pelagic aggregation.",
    { conditions: baseConditions(), trace: trace("planner", "ocean_analytics", "geospatial_reasoning", "reporting") },
  ),
  safe_route: make(
    "safe_route",
    "What is the safest route for a fishing vessel considering weather and sea-state conditions?",
    "Route computed avoiding cells with wave height above 2.0 m; total distance 18.4 nm, ETA 2h10m at 9 kt.",
    {
      conditions: baseConditions(),
      route: [
        { lat: 9.9658, lon: 76.2367 },
        { lat: 9.99, lon: 76.18 },
        { lat: 10.03, lon: 76.1 },
        { lat: 10.05, lon: 76.05 },
      ],
      trace: trace("planner", "weather_intelligence", "geospatial_reasoning", "risk_assessment", "reporting"),
    },
  ),
  productivity_decline: make(
    "productivity_decline",
    "Why has fish productivity declined in a particular coastal region?",
    "Chlorophyll near this zone has fallen ~28% over the last 6 weeks (0.58 -> 0.42 mg/m3) while SST rose 1.3°C above the seasonal baseline — consistent with reduced upwelling, not confirmed causally.",
    { conditions: baseConditions(), trace: trace("planner", "ocean_analytics", "geospatial_reasoning", "reporting") },
  ),
  geofence_avoidance: make(
    "geofence_avoidance",
    "Which fishing zones should be avoided due to hazardous marine conditions or geofencing restrictions?",
    "Avoid the zone within 21 nm of the indicative India–Sri Lanka IMBL, and any cell flagged for wave height above 2.0 m.",
    { boundaries: BOUNDARY_FIXTURE, conditions: baseConditions(), trace: trace("planner", "geospatial_reasoning", "risk_assessment", "reporting") },
  ),
};

export const EXAMPLE_QUERIES: { intent: QueryIntent; text: string }[] = (
  Object.keys(MOCK_ADVISORIES) as QueryIntent[]
).map((intent) => ({ intent, text: MOCK_ADVISORIES[intent].queryText }));

export function mockAnswer(intent: QueryIntent): AdvisoryResponse {
  return MOCK_ADVISORIES[intent];
}

export function mockAnswerForText(text: string): AdvisoryResponse {
  const lower = text.toLowerCase();
  const hit = EXAMPLE_QUERIES.find((q) => lower.includes(q.text.slice(0, 12).toLowerCase()));
  return hit ? MOCK_ADVISORIES[hit.intent] : MOCK_ADVISORIES.conditions_at_location;
}

// ------------------------------------------------------------------ fleet ----
// ------------------------------------------------------------- time series ----
// Backs the Study surface's Anomaly Explorer and Heatwave View. Consistent
// with the productivity_decline narrative above: chlorophyll -28% over 6
// weeks, SST anomaly warming toward +1.3C.
const WEEK_LABELS = ["W-6", "W-5", "W-4", "W-3", "W-2", "W-1", "Now"];

export const MOCK_CHLOROPHYLL_SERIES = WEEK_LABELS.map((label, i) => ({
  label,
  value: 0.58 - (0.58 - 0.42) * (i / (WEEK_LABELS.length - 1)),
}));

export const MOCK_SST_SERIES = WEEK_LABELS.map((label, i) => ({
  label,
  value: 27.8 + 1.3 * (i / (WEEK_LABELS.length - 1)),
}));

export const MOCK_SST_ANOMALY_SERIES = WEEK_LABELS.map((label, i) => ({
  label,
  anomaly: -0.3 + 1.6 * (i / (WEEK_LABELS.length - 1)),
}));

export const MOCK_FLEET: FleetVessel[] = [
  {
    vesselId: "IND-KL-0231",
    name: "Matsya Rani",
    boatClass: "mechanised_12_20m",
    status: "underway",
    position: { vesselId: "IND-KL-0231", lat: 9.97, lon: 76.05, headingDeg: 250, speedKt: 8, observedAt: minutesAgoIso(3) },
    verdict: safeVerdict(),
    lastCapsuleAt: minutesAgoIso(12),
  },
  {
    vesselId: "IND-KL-0198",
    name: "Samudra Jyothi",
    boatClass: "frp_country_craft",
    status: "breach_warning",
    position: { vesselId: "IND-KL-0198", lat: 9.6, lon: 79.6, headingDeg: 90, speedKt: 5, observedAt: minutesAgoIso(1) },
    verdict: { ...safeVerdict(), riskClass: "no_go", overrideActive: true, overrideReason: "Within 24 nm of indicative IMBL, closing" },
    lastCapsuleAt: minutesAgoIso(4),
  },
  {
    vesselId: "IND-KL-0304",
    name: "Kadal Veeran",
    boatClass: "deep_sea_20m_plus",
    status: "at_port",
    position: { vesselId: "IND-KL-0304", lat: 9.966, lon: 76.237, headingDeg: null, speedKt: 0, observedAt: minutesAgoIso(120) },
    verdict: null,
    lastCapsuleAt: minutesAgoIso(180),
  },
  {
    vesselId: "IND-KL-0117",
    name: "Theeram",
    boatClass: "mechanised_12_20m",
    status: "no_report",
    position: null,
    verdict: null,
    lastCapsuleAt: minutesAgoIso(600),
  },
];
