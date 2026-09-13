import { Link } from "react-router-dom";
import { SectionKicker } from "./ProblemSection";
import { EXAMPLE_QUERIES } from "../../shared/api/mock";
import type { QueryIntent } from "../../shared/types/domain";

const INTENT_ICON: Record<QueryIntent, string> = {
  nearest_pfz: "\u{1F41F}",
  safe_to_venture: "⚖",
  conditions_at_location: "\u{1F4CD}",
  hazard_alerts: "⚡",
  chlorophyll_sst_zones: "\u{1F32A}",
  safe_route: "\u{1F5FA}",
  productivity_decline: "\u{1F4C9}",
  geofence_avoidance: "\u{1F6A7}",
};

/**
 * The 8 official example queries from the ISRO brief, ARE the acceptance
 * test suite (IMPLEMENTATION.md: "if the prototype answers all 8 correctly,
 * with evidence, in more than one language, essentially every requirement in
 * the brief is met"). Surfacing them here, each a direct deep-link into a
 * pre-answered query, lets a judge verify the brief item-by-item without
 * typing anything.
 */
export function TrySection() {
  return (
    <section style={{ padding: "var(--space-6) var(--space-4)", maxWidth: 1000, margin: "0 auto" }}>
      <SectionKicker>The acceptance test</SectionKicker>
      <h2 style={{ fontSize: 28, margin: "0 0 var(--space-3)" }}>All 8 official queries. Try any of them.</h2>
      <p style={{ fontSize: 16, color: "var(--color-text-muted)", lineHeight: 1.7, maxWidth: 720, marginBottom: "var(--space-5)" }}>
        These are the exact example questions from the ISRO problem statement. Tap one — it opens the live app
        with that question already answered.
      </p>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "var(--space-3)" }}>
        {EXAMPLE_QUERIES.map((q, i) => (
          <Link
            key={q.intent}
            to={`/boat?q=${encodeURIComponent(q.text)}`}
            style={{
              display: "flex",
              gap: "var(--space-3)",
              alignItems: "flex-start",
              background: "var(--color-surface-raised)",
              borderRadius: "var(--radius-md)",
              padding: "var(--space-4)",
              textDecoration: "none",
              color: "var(--color-text)",
              border: "1px solid var(--color-border)",
              transition: "border-color 150ms ease, transform 150ms ease",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--color-accent)")}
            onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--color-border)")}
          >
            <span aria-hidden style={{ fontSize: 22 }}>
              {INTENT_ICON[q.intent]}
            </span>
            <span>
              <div style={{ fontSize: 11, color: "var(--color-text-muted)", marginBottom: 2 }}>Query {i + 1} of 8</div>
              <div style={{ fontSize: 14, lineHeight: 1.4 }}>{q.text}</div>
            </span>
          </Link>
        ))}
      </div>
    </section>
  );
}
