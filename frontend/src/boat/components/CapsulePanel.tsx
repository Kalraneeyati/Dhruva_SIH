import { useEffect, useMemo, useRef, useState } from "react";
import type { Capsule } from "../../shared/types/domain";
import { capsuleToPayload, capsuleToQrDataUrl, decodeQrFromImageData, payloadToCapsule } from "../../shared/capsule";
import { CAPSULE_TOTAL_BITS, NAVIC_SEGMENT_BITS } from "../../shared/capsule/fieldTable";
import { renderReason } from "../../shared/capsule/codebook";
import { useLocale } from "../../shared/hooks/useLocale";
import { saveCapsule } from "../../shared/offline/db";

/**
 * The offline demo: encode the current advisory into a 145-bit capsule, show
 * it as a QR, and — the actual "airplane mode" trick — decode a scanned QR
 * with zero network involved anywhere in this component. Camera scanning
 * degrades to a paste-the-string field if the camera is denied or unavailable,
 * so the demo still works if the venue's second device has camera trouble.
 */
export function CapsulePanel({ capsule }: { capsule: Capsule | null }) {
  const { locale, t } = useLocale();
  const [qrDataUrl, setQrDataUrl] = useState<string | null>(null);
  const payload = useMemo(() => (capsule ? capsuleToPayload(capsule) : ""), [capsule]);
  const [scanning, setScanning] = useState(false);
  const [scannedText, setScannedText] = useState<string | null>(null);
  const [pasteValue, setPasteValue] = useState("");
  const [decodeError, setDecodeError] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    if (!capsule) {
      setQrDataUrl(null);
      return;
    }
    capsuleToQrDataUrl(capsule).then(setQrDataUrl).catch(() => setQrDataUrl(null));
    saveCapsule(payload, capsule).catch(() => {
      // best-effort local cache; not fatal to the demo if IndexedDB is unavailable
    });
  }, [capsule, payload]);

  const stopScan = () => {
    setScanning(false);
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    streamRef.current?.getTracks().forEach((tr) => tr.stop());
    streamRef.current = null;
  };

  const startScan = async () => {
    setDecodeError(null);
    setScannedText(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setScanning(true);
      const canvas = document.createElement("canvas");
      const ctx = canvas.getContext("2d");
      const tick = () => {
        const video = videoRef.current;
        if (video && ctx && video.videoWidth > 0) {
          canvas.width = video.videoWidth;
          canvas.height = video.videoHeight;
          ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
          const frame = ctx.getImageData(0, 0, canvas.width, canvas.height);
          const text = decodeQrFromImageData(frame);
          if (text) {
            setScannedText(text);
            stopScan();
            return;
          }
        }
        rafRef.current = requestAnimationFrame(tick);
      };
      rafRef.current = requestAnimationFrame(tick);
    } catch {
      setDecodeError("Camera unavailable — paste the payload string below instead.");
    }
  };

  useEffect(() => stopScan, []);

  const decodedFromScan = scannedText ? tryDecode(scannedText) : null;
  const decodedFromPaste = pasteValue ? tryDecode(pasteValue) : null;
  const decoded = decodedFromScan ?? decodedFromPaste;

  return (
    <section style={{ background: "var(--color-surface-raised)", borderRadius: "var(--radius-lg)", padding: "var(--space-4)", display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
      <h3 style={{ margin: 0, fontSize: 15 }}>
        {t("offlineMode")} — {t("capsuleBits")} / {NAVIC_SEGMENT_BITS}-bit NavIC segment
      </h3>

      {capsule ? (
        <div style={{ display: "flex", gap: "var(--space-4)", flexWrap: "wrap", alignItems: "flex-start" }}>
          <div>
            {qrDataUrl && <img src={qrDataUrl} alt="Offline advisory QR code" width={180} height={180} style={{ borderRadius: "var(--radius-sm)", background: "#fff", padding: 6 }} />}
            <div style={{ fontSize: 11, color: "var(--color-text-muted)", marginTop: 6, wordBreak: "break-all", maxWidth: 180 }}>{payload}</div>
          </div>
          <div style={{ flex: 1, minWidth: 200, fontSize: 13 }}>
            <p style={{ margin: "0 0 var(--space-2)" }}>
              {CAPSULE_TOTAL_BITS} bits used, {NAVIC_SEGMENT_BITS - CAPSULE_TOTAL_BITS} free. Same wire format over QR, Bluetooth and SMS.
            </p>
            <p style={{ margin: 0, fontStyle: "italic" }}>{renderReason(capsule, locale, "0 min")}</p>
          </div>
        </div>
      ) : (
        <p style={{ margin: 0, fontSize: 13, color: "var(--color-text-muted)" }}>Ask a question that produces a risk verdict to generate a capsule.</p>
      )}

      <div style={{ borderTop: "1px solid var(--color-border)", paddingTop: "var(--space-3)" }}>
        <h4 style={{ margin: "0 0 var(--space-2)", fontSize: 13 }}>{t("scanCapsule")} — put this device in airplane mode first</h4>
        <div style={{ display: "flex", gap: "var(--space-2)", flexWrap: "wrap" }}>
          {!scanning ? (
            <button type="button" onClick={startScan} style={{ borderRadius: "var(--radius-md)", border: "1px solid var(--color-border)", background: "var(--color-surface)", color: "var(--color-text)" }}>
              Start camera scan
            </button>
          ) : (
            <button type="button" onClick={stopScan} style={{ borderRadius: "var(--radius-md)", border: "1px solid var(--color-border)", background: "var(--color-nogo)", color: "var(--color-nogo-text)" }}>
              Stop scan
            </button>
          )}
        </div>
        <video ref={videoRef} muted playsInline style={{ display: scanning ? "block" : "none", width: "100%", maxWidth: 260, marginTop: "var(--space-2)", borderRadius: "var(--radius-sm)" }} />
        {decodeError && <p style={{ fontSize: 12, color: "var(--color-caution)" }}>{decodeError}</p>}

        <label style={{ display: "block", marginTop: "var(--space-2)", fontSize: 12, color: "var(--color-text-muted)" }}>
          Or paste a base32 capsule payload:
          <input
            type="text"
            value={pasteValue}
            onChange={(e) => setPasteValue(e.target.value)}
            placeholder="e.g. JBSWY3DPFQQFO33SNRSCC..."
            style={{ display: "block", width: "100%", marginTop: 4, minHeight: 44, padding: "0 var(--space-3)", borderRadius: "var(--radius-sm)", border: "1px solid var(--color-border)", background: "var(--color-surface)", color: "var(--color-text)" }}
          />
        </label>

        {decoded && (
          <div style={{ marginTop: "var(--space-3)", background: "var(--color-surface)", borderRadius: "var(--radius-md)", padding: "var(--space-3)" }}>
            <p style={{ margin: 0, fontWeight: 600 }}>Decoded offline — zero network used:</p>
            <p style={{ margin: "4px 0 0" }}>{renderReason(decoded, locale, "unknown")}</p>
          </div>
        )}
      </div>
    </section>
  );
}

function tryDecode(text: string): Capsule | null {
  try {
    return payloadToCapsule(text);
  } catch {
    return null;
  }
}
