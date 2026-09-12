/**
 * Offline persistence for the boat surface — IndexedDB via Dexie.
 *
 * IMPLEMENTATION.md Phase 5: "Offline via service worker + Dexie: codebook,
 * last capsules, cached fields, map tiles for the coastal window only." The
 * reason codebook itself ships inside the JS bundle (shared/capsule/codebook.ts)
 * so the service worker's app-shell cache already makes it available offline;
 * Dexie here holds the state that changes at runtime: capsules received or
 * generated, and the last known Conditions per query location.
 *
 * CLAUDE.md: "Vessel positions quantise to the 0.05 grid at rest, tracks purge
 * after 7 days" — `purgeStaleVesselTracks` enforces the retention half of that
 * (the shore console's mock fleet already emits pre-quantised positions).
 */
import Dexie, { type Table } from "dexie";
import type { Capsule, Conditions, VesselPosition } from "../types/domain";

export interface StoredCapsule {
  id: string; // zoneId + issueSlot, so re-storing the same advisory upserts
  receivedAt: string;
  capsule: Capsule;
  sourcePayload: string; // the base32 string, so it can be re-shown/re-shared
}

export interface StoredConditions {
  id: string; // `${lat.toFixed(2)},${lon.toFixed(2)}`
  cachedAt: string;
  conditions: Conditions;
}

export interface StoredVesselTrack {
  id: string; // `${vesselId}:${observedAt}`
  vesselId: string;
  observedAt: string;
  position: VesselPosition;
}

class DhruvaDb extends Dexie {
  capsules!: Table<StoredCapsule, string>;
  conditions!: Table<StoredConditions, string>;
  vesselTracks!: Table<StoredVesselTrack, string>;

  constructor() {
    super("dhruva-offline");
    this.version(1).stores({
      capsules: "id, receivedAt",
      conditions: "id, cachedAt",
      vesselTracks: "id, vesselId, observedAt",
    });
  }
}

export const db = new DhruvaDb();

export async function saveCapsule(payload: string, capsule: Capsule): Promise<void> {
  await db.capsules.put({
    id: `${capsule.zoneId}:${capsule.issueSlot}`,
    receivedAt: new Date().toISOString(),
    capsule,
    sourcePayload: payload,
  });
}

export async function recentCapsules(limit = 20): Promise<StoredCapsule[]> {
  return db.capsules.orderBy("receivedAt").reverse().limit(limit).toArray();
}

export async function cacheConditions(lat: number, lon: number, conditions: Conditions): Promise<void> {
  await db.conditions.put({
    id: cellKey(lat, lon),
    cachedAt: new Date().toISOString(),
    conditions,
  });
}

export async function getCachedConditions(lat: number, lon: number): Promise<Conditions | null> {
  const row = await db.conditions.get(cellKey(lat, lon));
  return row?.conditions ?? null;
}

function cellKey(lat: number, lon: number): string {
  return `${lat.toFixed(2)},${lon.toFixed(2)}`;
}

export async function recordVesselPosition(position: VesselPosition): Promise<void> {
  await db.vesselTracks.put({
    id: `${position.vesselId}:${position.observedAt}`,
    vesselId: position.vesselId,
    observedAt: position.observedAt,
    position,
  });
}

const SEVEN_DAYS_MS = 7 * 24 * 60 * 60 * 1000;

/** CLAUDE.md: "tracks purge after 7 days." Call this on app start and it is
 * also exercised directly in offline.test.ts with an injected clock. */
export async function purgeStaleVesselTracks(now: Date = new Date()): Promise<number> {
  const cutoff = new Date(now.getTime() - SEVEN_DAYS_MS).toISOString();
  const stale = await db.vesselTracks.where("observedAt").below(cutoff).primaryKeys();
  if (stale.length > 0) await db.vesselTracks.bulkDelete(stale);
  return stale.length;
}
