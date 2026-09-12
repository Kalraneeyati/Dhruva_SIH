/**
 * QR transport for the capsule. Generation and decoding both operate on the
 * base32 string only — this is the literal "airplane mode" demo: encode a
 * capsule, render the QR, put the phone in airplane mode, scan it with a
 * second device, decode, speak the advisory. No network touches any of this.
 */
import QRCode from "qrcode";
import jsQR from "jsqr";
import { base32Decode, base32Encode } from "./base32";
import { decodeCapsule, encodeCapsule } from "./codec";
import type { Capsule } from "../types/domain";

export function capsuleToPayload(capsule: Capsule): string {
  return base32Encode(encodeCapsule(capsule));
}

export function payloadToCapsule(payload: string): Capsule {
  return decodeCapsule(base32Decode(payload));
}

export async function capsuleToQrDataUrl(capsule: Capsule): Promise<string> {
  const payload = capsuleToPayload(capsule);
  return QRCode.toDataURL(payload, { margin: 1, scale: 8, errorCorrectionLevel: "M" });
}

/** Decode a QR from a still video frame (ImageData). Returns null if no QR
 * was found in the frame — callers poll this on a requestAnimationFrame loop
 * against the camera feed. */
export function decodeQrFromImageData(imageData: ImageData): string | null {
  const result = jsQR(imageData.data, imageData.width, imageData.height);
  return result?.data ?? null;
}
