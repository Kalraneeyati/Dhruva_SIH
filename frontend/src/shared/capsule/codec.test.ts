import { describe, expect, it } from "vitest";
import { decodeCapsule, encodeCapsule } from "./codec";
import { base32Decode, base32Encode } from "./base32";
import { CAPSULE_BYTES, CAPSULE_TOTAL_BITS, fieldOffsets } from "./fieldTable";
import { decodeZone, encodeZone } from "./quantizers";
import type { Capsule } from "../types/domain";

function sampleCapsule(overrides: Partial<Capsule> = {}): Capsule {
  return {
    msgType: "advisory",
    schemaVer: 1,
    issueSlot: 200,
    validHours: 6,
    zoneId: 12345,
    latOffset: 128,
    lonOffset: 64,
    riskClass: "caution",
    hazardFlags: ["wave", "wind"],
    waveHs: 2.25,
    windKt: 22,
    windDir16: 4,
    currKt: 0.8,
    currDir16: 9,
    sstC: 28.5,
    chlClass: "moderate",
    pfzBearing16: 2,
    pfzDistNm: 14,
    pfzConfidence: 2,
    bndDistNm: 9,
    bndType: "imbl",
    bndEtaMin: 47,
    reasonCode: 1,
    evidenceHash: "a3f9c1",
    ...overrides,
  };
}

describe("capsule field table", () => {
  it("totals exactly 145 bits with no gaps or overlaps", () => {
    const offsets = fieldOffsets();
    expect(offsets.reduce((s, f) => s + f.width, 0)).toBe(CAPSULE_TOTAL_BITS);
    expect(CAPSULE_TOTAL_BITS).toBe(145);
  });

  it("fits in 19 bytes (the QR/BLE/SMS wire size)", () => {
    expect(CAPSULE_BYTES).toBe(19);
    expect(Math.ceil(CAPSULE_TOTAL_BITS / 8)).toBeLessThanOrEqual(CAPSULE_BYTES);
  });
});

describe("capsule codec round-trip", () => {
  const corpus: Capsule[] = [
    sampleCapsule(),
    sampleCapsule({ riskClass: "safe", hazardFlags: [], waveHs: 0.1, windKt: 3 }),
    sampleCapsule({
      riskClass: "no_go",
      hazardFlags: ["cyclone", "lightning", "tsunami"],
      waveHs: 9.0, // must saturate, not wrap
      windKt: 90, // must saturate
    }),
    sampleCapsule({ bndType: "closed", chlClass: "very_high", pfzConfidence: 3 }),
    sampleCapsule({ msgType: "test", reasonCode: 255, schemaVer: 7 }),
    sampleCapsule({ windDir16: 15, currDir16: 0, pfzBearing16: 8 }),
  ];

  it.each(corpus.map((c, i) => [i, c] as const))("round-trips corpus entry %i", (_i, capsule) => {
    const bytes = encodeCapsule(capsule);
    expect(bytes.length).toBe(CAPSULE_BYTES);
    const decoded = decodeCapsule(bytes);

    expect(decoded.msgType).toBe(capsule.msgType);
    expect(decoded.riskClass).toBe(capsule.riskClass);
    expect(decoded.hazardFlags.sort()).toEqual(capsule.hazardFlags.sort());
    expect(decoded.windDir16).toBe(capsule.windDir16);
    expect(decoded.currDir16).toBe(capsule.currDir16);
    expect(decoded.pfzBearing16).toBe(capsule.pfzBearing16);
    expect(decoded.bndType).toBe(capsule.bndType);
    expect(decoded.chlClass).toBe(capsule.chlClass);
  });

  it("quantises wave height to the 0.25m grid within tolerance", () => {
    const bytes = encodeCapsule(sampleCapsule({ waveHs: 2.25 }));
    const decoded = decodeCapsule(bytes);
    expect(decoded.waveHs).toBeCloseTo(2.25, 5);
  });

  it("quantises SST to the 0.5C grid within tolerance", () => {
    const bytes = encodeCapsule(sampleCapsule({ sstC: 28.5 }));
    const decoded = decodeCapsule(bytes);
    expect(decoded.sstC).toBeCloseTo(28.5, 5);
  });
});

describe("saturating quantisers — never wrap", () => {
  it("clamps a 9m sea to the max wave_hs bucket, not a wrapped small value", () => {
    const bytes = encodeCapsule(sampleCapsule({ waveHs: 9.0 }));
    const decoded = decodeCapsule(bytes);
    // 31 * 0.25 = 7.75, the documented saturation ceiling.
    expect(decoded.waveHs).toBeCloseTo(7.75, 5);
    expect(decoded.waveHs).toBeGreaterThan(5); // the regression this guards against
  });

  it("clamps negative wave height to zero rather than underflowing", () => {
    const bytes = encodeCapsule(sampleCapsule({ waveHs: -3 }));
    expect(decodeCapsule(bytes).waveHs).toBe(0);
  });

  it("clamps wind speed at 63kt", () => {
    const bytes = encodeCapsule(sampleCapsule({ windKt: 400 }));
    expect(decodeCapsule(bytes).windKt).toBe(63);
  });

  it("clamps out-of-range zone id into the valid 20-bit range", () => {
    const bytes = encodeCapsule(sampleCapsule({ zoneId: 999_999_999 }));
    const decoded = decodeCapsule(bytes);
    expect(decoded.zoneId).toBeLessThan(2 ** 20);
  });
});

describe("QR base32 wire format", () => {
  it("round-trips arbitrary bytes through base32", () => {
    const bytes = encodeCapsule(sampleCapsule());
    const text = base32Encode(bytes);
    expect(text).toMatch(/^[A-Z2-7]+$/);
    const back = base32Decode(text);
    expect(Array.from(back.slice(0, bytes.length))).toEqual(Array.from(bytes));
  });

  it("is resilient to a scanner lower-casing the payload", () => {
    const bytes = encodeCapsule(sampleCapsule());
    const text = base32Encode(bytes).toLowerCase();
    const back = base32Decode(text);
    expect(Array.from(back.slice(0, bytes.length))).toEqual(Array.from(bytes));
  });
});

describe("zone encoding", () => {
  it("round-trips a real Indian coastal point within ~25m", () => {
    // Kochi.
    const { zoneId, latOffsetRaw, lonOffsetRaw } = encodeZone(9.9658, 76.2367);
    const back = decodeZone(zoneId, latOffsetRaw, lonOffsetRaw);
    const kmPerDeg = 111.32;
    const dLat = (back.lat - 9.9658) * kmPerDeg;
    const dLon = (back.lon - 76.2367) * kmPerDeg * Math.cos((9.9658 * Math.PI) / 180);
    expect(Math.hypot(dLat, dLon)).toBeLessThan(0.03); // ~30m, matches the documented ~22m grid
  });

  it("clamps a point outside the capsule bbox to the nearest edge cell instead of throwing", () => {
    expect(() => encodeZone(40, 120)).not.toThrow();
    const { zoneId } = encodeZone(40, 120);
    expect(zoneId).toBeGreaterThanOrEqual(0);
    expect(zoneId).toBeLessThan(2 ** 20);
  });
});
