import { describe, expect, it } from "vitest";
import { contrastRatio } from "./contrast";

// Mirrors tokens.css exactly — if a colour changes there, change it here too;
// the test fails loudly rather than the app silently shipping a chip under 7:1.
const PAIRS: [name: string, bg: string, text: string][] = [
  ["safe chip", "#37c26a", "#04170a"],
  ["caution chip", "#f4c542", "#251d02"],
  ["no-go chip", "#ff7a7a", "#000000"],
  ["unknown chip", "#a9c0d1", "#04121f"],
  ["body text on background", "#081018", "#f4f8fb"],
  ["muted text on background", "#081018", "#a9c0d1"],
];

describe("risk chip contrast (WCAG AAA, >=7:1)", () => {
  it.each(PAIRS)("%s meets 7:1", (_name, bg, text) => {
    expect(contrastRatio(bg, text)).toBeGreaterThanOrEqual(7);
  });
});
