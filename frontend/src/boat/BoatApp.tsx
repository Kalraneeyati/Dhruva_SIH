import { useState } from "react";
import { useLocale } from "../shared/hooks/useLocale";
import { queryAdvisory } from "../shared/api/client";
import type { AdvisoryResponse } from "../shared/types/domain";
import { speak } from "../shared/voice/speech";
import { VerdictCard } from "./components/VerdictCard";
import { Readout } from "./components/Readout";
import { PfzRow } from "./components/PfzRow";
import { BoundaryCountdown } from "./components/BoundaryCountdown";
import { EvidencePanel } from "./components/EvidencePanel";
import { CapsulePanel } from "./components/CapsulePanel";
import { QueryBar } from "./components/QueryBar";
import { ConnectionBadge } from "./components/ConnectionBadge";
import { LanguageSwitcher } from "./components/LanguageSwitcher";

/**
 * The boat surface. IMPLEMENTATION.md: "the boat surface is the one that must
 * be finished" — this is the render order that encodes "NO-GO outranks
 * everything": VerdictCard always mounts first, before PfzRow, so an active
 * hazard is never scrolled past to reach a favourable fishing zone.
 */
export function BoatApp() {
  const { t } = useLocale();
  const [response, setResponse] = useState<AdvisoryResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const ask = async (text: string) => {
    setBusy(true);
    setError(null);
    try {
      const result = await queryAdvisory(text);
      setResponse(result);
      speak(result.narrative, result.detectedLanguage || "en");
    } catch {
      setError("Could not reach the advisory service. Showing nothing rather than a guess.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={{ maxWidth: 720, margin: "0 auto", padding: "var(--space-4)", display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "var(--space-2)" }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 22 }}>{t("appName")}</h1>
          <p style={{ margin: 0, fontSize: 12, color: "var(--color-text-muted)" }}>{t("tagline")}</p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
          <ConnectionBadge />
          <LanguageSwitcher />
        </div>
      </header>

      <QueryBar onSubmit={ask} busy={busy} />

      {error && (
        <p role="alert" style={{ color: "var(--color-nogo)" }}>
          {error}
        </p>
      )}

      {response && (
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
          <p style={{ margin: 0, fontSize: 16 }}>{response.narrative}</p>

          {/* Render order is the safety contract: verdict, THEN everything
              else. Never reorder this list. */}
          {response.verdict && <VerdictCard verdict={response.verdict} />}
          {response.conditions && <Readout conditions={response.conditions} />}
          {response.pfz.length > 0 && <PfzRow records={response.pfz} />}
          {response.boundaries.length > 0 && <BoundaryCountdown boundaries={response.boundaries} />}
          <EvidencePanel response={response} />
          <CapsulePanel capsule={response.capsule} />
        </div>
      )}

      <footer style={{ fontSize: 11, color: "var(--color-text-muted)", textAlign: "center", padding: "var(--space-3) 0" }}>
        {t("advisoryOnly")}
      </footer>
    </div>
  );
}
