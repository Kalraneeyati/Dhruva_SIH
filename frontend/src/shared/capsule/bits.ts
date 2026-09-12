/**
 * MSB-first bit packing over a byte array. Pure — no network, no filesystem, no
 * clock, per CLAUDE.md: "The decoder is pure... Python and TypeScript run the
 * same corpus in CI." This is the TypeScript half of that pair.
 */

export class BitWriter {
  private bytes: Uint8Array;
  private bitPos = 0;

  constructor(totalBits: number) {
    this.bytes = new Uint8Array(Math.ceil(totalBits / 8));
  }

  /** Write the low `width` bits of `value`, MSB-first. */
  write(value: number, width: number): void {
    if (value < 0 || value >= 2 ** width) {
      throw new Error(`value ${value} does not fit in ${width} bits`);
    }
    for (let i = width - 1; i >= 0; i--) {
      const bit = (value >>> i) & 1;
      const byteIndex = this.bitPos >>> 3;
      const bitInByte = 7 - (this.bitPos & 7);
      if (bit) this.bytes[byteIndex] |= 1 << bitInByte;
      this.bitPos++;
    }
  }

  toBytes(): Uint8Array {
    return this.bytes;
  }
}

export class BitReader {
  private bitPos = 0;
  private bytes: Uint8Array;

  constructor(bytes: Uint8Array) {
    this.bytes = bytes;
  }

  read(width: number): number {
    let value = 0;
    for (let i = 0; i < width; i++) {
      const byteIndex = this.bitPos >>> 3;
      const bitInByte = 7 - (this.bitPos & 7);
      const bit = (this.bytes[byteIndex] >>> bitInByte) & 1;
      value = (value << 1) | bit;
      this.bitPos++;
    }
    return value >>> 0;
  }
}

/** Clamp, never wrap. CLAUDE.md: "Wrapping a 9m sea into a calm reading is the
 * worst bug we can ship." Every quantiser in quantizers.ts routes through this. */
export function clampInt(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, Math.round(value)));
}
