import { beforeEach, describe, expect, it } from "vitest";
import { db, purgeStaleVesselTracks, recordVesselPosition, saveCapsule, recentCapsules, cacheConditions, getCachedConditions } from "./db";
import type { Capsule, Conditions, VesselPosition } from "../types/domain";

function sampleCapsule(): Capsule {
  return {
    msgType: "advisory", schemaVer: 1, issueSlot: 10, validHours: 6, zoneId: 5,
    latOffset: 0, lonOffset: 0, riskClass: "safe", hazardFlags: [], waveHs: 0.5,
    windKt: 5, windDir16: 0, currKt: 0.1, currDir16: 0, sstC: 28, chlClass: "low",
    pfzBearing16: 0, pfzDistNm: 5, pfzConfidence: 1, bndDistNm: 10, bndType: "none",
    bndEtaMin: 60, reasonCode: 0, evidenceHash: "abc",
  };
}

beforeEach(async () => {
  await db.capsules.clear();
  await db.conditions.clear();
  await db.vesselTracks.clear();
});

describe("capsule storage", () => {
  it("stores and retrieves the most recent capsules first", async () => {
    await saveCapsule("PAYLOAD1", { ...sampleCapsule(), zoneId: 1 });
    await saveCapsule("PAYLOAD2", { ...sampleCapsule(), zoneId: 2 });
    const recent = await recentCapsules();
    expect(recent).toHaveLength(2);
    expect(recent[0].capsule.zoneId).toBe(2); // most recent first
  });
});

describe("conditions cache", () => {
  it("round-trips a Conditions object by cell", async () => {
    const conditions = { requestedLat: 9.9658, requestedLon: 76.2367 } as Conditions;
    await cacheConditions(9.9658, 76.2367, conditions);
    const back = await getCachedConditions(9.9658, 76.2367);
    expect(back?.requestedLat).toBe(9.9658);
  });

  it("returns null for an uncached location", async () => {
    expect(await getCachedConditions(1, 1)).toBeNull();
  });
});

describe("vessel track retention", () => {
  it("purges tracks older than 7 days and keeps recent ones", async () => {
    const now = new Date("2026-09-12T00:00:00Z");
    const old: VesselPosition = { vesselId: "V1", lat: 9, lon: 76, headingDeg: 0, speedKt: 1, observedAt: new Date(now.getTime() - 8 * 86_400_000).toISOString() };
    const fresh: VesselPosition = { vesselId: "V1", lat: 9, lon: 76, headingDeg: 0, speedKt: 1, observedAt: new Date(now.getTime() - 1 * 86_400_000).toISOString() };
    await recordVesselPosition(old);
    await recordVesselPosition(fresh);

    const purged = await purgeStaleVesselTracks(now);
    expect(purged).toBe(1);

    const remaining = await db.vesselTracks.toArray();
    expect(remaining).toHaveLength(1);
    expect(remaining[0].observedAt).toBe(fresh.observedAt);
  });
});
