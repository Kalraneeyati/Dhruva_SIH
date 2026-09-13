import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useLocale } from "../shared/hooks/useLocale";
import { queryAdvisory } from "../shared/api/client";
import type { AdvisoryResponse, LatLon } from "../shared/types/domain";
import { speak } from "../shared/voice/speech";
import { RISK_VISUALS } from "../shared/theme/risk";
import { MiniMap, type MiniMapMarker } from "../shared/map/MiniMap";
import { VerdictCard } from "./components/VerdictCard";
import { Readout } from "./components/Readout";
import { PfzRow } from "./components/PfzRow";
import { BoundaryCountdown } from "./components/BoundaryCountdown";
import { EvidencePanel } from "./components/EvidencePanel";
import { CapsulePanel } from "./components/CapsulePanel";
import { AgentPipeline } from "./components/AgentPipeline";
import { TechnicalDetails } from "./components/TechnicalDetails";
import { QueryBar } from "./components/QueryBar";
import { ConnectionBadge } from "./components/ConnectionBadge";
import { LanguageSwitcher } from "./components/LanguageSwitcher";
import { BoatClassSelector, loadSavedBoatClass, saveBoatClass } from "./components/BoatClassSelector";
import { LocationControl } from "./components/LocationControl";
import type { BoatClass } from "../shared/types/domain";

const DEFAULT_CENTER: LatLon = { lat: 9.9658, lon: 76.2367 };

function mapPropsFor(response: AdvisoryResponse) {
  const center = response.conditions
    ? { lat: response.conditions.requestedLat, lon: response.conditions.requestedLon }
    : response.pfz[0]?.lat != null && response.pfz[0]?.lon != null
      ? { lat: response.pfz[0].lat, lon: response.pfz[0].lon }
      : DEFAULT_CENTER;

  const markers: MiniMapMarker[] = [];
  markers.push({ ...center, glyph: "●", bg: "#f4f8fb", fg: "#0b1a26", label: "Query location" });

  if (response.verdict) {
    const visual = RISK_VISUALS[response.verdict.riskClass];
    markers[0] = { ...center, glyph: visual.glyph, bg: visual.bgVar, fg: visual.textVar, label: "Your position" };
  }

  for (const pfz of response.pfz) {
    if (pfz.lat != null && pfz.lon != null) {
      markers.push({ lat: pfz.lat, lon: pfz.lon, glyph: "\u{1F41F}", bg: "#37c26a", fg: "#04170a", label: `PFZ — ${pfz.landingCentre}` });
    }
  }

  const hasSpatialContent = response.pfz.length > 0 || !!response.route || response.boundaries.length > 0;
  return { center, markers, route: response.route ?? undefined, show: !!response.conditions || hasSpatialContent };
}

/**
 * The boat surface. IMPLEMENTATION.md: "the boat surface is the one that must
 * be finished" — this is the render order that encodes "NO-GO outranks
 * everything": VerdictCard always mounts first, before PfzRow, so an active
 * hazard is never scrolled past to reach a favourable fishing zone.
 */
export function BoatApp() {
  const { t } = useLocale();
  const [searchParams] = useSearchParams();
  const [response, setResponse] = useState<AdvisoryResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [initialQuery] = useState(() => searchParams.get("q") ?? "");
  const autoSubmitted = useRef(false);
  const [boatClass, setBoatClass] = useState<BoatClass>(() => loadSavedBoatClass());
  const [userLocation, setUserLocation] = useState<LatLon | null>(null);

  const handleBoatClassChange = (value: BoatClass) => {
    setBoatClass(value);
    saveBoatClass(value);
  };

  const ask = async (text: string) => {
    setBusy(true);
    setError(null);
    try {
      const result = await queryAdvisory(text, {
        boatClass,
        location: userLocation ?? undefined,
      });
      setResponse(result);
      speak(result.narrative, result.detectedLanguage || "en");
    } catch {
      setError("Could not reach the advisory service. Showing nothing rather than a guess.");
    } finally {
      setBusy(false);
    }
  };

  const map = useMemo(() => (response ? mapPropsFor(response) : null), [response]);

  // Deep-linked from the landing page's "try it" cards (/boat?q=...): fire
  // the query automatically once, so tapping a card there feels like tapping
  // a button, not landing on an empty form the visitor still has to fill in.
  useEffect(() => {
    if (initialQuery && !autoSubmitted.current) {
      autoSubmitted.current = true;
      void ask(initialQuery);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialQuery]);

  return (
    <div style={{ maxWidth: 760, margin: "0 auto", padding: "var(--space-4)", display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "var(--space-2)" }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 22, display: "flex", alignItems: "center", gap: 8 }}>
            <span aria-hidden style={{ fontSize: 24 }}>🌊</span> {t("appName")}
          </h1>
          <p style={{ margin: 0, fontSize: 12, color: "var(--color-text-muted)" }}>{t("tagline")}</p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
          <ConnectionBadge />
          <LanguageSwitcher />
        </div>
      </header>

      <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
        <LocationControl onLocation={setUserLocation} />
        <BoatClassSelector value={boatClass} onChange={handleBoatClassChange} />
      </div>

      <QueryBar onSubmit={ask} busy={busy} initialText={initialQuery} />

      {busy && (
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", color: "var(--color-text-muted)", fontSize: 13, padding: "var(--space-2) 0" }}>
          <span className="dhruva-spinner" aria-hidden />
          Routing to specialist agents…
        </div>
      )}

      {error && (
        <p role="alert" style={{ color: "var(--color-nogo)" }}>
          {error}
        </p>
      )}

      {response && !busy && (
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }} className="dhruva-fade-in">
          <div style={{ background: "var(--color-surface-raised)", borderRadius: "var(--radius-lg)", padding: "var(--space-4)", borderLeft: "3px solid var(--color-accent)" }}>
            <p style={{ margin: 0, fontSize: 18, lineHeight: 1.6, fontWeight: 500 }}>{response.narrative}</p>
          </div>

          {/* Render order is the safety contract: verdict, THEN everything
              else. Never reorder this list — a fisherman must see an active
              hazard before a favourable fishing zone, full stop. */}
          {response.verdict && <VerdictCard verdict={response.verdict} />}

          {map?.show && (
            <section style={{ background: "var(--color-surface-raised)", borderRadius: "var(--radius-lg)", padding: "var(--space-2)" }}>
              <MiniMap center={map.center} markers={map.markers} route={map.route} zoom={response.route ? 9 : 8} />
            </section>
          )}

          {response.conditions && <Readout conditions={response.conditions} />}
          {response.pfz.length > 0 && <PfzRow records={response.pfz} />}
          {response.boundaries.length > 0 && <BoundaryCountdown boundaries={response.boundaries} />}
          <CapsulePanel capsule={response.capsule} />

          {/* Everything past here is "how did the system work this out" —
              real, inspectable, but not ahead of the answer for the person
              who just wants to know if it's safe to go to sea. */}
          <TechnicalDetails>
            <AgentPipeline trace={response.trace} />
            <EvidencePanel response={response} />
          </TechnicalDetails>
        </div>
      )}

      <footer style={{ fontSize: 11, color: "var(--color-text-muted)", textAlign: "center", padding: "var(--space-3) 0" }}>
        {t("advisoryOnly")}
      </footer>
    </div>
  );
}
