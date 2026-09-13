import { useState } from "react";
import type { ReactNode } from "react";

/**
 * Progressive disclosure: a fisherman needs the verdict, the map, and the
 * numbers — not "5 specialist agents" or "narration validated against
 * evidence." Those are real and worth showing (a judge, or a curious user,
 * should be able to inspect them), just not ahead of the answer. Collapsed
 * by default; one tap reveals the same AgentPipeline/EvidencePanel content
 * that used to sit inline in the default view.
 */
export function TechnicalDetails({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <section style={{ background: "var(--color-surface)", borderRadius: "var(--radius-lg)", overflow: "hidden" }}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        style={{
          width: "100%",
          textAlign: "left",
          background: "none",
          border: "none",
          color: "var(--color-text-muted)",
          padding: "var(--space-3) var(--space-4)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          fontSize: 13,
        }}
      >
        <span>🔧 How was this worked out?</span>
        <span aria-hidden style={{ transform: open ? "rotate(180deg)" : "none", transition: "transform 200ms ease" }}>
          ▾
        </span>
      </button>
      {open && (
        <div style={{ padding: "0 var(--space-4) var(--space-4)", display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
          {children}
        </div>
      )}
    </section>
  );
}
