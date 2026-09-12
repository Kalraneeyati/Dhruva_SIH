/**
 * The 145-bit capsule field table — CLAUDE.md, "Capsule" section. This is the
 * single source of truth for field order and width; encode() and decode() both
 * derive offsets from it so they cannot drift apart (capsule-auditor's first
 * check: "Recompute offsets from widths rather than trusting the constants").
 *
 * Total width must be exactly 145 (75 free inside the 220-bit NavIC segment).
 * `capsule.test.ts` asserts this on import, not just in CI.
 */

export interface FieldSpec {
  name: string;
  width: number;
}

// Order and widths transcribed verbatim from CLAUDE.md's field table.
export const FIELD_TABLE: readonly FieldSpec[] = [
  { name: "msg_type", width: 4 },
  { name: "schema_ver", width: 3 },
  { name: "issue_slot", width: 10 },
  { name: "valid_hours", width: 4 },
  { name: "zone_id", width: 20 },
  { name: "lat_offset", width: 8 },
  { name: "lon_offset", width: 8 },
  { name: "risk_class", width: 2 },
  { name: "hazard_flags", width: 8 },
  { name: "wave_hs", width: 5 },
  { name: "wind_kt", width: 6 },
  { name: "wind_dir", width: 4 },
  { name: "curr_kt", width: 5 },
  { name: "curr_dir", width: 4 },
  { name: "sst", width: 5 },
  { name: "chl_class", width: 2 },
  { name: "pfz_bearing", width: 4 },
  { name: "pfz_dist_nm", width: 6 },
  { name: "pfz_conf", width: 2 },
  { name: "bnd_dist_nm", width: 5 },
  { name: "bnd_type", width: 2 },
  { name: "bnd_eta_min", width: 8 },
  { name: "reason_code", width: 8 },
  { name: "evidence_hash", width: 12 },
] as const;

export const CAPSULE_TOTAL_BITS = 145;
export const NAVIC_SEGMENT_BITS = 220;
export const CAPSULE_BYTES = 19; // ceil(145/8) = 19, matches the QR/BLE/SMS wire size

export interface FieldOffset extends FieldSpec {
  offset: number;
}

/** Cumulative offsets, recomputed every time — never hand-maintained. */
export function fieldOffsets(): FieldOffset[] {
  let offset = 0;
  return FIELD_TABLE.map((f) => {
    const withOffset = { ...f, offset };
    offset += f.width;
    return withOffset;
  });
}

export function assertTableIntegrity(): void {
  const offsets = fieldOffsets();
  const total = offsets.reduce((sum, f) => sum + f.width, 0);
  if (total !== CAPSULE_TOTAL_BITS) {
    throw new Error(
      `capsule field table is ${total} bits, expected exactly ${CAPSULE_TOTAL_BITS}`,
    );
  }
  const names = new Set<string>();
  for (const f of offsets) {
    if (names.has(f.name)) throw new Error(`duplicate capsule field: ${f.name}`);
    names.add(f.name);
  }
  // No field may overlap another — true by construction from cumulative
  // offsets, but checked explicitly so a future hand-edit cannot break it.
  for (let i = 1; i < offsets.length; i++) {
    const prevEnd = offsets[i - 1].offset + offsets[i - 1].width;
    if (offsets[i].offset !== prevEnd) {
      throw new Error(`capsule field ${offsets[i].name} does not start where the prior field ends`);
    }
  }
}

// Fails fast on import if the table is ever hand-edited into an inconsistent state.
assertTableIntegrity();
