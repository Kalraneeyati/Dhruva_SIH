/**
 * The 145-bit capsule codec. Pure: no network, no filesystem, no clock (the
 * caller supplies `issueSlot`/`schemaVer`/etc already computed) — CLAUDE.md
 * requires this because the decoder must run forever on a phone in airplane
 * mode, and a corpus of these encode/decode round-trips is meant to run
 * identically in the Python backend's eventual codec/ module and here.
 *
 * `encode` never throws on out-of-range physical input — every quantiser
 * clamps (bits.ts::clampInt). The one thing `encode` DOES throw on is an
 * internal field-table bug, which `fieldTable.ts` already guards at import
 * time.
 */
import { BitReader, BitWriter } from "./bits";
import { boundaryTypeCodec, chlClassCodec, decodeHazardFlags, encodeHazardFlags, msgTypeCodec, quantize, dequantize, riskClassCodec } from "./quantizers";
import { CAPSULE_BYTES, fieldOffsets } from "./fieldTable";
import type { Capsule } from "../types/domain";
import { clampInt } from "./bits";

const OFFSETS = fieldOffsets();
const byName = Object.fromEntries(OFFSETS.map((f) => [f.name, f]));

function widthOf(name: string): number {
  return byName[name].width;
}

export function encodeCapsule(c: Capsule): Uint8Array {
  const w = new BitWriter(CAPSULE_BYTES * 8);

  w.write(msgTypeCodec.encode(c.msgType), widthOf("msg_type"));
  w.write(clampInt(c.schemaVer, 0, 2 ** widthOf("schema_ver") - 1), widthOf("schema_ver"));
  w.write(clampInt(c.issueSlot, 0, 2 ** widthOf("issue_slot") - 1), widthOf("issue_slot"));
  w.write(clampInt(c.validHours, 0, 2 ** widthOf("valid_hours") - 1), widthOf("valid_hours"));
  w.write(clampInt(c.zoneId, 0, 2 ** widthOf("zone_id") - 1), widthOf("zone_id"));
  w.write(clampInt(c.latOffset, 0, 255), widthOf("lat_offset"));
  w.write(clampInt(c.lonOffset, 0, 255), widthOf("lon_offset"));
  w.write(riskClassCodec.encode(c.riskClass), widthOf("risk_class"));
  w.write(encodeHazardFlags(c.hazardFlags), widthOf("hazard_flags"));
  w.write(quantize.waveHs(c.waveHs), widthOf("wave_hs"));
  w.write(quantize.windKt(c.windKt), widthOf("wind_kt"));
  w.write(clampInt(c.windDir16, 0, 15), widthOf("wind_dir"));
  w.write(quantize.currKt(c.currKt), widthOf("curr_kt"));
  w.write(clampInt(c.currDir16, 0, 15), widthOf("curr_dir"));
  w.write(quantize.sst(c.sstC), widthOf("sst"));
  w.write(chlClassCodec.encode(c.chlClass), widthOf("chl_class"));
  w.write(clampInt(c.pfzBearing16, 0, 15), widthOf("pfz_bearing"));
  w.write(quantize.pfzDistNm(c.pfzDistNm), widthOf("pfz_dist_nm"));
  w.write(clampInt(c.pfzConfidence, 0, 3), widthOf("pfz_conf"));
  w.write(quantize.bndDistNm(c.bndDistNm), widthOf("bnd_dist_nm"));
  w.write(boundaryTypeCodec.encode(c.bndType), widthOf("bnd_type"));
  w.write(quantize.bndEtaMin(c.bndEtaMin), widthOf("bnd_eta_min"));
  w.write(clampInt(c.reasonCode, 0, 255), widthOf("reason_code"));
  w.write(parseEvidenceHash(c.evidenceHash), widthOf("evidence_hash"));

  return w.toBytes();
}

export function decodeCapsule(bytes: Uint8Array): Capsule {
  if (bytes.length < CAPSULE_BYTES) {
    throw new Error(`capsule must be at least ${CAPSULE_BYTES} bytes, got ${bytes.length}`);
  }
  const r = new BitReader(bytes);

  const msgType = msgTypeCodec.decode(r.read(widthOf("msg_type")));
  const schemaVer = r.read(widthOf("schema_ver"));
  const issueSlot = r.read(widthOf("issue_slot"));
  const validHours = r.read(widthOf("valid_hours"));
  const zoneId = r.read(widthOf("zone_id"));
  const latOffset = r.read(widthOf("lat_offset"));
  const lonOffset = r.read(widthOf("lon_offset"));
  const riskClass = riskClassCodec.decode(r.read(widthOf("risk_class")));
  const hazardFlags = decodeHazardFlags(r.read(widthOf("hazard_flags")));
  const waveHs = dequantize.waveHs(r.read(widthOf("wave_hs")));
  const windKt = dequantize.windKt(r.read(widthOf("wind_kt")));
  const windDir16 = r.read(widthOf("wind_dir"));
  const currKt = dequantize.currKt(r.read(widthOf("curr_kt")));
  const currDir16 = r.read(widthOf("curr_dir"));
  const sstC = dequantize.sst(r.read(widthOf("sst")));
  const chlClass = chlClassCodec.decode(r.read(widthOf("chl_class")));
  const pfzBearing16 = r.read(widthOf("pfz_bearing"));
  const pfzDistNm = dequantize.pfzDistNm(r.read(widthOf("pfz_dist_nm")));
  const pfzConfidence = r.read(widthOf("pfz_conf")) as 0 | 1 | 2 | 3;
  const bndDistNm = dequantize.bndDistNm(r.read(widthOf("bnd_dist_nm")));
  const bndType = boundaryTypeCodec.decode(r.read(widthOf("bnd_type")));
  const bndEtaMin = dequantize.bndEtaMin(r.read(widthOf("bnd_eta_min")));
  const reasonCode = r.read(widthOf("reason_code"));
  const evidenceHash = formatEvidenceHash(r.read(widthOf("evidence_hash")));

  return {
    msgType, schemaVer, issueSlot, validHours, zoneId, latOffset, lonOffset,
    riskClass, hazardFlags, waveHs, windKt, windDir16, currKt, currDir16,
    sstC, chlClass, pfzBearing16, pfzDistNm, pfzConfidence, bndDistNm,
    bndType, bndEtaMin, reasonCode, evidenceHash,
  };
}

/** Accepts a full SHA-256 hex digest or an already-truncated 3-hex-char
 * fingerprint; only the top 12 bits ever reach the wire. */
function parseEvidenceHash(hash: string): number {
  const prefix = hash.slice(0, 3).padEnd(3, "0");
  return clampInt(parseInt(prefix, 16), 0, 4095);
}

function formatEvidenceHash(raw: number): string {
  return raw.toString(16).padStart(3, "0");
}

/** SHA-256 over a canonical JSON encoding of the evidence bundle, truncated to
 * the 3 hex chars (12 bits) the capsule carries. Async because Web Crypto is;
 * callers build the Capsule after awaiting this once per advisory. */
export async function computeEvidenceFingerprint(evidence: unknown): Promise<string> {
  const canonical = JSON.stringify(evidence, Object.keys(evidence as object).sort());
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(canonical));
  const hex = Array.from(new Uint8Array(digest)).map((b) => b.toString(16).padStart(2, "0")).join("");
  return hex.slice(0, 3);
}
