import { cn } from "@/lib/cn";
import type { StatusFamily } from "@/components/ui/status-pill";

/**
 * `strokeClass`/`dotClass`/`barClass` must be literal Tailwind classes (e.g.
 * "stroke-severity-critical") written at the call site — Tailwind's JIT scans
 * source text, so a class built by string interpolation at runtime would be
 * purged from the build.
 */
export type ChartSegment = {
  key: string;
  label: string;
  value: number;
  strokeClass: string;
  dotClass: string;
};

/**
 * The platform's six status families (see status-pill.tsx), in chart form.
 * Reuse this instead of inventing per-feature chart palettes — it's the same
 * six colors a StatusPill would use for the same state.
 */
export const FAMILY_CHART: Record<StatusFamily, { stroke: string; dot: string; bar: string }> = {
  success: { stroke: "stroke-status-success-base", dot: "bg-status-success-base", bar: "bg-status-success-base" },
  danger: { stroke: "stroke-status-danger-base", dot: "bg-status-danger-base", bar: "bg-status-danger-base" },
  warning: { stroke: "stroke-status-warning-base", dot: "bg-status-warning-base", bar: "bg-status-warning-base" },
  progress: { stroke: "stroke-status-progress-base", dot: "bg-status-progress-base", bar: "bg-status-progress-base" },
  pending: { stroke: "stroke-status-pending-base", dot: "bg-status-pending-base", bar: "bg-status-pending-base" },
  neutral: { stroke: "stroke-status-neutral-base", dot: "bg-status-neutral-base", bar: "bg-status-neutral-base" },
};

const GAP_PX = 3;

function pct(value: number, total: number): number {
  return total > 0 ? Math.round((value / total) * 100) : 0;
}

export function Donut({
  segments,
  size = 132,
  thickness = 18,
  centerValue,
  centerLabel,
  showPercent = true,
}: {
  segments: ChartSegment[];
  size?: number;
  thickness?: number;
  centerValue?: string | number;
  centerLabel?: string;
  /** Legend rows show "count (pct%)" — set false for a raw-count-only legend. */
  showPercent?: boolean;
}) {
  const total = segments.reduce((sum, s) => sum + s.value, 0);
  const r = (size - thickness) / 2;
  const c = 2 * Math.PI * r;
  const cx = size / 2;
  const cy = size / 2;

  let offset = 0;
  const arcs = segments
    .filter((s) => s.value > 0)
    .map((s) => {
      const frac = total ? s.value / total : 0;
      const len = Math.max(frac * c - GAP_PX, 0);
      const dashOffset = -offset;
      offset += frac * c;
      return { ...s, len, dashOffset };
    });

  return (
    <div className="flex items-center gap-6">
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        className="shrink-0"
        role="img"
        aria-label={centerLabel ?? "Distribution"}
      >
        <circle r={r} cx={cx} cy={cy} fill="none" strokeWidth={thickness} className="stroke-surface-sunken" />
        {arcs.map((a) => (
          <circle
            key={a.key}
            r={r}
            cx={cx}
            cy={cy}
            fill="none"
            strokeWidth={thickness}
            strokeDasharray={`${a.len} ${Math.max(c - a.len, 0)}`}
            strokeDashoffset={a.dashOffset}
            transform={`rotate(-90 ${cx} ${cy})`}
            className={a.strokeClass}
          />
        ))}
        {centerValue != null ? (
          <text
            x={cx}
            y={cy - 2}
            textAnchor="middle"
            dominantBaseline="middle"
            className="fill-text-primary font-display"
            style={{ fontSize: size * 0.24 }}
          >
            {centerValue}
          </text>
        ) : null}
        {centerLabel ? (
          <text
            x={cx}
            y={cy + size * 0.16}
            textAnchor="middle"
            dominantBaseline="middle"
            className="fill-text-subtle"
            style={{ fontSize: size * 0.08 }}
          >
            {centerLabel}
          </text>
        ) : null}
      </svg>
      <ul className="min-w-0 flex-1 space-y-1.5">
        {segments.map((s) => (
          <li key={s.key} className="flex items-center gap-2 text-body-sm">
            <span className={cn("size-2.5 shrink-0 rounded-full", s.dotClass)} aria-hidden />
            <span className="flex-1 truncate text-text-secondary">{s.label}</span>
            <span className="tabular font-semibold text-text-primary">
              {s.value}
              {showPercent ? <span className="ml-1 font-normal text-text-subtle">({pct(s.value, total)}%)</span> : null}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export type GaugeZone = { to: number; strokeClass: string; textClass: string };

/** Red / amber / green compliance bands — the default for any 0-100 "how
 *  healthy is this" gauge (SLA rate, hygiene score, ...). */
const DEFAULT_GAUGE_ZONES: GaugeZone[] = [
  { to: 50, strokeClass: "stroke-status-danger-base", textClass: "text-status-danger-text" },
  { to: 80, strokeClass: "stroke-status-warning-base", textClass: "text-status-warning-text" },
  { to: 100, strokeClass: "stroke-status-success-base", textClass: "text-status-success-text" },
];

const ZONE_GAP = 1.2;

export function Gauge({
  value,
  max = 100,
  size = 160,
  thickness = 14,
  zones = DEFAULT_GAUGE_ZONES,
  label,
  badge,
}: {
  value: number;
  max?: number;
  size?: number;
  thickness?: number;
  /** Fixed color bands (cumulative upper bound `to`, out of 100) the needle
   *  points into — a real speedometer, not a single-hue fill. */
  zones?: GaugeZone[];
  label?: string;
  badge?: { text: string; toneClass: string };
}) {
  const p = max > 0 ? Math.max(0, Math.min(100, (value / max) * 100)) : 0;
  const r = size / 2 - thickness;
  const cx = size / 2;
  const cy = size / 2;
  const height = size / 2 + thickness + 14;
  const d = `M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`;

  const needleAngle = (1 - p / 100) * Math.PI;
  const needleLen = r - thickness * 0.35;
  const needleX = cx + needleLen * Math.cos(needleAngle);
  const needleY = cy - needleLen * Math.sin(needleAngle);

  let from = 0;
  const zoneArcs = zones.map((z, i) => {
    const len = Math.max(z.to - from - (i < zones.length - 1 ? ZONE_GAP : 0), 0);
    const arc = { key: `${z.to}-${i}`, from, len, strokeClass: z.strokeClass };
    from = z.to;
    return arc;
  });
  const heroZone = zones.find((z) => p <= z.to) ?? zones[zones.length - 1];

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={height} viewBox={`0 0 ${size} ${height}`}>
        {zoneArcs.map((a) => (
          <path
            key={a.key}
            d={d}
            fill="none"
            strokeWidth={thickness}
            strokeLinecap="round"
            pathLength={100}
            strokeDasharray={`${a.len} ${100 - a.len}`}
            strokeDashoffset={-a.from}
            className={a.strokeClass}
          />
        ))}
        <line x1={cx} y1={cy} x2={needleX} y2={needleY} strokeWidth={2.5} strokeLinecap="round" className="stroke-text-primary" />
        <circle cx={cx} cy={cy} r={4} className="fill-text-primary" />
        <text x={cx - r} y={cy + 14} textAnchor="start" className="fill-text-faint" style={{ fontSize: 10 }}>
          0%
        </text>
        <text x={cx + r} y={cy + 14} textAnchor="end" className="fill-text-faint" style={{ fontSize: 10 }}>
          100%
        </text>
      </svg>
      <p className={cn("-mt-1 font-display text-heading-lg tabular", heroZone.textClass)}>{Math.round(p)}%</p>
      {label ? <p className="text-caption text-text-subtle">{label}</p> : null}
      {badge ? (
        <span className={cn("mt-2 rounded-full px-2.5 py-0.5 text-caption font-semibold", badge.toneClass)}>{badge.text}</span>
      ) : null}
    </div>
  );
}

export type BarListItem = {
  key: string;
  label: string;
  value: number;
  barClass: string;
};

/**
 * A ranked "label — count (pct%)" row with a thin fill bar underneath, used
 * for the reference's "By severity" / "By domain"-style metric breakdowns.
 * Percent is against `total` (defaults to the sum of all item values); pass a
 * separate `total` when the list is a subset of a larger population.
 */
export function BarList({ items, total }: { items: BarListItem[]; total?: number }) {
  if (items.length === 0) {
    return <p className="text-body-sm text-text-subtle">No data yet.</p>;
  }
  const sum = total ?? items.reduce((s, i) => s + i.value, 0);
  const max = Math.max(1, ...items.map((i) => i.value));
  return (
    <ul className="space-y-3">
      {items.map((item) => (
        <li key={item.key}>
          <div className="mb-1 flex items-baseline justify-between gap-2 text-body-sm">
            <span className="text-text-secondary">{item.label}</span>
            <span className="tabular font-semibold text-text-primary">
              {item.value}
              <span className="ml-1 font-normal text-text-subtle">({pct(item.value, sum)}%)</span>
            </span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-surface-sunken">
            <div className={cn("h-full rounded-full", item.barClass)} style={{ width: `${(item.value / max) * 100}%` }} />
          </div>
        </li>
      ))}
    </ul>
  );
}

/**
 * A plain ranked count list (no percent, no bar) — for panels like the
 * reference's raw-CVSS donut legend that intentionally shows counts only.
 */
export function RankedBars({ items }: { items: BarListItem[] }) {
  const max = Math.max(1, ...items.map((i) => i.value));
  return (
    <ul className="space-y-2.5">
      {items.map((item) => (
        <li key={item.key} className="flex items-center gap-3">
          <span className="w-28 shrink-0 truncate text-body-sm text-text-secondary">{item.label}</span>
          <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-surface-sunken">
            <div className={cn("h-full rounded-full", item.barClass)} style={{ width: `${(item.value / max) * 100}%` }} />
          </div>
          <span className="w-8 shrink-0 text-right tabular text-body-sm font-semibold text-text-primary">{item.value}</span>
        </li>
      ))}
    </ul>
  );
}
