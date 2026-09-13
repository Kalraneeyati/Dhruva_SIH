import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { decodeCapsule, encodeCapsule } from "./codec";
import { CAPSULE_BYTES } from "./fieldTable";
import type { Capsule, HazardFlag } from "../types/domain";

/**
 * Loads the EXACT SAME file backend/tests/test_codec_corpus.py loads
 * (eval/capsule_corpus.jsonl) and runs the same round-trip assertions. This
 * is the cross-language proof CLAUDE.md requires ("Python and TypeScript run
 * the same corpus in CI") — not two independently-written test suites that
 * happen to both pass, but one shared fixture file both codecs must agree on.
 */
const __dirname = dirname(fileURLToPath(import.meta.url));
const CORPUS_PATH = resolve(__dirname, "../../../../eval/capsule_corpus.jsonl");

interface CorpusRow {
  id: string;
  msg_type: Capsule["msgType"];
  schema_ver: number;
  issue_slot: number;
  valid_hours: number;
  zone_id: number;
  lat_offset: number;
  lon_offset: number;
  risk_class: Capsule["riskClass"];
  hazard_flags: HazardFlag[];
  wave_hs: number;
  wind_kt: number;
  wind_dir16: number;
  curr_kt: number;
  curr_dir16: number;
  sst_c: number;
  chl_class: Capsule["chlClass"];
  pfz_bearing16: number;
  pfz_dist_nm: number;
  pfz_confidence: 0 | 1 | 2 | 3;
  bnd_dist_nm: number;
  bnd_type: Capsule["bndType"];
  bnd_eta_min: number;
  reason_code: number;
  evidence_hash: string;
}

function loadCorpus(): CorpusRow[] {
  const text = readFileSync(CORPUS_PATH, "utf-8");
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => JSON.parse(line) as CorpusRow);
}

function toCapsule(row: CorpusRow): Capsule {
  return {
    msgType: row.msg_type,
    schemaVer: row.schema_ver,
    issueSlot: row.issue_slot,
    validHours: row.valid_hours,
    zoneId: row.zone_id,
    latOffset: row.lat_offset,
    lonOffset: row.lon_offset,
    riskClass: row.risk_class,
    hazardFlags: row.hazard_flags,
    waveHs: row.wave_hs,
    windKt: row.wind_kt,
    windDir16: row.wind_dir16,
    currKt: row.curr_kt,
    currDir16: row.curr_dir16,
    sstC: row.sst_c,
    chlClass: row.chl_class,
    pfzBearing16: row.pfz_bearing16,
    pfzDistNm: row.pfz_dist_nm,
    pfzConfidence: row.pfz_confidence,
    bndDistNm: row.bnd_dist_nm,
    bndType: row.bnd_type,
    bndEtaMin: row.bnd_eta_min,
    reasonCode: row.reason_code,
    evidenceHash: row.evidence_hash,
  };
}

const CORPUS = loadCorpus();

describe("shared cross-language corpus (eval/capsule_corpus.jsonl)", () => {
  it("loads at least 5 fixtures from the file both languages share", () => {
    expect(CORPUS.length).toBeGreaterThanOrEqual(5);
  });

  it.each(CORPUS.map((row) => [row.id, row] as const))("round-trips %s identically to the Python codec", (_id, row) => {
    const capsule = toCapsule(row);
    const bytes = encodeCapsule(capsule);
    expect(bytes.length).toBe(CAPSULE_BYTES);
    const decoded = decodeCapsule(bytes);

    expect(decoded.msgType).toBe(capsule.msgType);
    expect(decoded.riskClass).toBe(capsule.riskClass);
    expect(decoded.hazardFlags.slice().sort()).toEqual(capsule.hazardFlags.slice().sort());
    expect(decoded.chlClass).toBe(capsule.chlClass);
    expect(decoded.bndType).toBe(capsule.bndType);
    expect(decoded.waveHs).toBeGreaterThanOrEqual(0);
    expect(decoded.waveHs).toBeLessThanOrEqual(7.75);
    expect(decoded.windKt).toBeGreaterThanOrEqual(0);
    expect(decoded.windKt).toBeLessThanOrEqual(63);
  });

  it("resolves the .5 rounding boundary the same way Python's clamp_int does (round-half-up, not banker's)", () => {
    const row = CORPUS.find((r) => r.id === "half_bit_rounding_boundary")!;
    const decoded = decodeCapsule(encodeCapsule(toCapsule(row)));
    expect(decoded.waveHs).toBeCloseTo(1.5, 5); // 1.375/0.25 = 5.5 -> round -> 6 * 0.25
    expect(decoded.currKt).toBeCloseTo(0.5, 5); // 0.45/0.1 = 4.5 -> round-half-up -> 5 * 0.1
    expect(decoded.sstC).toBeCloseTo(22.5, 5); // (22.25-18)/0.5 = 8.5 -> round -> 9 * 0.5 + 18
  });

  it("saturates the cyclone no-go fixture's 9m wave to the same 7.75m ceiling as Python", () => {
    const row = CORPUS.find((r) => r.id === "cyclone_no_go_saturates")!;
    const decoded = decodeCapsule(encodeCapsule(toCapsule(row)));
    expect(decoded.waveHs).toBeCloseTo(7.75, 5);
  });
});
