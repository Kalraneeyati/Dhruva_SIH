import { useState } from "react";

export interface AnomalyPoint {
  label: string;
  anomaly: number; // signed — positive = warmer/higher than baseline
}

const WIDTH = 480;
const HEIGHT = 180;
const PAD = { top: 16, right: 16, bottom: 28, left: 44 };

// Diverging blue<->red pair, validated (dataviz skill validator) against this
// app's dark surface #081018: worst adjacent normal-vision ΔE 29.0, CVD ΔE
// 19.2 — clear of both floors. Neutral midpoint uses this app's own border
// token rather than the skill's reference gray, since we render on a custom
// dark surface, not the skill's #1a1a19 reference surface.
const POSITIVE = "#e66767"; // warmer than baseline
const NEGATIVE = "#3987e5"; // cooler than baseline

/** Diverging bar chart for anomaly-vs-baseline data (dataviz skill: "Diverging
 * = two hues + a neutral gray midpoint"). Used for the marine-heatwave view,
 * where the sign of the anomaly is the entire point of the chart. */
export function DivergingBarChart({ title, unit, points }: { title: string; unit: string; points: AnomalyPoint[] }) {
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);
  if (points.length === 0) return null;

  const maxAbs = Math.max(...points.map((p) => Math.abs(p.anomaly)), 0.1);
  const plotW = WIDTH - PAD.left - PAD.right;
  const plotH = HEIGHT - PAD.top - PAD.bottom;
  const zeroY = PAD.top + plotH / 2;
  const barW = (plotW / points.length) * 0.6;

  const x = (i: number) => PAD.left + (i + 0.5) * (plotW / points.length);
  const barHeight = (v: number) => (Math.abs(v) / maxAbs) * (plotH / 2);

  return (
    <div>
      <h4 style={{ margin: "0 0 4px", fontSize: 13 }}>
        {title} <span style={{ color: "var(--color-text-muted)", fontWeight: 400 }}>({unit}, vs. seasonal baseline)</span>
      </h4>
      <div style={{ display: "flex", gap: 12, fontSize: 11, color: "var(--color-text-muted)", marginBottom: 4 }}>
        <span>
          <span style={{ display: "inline-block", width: 10, height: 10, background: POSITIVE, borderRadius: 2, marginRight: 4 }} />
          Warmer
        </span>
        <span>
          <span style={{ display: "inline-block", width: 10, height: 10, background: NEGATIVE, borderRadius: 2, marginRight: 4 }} />
          Cooler
        </span>
      </div>
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label={`${title}: values range from ${Math.min(...points.map((p) => p.anomaly)).toFixed(2)} to ${Math.max(...points.map((p) => p.anomaly)).toFixed(2)} ${unit}`} style={{ width: "100%", height: "auto" }} onMouseLeave={() => setHoverIdx(null)}>
        <line x1={PAD.left} x2={WIDTH - PAD.right} y1={zeroY} y2={zeroY} stroke="var(--color-border)" strokeWidth={1.5} />
        {points.map((p, i) => {
          const h = barHeight(p.anomaly);
          const isPositive = p.anomaly >= 0;
          const barY = isPositive ? zeroY - h : zeroY;
          return (
            <g key={p.label}>
              <rect
                x={x(i) - barW / 2}
                y={barY}
                width={barW}
                height={Math.max(h, 1)}
                rx={2}
                fill={isPositive ? POSITIVE : NEGATIVE}
                opacity={hoverIdx === null || hoverIdx === i ? 1 : 0.45}
                onMouseEnter={() => setHoverIdx(i)}
              />
              <rect x={x(i) - plotW / points.length / 2} y={PAD.top} width={plotW / points.length} height={plotH} fill="transparent" onMouseEnter={() => setHoverIdx(i)} />
            </g>
          );
        })}
        {hoverIdx !== null && (
          <text x={x(hoverIdx)} y={points[hoverIdx].anomaly >= 0 ? zeroY - barHeight(points[hoverIdx].anomaly) - 6 : zeroY + barHeight(points[hoverIdx].anomaly) + 14} textAnchor="middle" fontSize={10} fill="var(--color-text)">
            {points[hoverIdx].anomaly > 0 ? "+" : ""}
            {points[hoverIdx].anomaly.toFixed(2)}
          </text>
        )}
        {points.map(
          (p, i) =>
            (i === 0 || i === points.length - 1 || i === hoverIdx) && (
              <text key={`l-${p.label}`} x={x(i)} y={HEIGHT - 6} textAnchor="middle" fontSize={9} fill="var(--color-text-muted)">
                {p.label}
              </text>
            ),
        )}
      </svg>
    </div>
  );
}
