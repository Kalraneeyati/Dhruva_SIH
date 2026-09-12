/**
 * RFC 4648 base32 (no padding) — the wire encoding CLAUDE.md specifies for the
 * QR transport: "QR (19 bytes, base32 for scanner reliability)". Base32 avoids
 * mixed-case and the visually ambiguous glyphs a QR alphanumeric-mode encoder
 * would otherwise round-trip through, which matters when a crew member is
 * reading a printed capsule aloud over VHF as a fallback to scanning it.
 */
const ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";

export function base32Encode(bytes: Uint8Array): string {
  let bits = 0;
  let value = 0;
  let output = "";
  for (const byte of bytes) {
    value = (value << 8) | byte;
    bits += 8;
    while (bits >= 5) {
      output += ALPHABET[(value >>> (bits - 5)) & 31];
      bits -= 5;
    }
  }
  if (bits > 0) {
    output += ALPHABET[(value << (5 - bits)) & 31];
  }
  return output;
}

export function base32Decode(input: string): Uint8Array {
  const clean = input.toUpperCase().replace(/[^A-Z2-7]/g, "");
  const bytes: number[] = [];
  let bits = 0;
  let value = 0;
  for (const char of clean) {
    const idx = ALPHABET.indexOf(char);
    if (idx < 0) continue;
    value = (value << 5) | idx;
    bits += 5;
    if (bits >= 8) {
      bytes.push((value >>> (bits - 8)) & 0xff);
      bits -= 8;
    }
  }
  return new Uint8Array(bytes);
}
