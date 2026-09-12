/**
 * Enum value orderings for the capsule codec. The array index IS the raw wire
 * value, so these arrays must never be reordered once a capsule has shipped —
 * doing so silently reinterprets every capsule already issued.
 */
import type { BoatClass, HazardFlag, RiskClass } from "../types/domain";

export type { BoatClass, HazardFlag, RiskClass };

export type MsgType = "advisory" | "alert" | "all_clear" | "test";
export const MSG_TYPE_VALUES: readonly MsgType[] = ["advisory", "alert", "all_clear", "test"];

// CLAUDE.md: 0=safe, 1=caution, 2=no-go, 3=unknown.
export const RISK_CLASS_VALUES: readonly RiskClass[] = ["safe", "caution", "no_go", "unknown"];

export type ChlClassName = "low" | "moderate" | "high" | "very_high";
export const CHL_CLASS_VALUES: readonly ChlClassName[] = ["low", "moderate", "high", "very_high"];

export type ZoneBoundaryType = "none" | "imbl" | "mpa" | "closed";
export const ZONE_BOUNDARY_VALUES: readonly ZoneBoundaryType[] = ["none", "imbl", "mpa", "closed"];
