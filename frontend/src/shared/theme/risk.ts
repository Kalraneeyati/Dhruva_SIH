/**
 * Risk-class -> visual encoding. IMPLEMENTATION.md: "colour never carrying the
 * verdict alone" — every entry pairs a colour with a glyph AND a text label,
 * so a colour-blind reader, a black-and-white printout, and a screen reader
 * all get the same verdict. contrast.ts proves the colour pairs meet 7:1.
 */
import type { RiskClass } from "../types/domain";
import type { UiLocale } from "../i18n/strings";
import { t } from "../i18n/strings";

export interface RiskVisual {
  glyph: string;
  bgVar: string;
  textVar: string;
  labelKey: "verdictSafe" | "verdictCaution" | "verdictNoGo" | "verdictUnknown";
}

export const RISK_VISUALS: Record<RiskClass, RiskVisual> = {
  safe: { glyph: "✓", bgVar: "var(--color-safe)", textVar: "var(--color-safe-text)", labelKey: "verdictSafe" },
  caution: { glyph: "⚠", bgVar: "var(--color-caution)", textVar: "var(--color-caution-text)", labelKey: "verdictCaution" },
  no_go: { glyph: "✕", bgVar: "var(--color-nogo)", textVar: "var(--color-nogo-text)", labelKey: "verdictNoGo" },
  unknown: { glyph: "?", bgVar: "var(--color-unknown)", textVar: "var(--color-unknown-text)", labelKey: "verdictUnknown" },
};

export function riskLabel(risk: RiskClass, locale: UiLocale): string {
  return t(locale, RISK_VISUALS[risk].labelKey);
}
