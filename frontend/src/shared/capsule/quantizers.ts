/**
 * Physical-unit <-> raw-field conversions for the capsule codec.
 *
 * Every quantiser clamps rather than wraps (clampInt in bits.ts) — CLAUDE.md:
 * "Wrapping a 9m sea into a calm reading is the worst bug this project can
 * ship." Figures are quantised to the grid stated in CLAUDE.md, not rounded
 * for display, so the online card and the offline capsule card agree on
 * screen when both are shown side by side in the demo.
 */
import { clampInt } from "./bits";
import type { BoatClass, ChlClassName, HazardFlag, MsgType, RiskClass, ZoneBoundaryType } from "./enums";
import { CHL_CLASS_VALUES, MSG_TYPE_VALUES, RISK_CLASS_VALUES, ZONE_BOUNDARY_VALUES } from "./enums";

// ------------------------------------------------------------- compass ----
// Matches backend/dhruva/sources/base.py::to_compass_16 exactly — demo values
// must sit on the same 16-point grid on both sides or the boat and shore
// cards disagree, per CLAUDE.md.
export function toCompass16(bearingDeg: number): number {
  return Math.trunc(((bearingDeg % 360) + 360) % 360 / 22.5 + 0.5) % 16;
}

export function fromCompass16(index: number): number {
  return (index % 16) * 22.5;
}

export const COMPASS_16_LABELS = [
  "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
  "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
] as const;

// --------------------------------------------------------------- zone ----
// bbox 6-24 deg N, 66-94 deg E, 0.05deg step (CLAUDE.md capsule spec).
export const ZONE_LAT_MIN = 6;
export const ZONE_LAT_MAX = 24;
export const ZONE_LON_MIN = 66;
export const ZONE_LON_MAX = 94;
export const ZONE_STEP_DEG = 0.05;
export const ZONE_LON_CELLS = Math.round((ZONE_LON_MAX - ZONE_LON_MIN) / ZONE_STEP_DEG); // 560
export const ZONE_LAT_CELLS = Math.round((ZONE_LAT_MAX - ZONE_LAT_MIN) / ZONE_STEP_DEG); // 360

export interface ZoneEncoding {
  zoneId: number;
  latOffsetRaw: number;
  lonOffsetRaw: number;
}

/** Position -> zone_id + sub-cell offsets. Points outside the bbox clamp to
 * the nearest edge cell rather than wrapping or throwing — a capsule must
 * still be constructible for a boat near the bbox edge. */
export function encodeZone(lat: number, lon: number): ZoneEncoding {
  // Cell index must FLOOR, never round — clampInt rounds, which for an index
  // silently shifts the cell and threw the sub-cell offset off by up to half
  // a cell (~1.5km at this grid). Floor first, then clamp the integer.
  const latIdx = Math.min(Math.max(Math.floor((lat - ZONE_LAT_MIN) / ZONE_STEP_DEG), 0), ZONE_LAT_CELLS - 1);
  const lonIdx = Math.min(Math.max(Math.floor((lon - ZONE_LON_MIN) / ZONE_STEP_DEG), 0), ZONE_LON_CELLS - 1);
  const cellLat = ZONE_LAT_MIN + latIdx * ZONE_STEP_DEG;
  const cellLon = ZONE_LON_MIN + lonIdx * ZONE_STEP_DEG;
  const latFrac = clampInt(((lat - cellLat) / ZONE_STEP_DEG) * 256, 0, 255);
  const lonFrac = clampInt(((lon - cellLon) / ZONE_STEP_DEG) * 256, 0, 255);
  return {
    zoneId: latIdx * ZONE_LON_CELLS + lonIdx,
    latOffsetRaw: latFrac,
    lonOffsetRaw: lonFrac,
  };
}

export function decodeZone(zoneId: number, latOffsetRaw: number, lonOffsetRaw: number): { lat: number; lon: number } {
  const latIdx = Math.floor(zoneId / ZONE_LON_CELLS);
  const lonIdx = zoneId % ZONE_LON_CELLS;
  const lat = ZONE_LAT_MIN + latIdx * ZONE_STEP_DEG + (latOffsetRaw / 256) * ZONE_STEP_DEG;
  const lon = ZONE_LON_MIN + lonIdx * ZONE_STEP_DEG + (lonOffsetRaw / 256) * ZONE_STEP_DEG;
  return { lat, lon };
}

// ------------------------------------------------------------- issue slot ----
export const SLOTS_PER_WEEK = 7 * 24 * 4; // 672, 15-minute slots

export function encodeIssueSlot(when: Date): number {
  const utcDay = Math.floor(when.getTime() / 86_400_000);
  const dayOfWeek = ((utcDay % 7) + 7) % 7;
  const minuteOfDay = when.getUTCHours() * 60 + when.getUTCMinutes();
  const slot = dayOfWeek * (24 * 4) + Math.floor(minuteOfDay / 15);
  return clampInt(slot, 0, SLOTS_PER_WEEK - 1);
}

// ---------------------------------------------------------- scalar fields ----
export const quantize = {
  waveHs: (m: number) => clampInt(m / 0.25, 0, 31),
  windKt: (kt: number) => clampInt(kt, 0, 63),
  currKt: (kt: number) => clampInt(kt / 0.1, 0, 31),
  sst: (c: number) => clampInt((c - 18) / 0.5, 0, 31),
  pfzDistNm: (nm: number) => clampInt(nm, 0, 63),
  bndDistNm: (nm: number) => clampInt(nm, 0, 31),
  bndEtaMin: (min: number) => clampInt(min, 0, 255),
} as const;

export const dequantize = {
  waveHs: (raw: number) => raw * 0.25,
  windKt: (raw: number) => raw,
  currKt: (raw: number) => raw * 0.1,
  sst: (raw: number) => raw * 0.5 + 18,
  pfzDistNm: (raw: number) => raw,
  bndDistNm: (raw: number) => raw,
  bndEtaMin: (raw: number) => raw,
} as const;

// ------------------------------------------------------------------ enums ----
export function encodeEnum<T extends string>(values: readonly T[], value: T): number {
  const idx = values.indexOf(value);
  if (idx < 0) throw new Error(`unknown enum value ${value}`);
  return idx;
}

export function decodeEnum<T extends string>(values: readonly T[], raw: number): T {
  const v = values[raw];
  if (v === undefined) throw new Error(`enum raw value ${raw} out of range`);
  return v;
}

export const msgTypeCodec = {
  encode: (v: MsgType) => encodeEnum(MSG_TYPE_VALUES, v),
  decode: (raw: number) => decodeEnum(MSG_TYPE_VALUES, raw),
};

export const riskClassCodec = {
  encode: (v: RiskClass) => encodeEnum(RISK_CLASS_VALUES, v),
  decode: (raw: number) => decodeEnum(RISK_CLASS_VALUES, raw),
};

export const chlClassCodec = {
  encode: (v: ChlClassName) => encodeEnum(CHL_CLASS_VALUES, v),
  decode: (raw: number) => decodeEnum(CHL_CLASS_VALUES, raw),
};

export const boundaryTypeCodec = {
  encode: (v: ZoneBoundaryType) => encodeEnum(ZONE_BOUNDARY_VALUES, v),
  decode: (raw: number) => decodeEnum(ZONE_BOUNDARY_VALUES, raw),
};

// -------------------------------------------------------------- hazard bitmap
// Bit order fixed per CLAUDE.md offset 59 width 8, listed order = MSB..LSB.
export const HAZARD_BIT_ORDER: readonly HazardFlag[] = [
  "wave", "wind", "squall", "lightning", "cyclone", "current", "fog", "tsunami",
];

export function encodeHazardFlags(flags: HazardFlag[]): number {
  let raw = 0;
  for (const f of flags) {
    const idx = HAZARD_BIT_ORDER.indexOf(f);
    if (idx < 0) throw new Error(`unknown hazard flag ${f}`);
    raw |= 1 << (HAZARD_BIT_ORDER.length - 1 - idx);
  }
  return raw;
}

export function decodeHazardFlags(raw: number): HazardFlag[] {
  const out: HazardFlag[] = [];
  HAZARD_BIT_ORDER.forEach((f, idx) => {
    if (raw & (1 << (HAZARD_BIT_ORDER.length - 1 - idx))) out.push(f);
  });
  return out;
}

// ------------------------------------------------------------- boat class ----
// Not itself a capsule field (the capsule is one boat's own advisory), but
// shared so the risk-threshold table (IMPLEMENTATION.md 3.2) has one place to
// look boat class up from.
export const BOAT_CLASS_VALUES: readonly BoatClass[] = [
  "frp_country_craft", "mechanised_12_20m", "deep_sea_20m_plus",
];
