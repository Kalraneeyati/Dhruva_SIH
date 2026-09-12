import { useId, useState } from "react";

export interface SeriesPoint {
  label: string;
  value: number;
}

interface LineChartProps {
  title: string;
  unit: string;
  points: SeriesPoint[];
  /** Single-hue sequential ramp step, per dataviz skill: one series needs no
   * legend — the title names it — but still gets a real ink, never a random
   * CSS color. Validated against this app's dark surface (#081018). */
  color?: string;
}

const WIDTH = 480;
const HEIGHT = 180;
const PAD = { top: 16, right: 16, bottom: 28, left: 44 };

/** A minimal, dependency-free line chart: thin 2px line, a rounded end dot,
 * recessive gridlines, hover crosshair + tooltip (dataviz skill:
 * interaction.md — "ship a crosshair+tooltip on line/area by default"), and a
 * table-view toggle so the same data is available to a screen reader. */
export function LineChart({ title, unit, points, color = "#3987e5" }: LineChartProps) {
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);
  const [showTable, setShowTable] = useState(false);
  const gradientId = useId();

  if (points.length === 0) return null;

  const values = points.map((p) => p.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const plotW = WIDTH - PAD.left - PAD.right;
  const plotH = HEIGHT - PAD.top - PAD.bottom;

  const x = (i: number) => PAD.left + (i / Math.max(1, points.length - 1)) * plotW;
  const y = (v: number) => PAD.top + plotH - ((v - min) / span) * plotH;

  const linePath = points.map((p, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${y(p.value).toFixed(1)}`).join(" ");
  const areaPath = `${linePath} L ${x(points.length - 1).toFixed(1)} ${(PAD.top + plotH).toFixed(1)} L ${x(0).toFixed(1)} ${(PAD.top + plotH).toFixed(1)} Z`;

  const gridLines = 3;

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <h4 style={{ margin: "0 0 4px", fontSize: 13, color: "var(--color-text)" }}>
          {title} <span style={{ color: "var(--color-text-muted)", fontWeight: 400 }}>({unit})</span>
        </h4>
        <button
          type="button"
          onClick={() => setShowTable((s) => !s)}
          style={{ fontSize: 11, minHeight: 28, padding: "2px 8px", background: "none", border: "1px solid var(--color-border)", borderRadius: 6, color: "var(--color-text-muted)" }}
        >
          {showTable ? "Show chart" : "Show table"}
        </button>
      </div>

      {showTable ? (
        <table style={{ width: "100%", fontSize: 12, borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left", borderBottom: "1px solid var(--color-border)" }}>Date</th>
              <th style={{ textAlign: "right", borderBottom: "1px solid var(--color-border)" }}>{unit}</th>
            </tr>
          </thead>
          <tbody>
            {points.map((p) => (
              <tr key={p.label}>
                <td>{p.label}</td>
                <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{p.value.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <svg
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          role="img"
          aria-label={`${title}: ranges from ${min.toFixed(2)} to ${max.toFixed(2)} ${unit}`}
          style={{ width: "100%", height: "auto" }}
          onMouseLeave={() => setHoverIdx(null)}
        >
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.25} />
              <stop offset="100%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>

          {Array.from({ length: gridLines + 1 }, (_, i) => {
            const gy = PAD.top + (i / gridLines) * plotH;
            const value = max - (i / gridLines) * span;
            return (
              <g key={i}>
                <line x1={PAD.left} x2={WIDTH - PAD.right} y1={gy} y2={gy} stroke="var(--color-border)" strokeWidth={1} />
                <text x={PAD.left - 8} y={gy + 3} textAnchor="end" fontSize={9} fill="var(--color-text-muted)">
                  {value.toFixed(1)}
                </text>
              </g>
            );
          })}

          <path d={areaPath} fill={`url(#${gradientId})`} stroke="none" />
          <path d={linePath} fill="none" stroke={color} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />

          {points.map((p, i) => (
            <circle
              key={p.label}
              cx={x(i)}
              cy={y(p.value)}
              r={hoverIdx === i ? 5 : 3}
              fill={color}
              stroke="var(--color-surface-raised)"
              strokeWidth={1.5}
              onMouseEnter={() => setHoverIdx(i)}
            />
          ))}

          {/* Invisible wide hit targets — bigger than the 3px dot, per interaction.md. */}
          {points.map((p, i) => (
            <rect
              key={`hit-${p.label}`}
              x={x(i) - plotW / points.length / 2}
              y={PAD.top}
              width={plotW / points.length}
              height={plotH}
              fill="transparent"
              onMouseEnter={() => setHoverIdx(i)}
            />
          ))}

          {hoverIdx !== null && (
            <g>
              <line x1={x(hoverIdx)} x2={x(hoverIdx)} y1={PAD.top} y2={PAD.top + plotH} stroke="var(--color-text-muted)" strokeWidth={1} strokeDasharray="2,2" />
              <text x={x(hoverIdx)} y={PAD.top - 4} textAnchor="middle" fontSize={10} fill="var(--color-text)">
                {points[hoverIdx].value.toFixed(2)} {unit}
              </text>
            </g>
          )}

          {points.map(
            (p, i) =>
              (i === 0 || i === points.length - 1 || i === hoverIdx) && (
                <text key={`label-${p.label}`} x={x(i)} y={HEIGHT - 6} textAnchor="middle" fontSize={9} fill="var(--color-text-muted)">
                  {p.label}
                </text>
              ),
          )}
        </svg>
      )}
    </div>
  );
}
