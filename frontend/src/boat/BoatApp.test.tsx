import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BoatApp } from "./BoatApp";
import { LocaleProvider } from "../shared/hooks/useLocale";
import type { AdvisoryResponse } from "../shared/types/domain";

vi.mock("../shared/voice/speech", () => ({
  speak: vi.fn(),
  speechRecognitionAvailable: () => false,
  speechSynthesisAvailable: () => false,
  recognizeSpeech: vi.fn(),
}));

const hazardResponse: AdvisoryResponse = {
  queryText: "Which fishing zones should be avoided?",
  detectedLanguage: "en",
  intent: "geofence_avoidance",
  narrative: "Multiple hazards active near a favourable fishing zone.",
  verdict: {
    riskClass: "no_go",
    boatClass: "frp_country_craft",
    overrideActive: true,
    overrideReason: "Cyclone warning active within 300km",
    computedAt: new Date().toISOString(),
    dataAgeSeconds: 300,
    advisoryNotice: "Advisory only. Follow official INCOIS and IMD warnings.",
    factors: [],
  },
  conditions: null,
  pfz: [
    {
      landingCentre: "Munambam",
      sourceUrl: "https://incois.gov.in/MarineFisheries/TextDataHome",
      issuedFor: "2026-09-12",
      bearingDeg: 250,
      distanceNm: 8,
      depthM: 40,
      lat: 10,
      lon: 76,
      region: "Kerala",
      confidence: "official",
    },
  ],
  boundaries: [],
  route: null,
  capsule: null,
  trace: [{ agent: "planner", startedAt: "", finishedAt: "", ok: true, summary: "done" }],
  firewallRetried: false,
  firewallFellBackToTemplate: false,
};

vi.mock("../shared/api/client", () => ({
  queryAdvisory: vi.fn(async () => hazardResponse),
}));

describe("BoatApp — NO-GO outranks everything (IMPLEMENTATION.md)", () => {
  it("renders the verdict card before the PFZ row in document order, even for a favourable-zone query", async () => {
    const user = userEvent.setup();
    render(
      <LocaleProvider>
        <BoatApp />
      </LocaleProvider>,
    );

    await user.type(screen.getByPlaceholderText(/ask about sea conditions/i), "Which fishing zones should be avoided?");
    await user.keyboard("{Enter}");

    await waitFor(() => expect(screen.getByText(/Cyclone warning active/i)).toBeInTheDocument());

    const verdictNode = screen.getByText(/Cyclone warning active/i);
    const pfzNode = screen.getByText(/Munambam/i);

    // DOCUMENT_POSITION_FOLLOWING means `pfzNode` comes AFTER `verdictNode`.
    const relation = verdictNode.compareDocumentPosition(pfzNode);
    expect(relation & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });
});
