import { useMemo, useState } from "react";
import { encodeCapsule } from "../../shared/capsule/codec";
import { CAPSULE_BYTES, CAPSULE_TOTAL_BITS } from "../../shared/capsule/fieldTable";
import { base32Encode } from "../../shared/capsule/base32";
import { encodeZone } from "../../shared/capsule/quantizers";
import type { Capsule, HazardFlag, RiskClass } from "../../shared/types/domain";
import { useLocale } from "../../shared/hooks/useLocale";

const RISK_OPTIONS: RiskClass[] = ["safe", "caution", "no_go", "unknown"];
const HAZARD_OPTIONS: HazardFlag[] = ["wave", "wind", "squall", "lightning", "cyclone", "current", "fog", "tsunami"];

/** Shows the payload cost BEFORE sending, per IMPLEMENTATION.md Phase 5:
 * "broadcast composer showing payload cost before send." SMS is priced per
 * 160 (GSM-7) or 70 (UCS-2, for non-Latin scripts) character segment, so a
 * base32 capsule — pure ASCII — always ships as a single GSM-7 SMS segment,
 * which is worth showing explicitly next to a free-text alternative. */
export function BroadcastComposer() {
  const { t } = useLocale();
  const [riskClass, setRiskClass] = useState<RiskClass>("caution");
  const [hazards, setHazards] = useState<Set<HazardFlag>>(new Set(["wave"]));
  const [freeText, setFreeText] = useState("");

  const capsule: Capsule = useMemo(() => {
    const zone = encodeZone(9.9658, 76.2367);
    return {
      msgType: "alert",
      schemaVer: 1,
      issueSlot: 0,
      validHours: 6,
      zoneId: zone.zoneId,
      latOffset: zone.latOffsetRaw,
      lonOffset: zone.lonOffsetRaw,
      riskClass,
      hazardFlags: Array.from(hazards),
      waveHs: 2,
      windKt: 20,
      windDir16: 0,
      currKt: 0.5,
      currDir16: 0,
      sstC: 28,
      chlClass: "moderate",
      pfzBearing16: 0,
      pfzDistNm: 0,
      pfzConfidence: 0,
      bndDistNm: 31,
      bndType: "none",
      bndEtaMin: 0,
      reasonCode: riskClass === "no_go" ? 7 : riskClass === "safe" ? 0 : 1,
      evidenceHash: "000",
    };
  }, [riskClass, hazards]);

  const payload = base32Encode(encodeCapsule(capsule));
  const smsSegments = Math.ceil(payload.length / 160);
  const freeTextSegments = freeText.length === 0 ? 0 : Math.ceil(freeText.length / (isAsciiOnly(freeText) ? 160 : 70));

  const toggleHazard = (h: HazardFlag) => {
    setHazards((prev) => {
      const next = new Set(prev);
      if (next.has(h)) next.delete(h);
      else next.add(h);
      return next;
    });
  };

  return (
    <section style={{ background: "var(--color-surface-raised)", borderRadius: "var(--radius-lg)", padding: "var(--space-4)", display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
      <h3 style={{ margin: 0, fontSize: 15 }}>{t("broadcastHeading")}</h3>

      <label style={{ fontSize: 13 }}>
        Risk class
        <select value={riskClass} onChange={(e) => setRiskClass(e.target.value as RiskClass)} style={{ display: "block", marginTop: 4, minHeight: 44 }}>
          {RISK_OPTIONS.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
      </label>

      <fieldset style={{ border: "1px solid var(--color-border)", borderRadius: "var(--radius-sm)", padding: "var(--space-2)" }}>
        <legend style={{ fontSize: 12, color: "var(--color-text-muted)" }}>Hazard flags</legend>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)" }}>
          {HAZARD_OPTIONS.map((h) => (
            <label key={h} style={{ fontSize: 12, display: "flex", alignItems: "center", gap: 4 }}>
              <input type="checkbox" checked={hazards.has(h)} onChange={() => toggleHazard(h)} />
              {h}
            </label>
          ))}
        </div>
      </fieldset>

      <label style={{ fontSize: 13 }}>
        Free-text fallback (e.g. plain-language SMS to boats without a decoder)
        <textarea
          value={freeText}
          onChange={(e) => setFreeText(e.target.value)}
          rows={2}
          style={{ display: "block", width: "100%", marginTop: 4, borderRadius: "var(--radius-sm)", border: "1px solid var(--color-border)", background: "var(--color-surface)", color: "var(--color-text)", padding: "var(--space-2)" }}
        />
      </label>

      <div style={{ background: "var(--color-surface)", borderRadius: "var(--radius-md)", padding: "var(--space-3)", fontSize: 13 }}>
        <strong>{t("payloadCost")}:</strong>
        <div>
          Capsule: {CAPSULE_TOTAL_BITS} bits ({CAPSULE_BYTES} bytes) → base32 payload {payload.length} chars → {smsSegments} SMS segment{smsSegments !== 1 ? "s" : ""} (GSM-7)
        </div>
        {freeText.length > 0 && (
          <div>
            Free text: {freeText.length} chars → {freeTextSegments} SMS segment{freeTextSegments !== 1 ? "s" : ""} ({isAsciiOnly(freeText) ? "GSM-7" : "UCS-2, non-Latin script"})
          </div>
        )}
        <div style={{ marginTop: 4, fontFamily: "monospace", wordBreak: "break-all", color: "var(--color-text-muted)" }}>{payload}</div>
      </div>
    </section>
  );
}

function isAsciiOnly(text: string): boolean {
  // Intentionally matches the full 7-bit ASCII range, control characters
  // included — this is the actual GSM-7 vs UCS-2 encoding boundary SMS
  // gateways use, not a mistaken character-class range.
  // oxlint-disable-next-line no-control-regex
  return /^[\x00-\x7F]*$/.test(text);
}
