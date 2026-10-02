import { useId, type CSSProperties } from "react";
import { cn } from "@/lib/cn";

/**
 * Inline SVG charts. They animate only inside a [data-animate] ancestor that
 * has scrolled into view (motion.css); otherwise they render complete.
 */

export interface Segment {
  label: string;
  value: number;
  color: string;
}

export function Donut({ segments, size = 156, thickness = 20, total, caption, className }: { segments: Segment[]; size?: number; thickness?: number; total?: string; caption?: string; className?: string }) {
  const maskId = `donut-${useId().replace(/[^a-zA-Z0-9_-]/g, "")}`;
  const sum = segments.reduce((acc, s) => acc + s.value, 0);
  const r = (size - thickness) / 2;
  const c = 2 * Math.PI * r;
  const gap = segments.length > 1 ? 2.5 : 0;
  let offset = 0;
  return (
    <div className={cn("relative shrink-0", className)} style={{ width: size, height: size }}>
      <svg viewBox={`0 0 ${size} ${size}`} width={size} height={size} aria-hidden="true" className="-rotate-90">
        <mask id={maskId}>
          <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#fff" strokeWidth={thickness + 2} strokeDasharray={c} className="sweep" style={{ ["--len" as string]: c } as CSSProperties} />
        </mask>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#EEF1F5" strokeWidth={thickness} />
        <g mask={`url(#${maskId})`}>
          {segments.map((segment) => {
            const length = Math.max(0, (segment.value / sum) * c - gap);
            const node = <circle key={segment.label} cx={size / 2} cy={size / 2} r={r} fill="none" stroke={segment.color} strokeWidth={thickness} strokeDasharray={`${length} ${c - length}`} strokeDashoffset={-offset} />;
            offset += (segment.value / sum) * c;
            return node;
          })}
        </g>
      </svg>
      {(total || caption) && (
        <div className="absolute inset-0 grid place-content-center text-center">
          {caption && <span className="text-[11px] text-[#566072]">{caption}</span>}
          {total && <span className="font-serif text-[30px] leading-none text-[#0B0F17] tabular">{total}</span>}
        </div>
      )}
    </div>
  );
}

/** Horizontal stacked bar with gaps, as in "open issues by severity". */
export function StackedBar({ segments, height = 10, className }: { segments: Segment[]; height?: number; className?: string }) {
  const sum = segments.reduce((acc, s) => acc + s.value, 0);
  return (
    <div className={cn("flex w-full gap-1", className)} style={{ height }} aria-hidden="true">
      {segments.map((segment, index) => (
        <span key={segment.label} className="grow-x block h-full rounded-full" style={{ width: `${(segment.value / sum) * 100}%`, background: segment.color, ["--i" as string]: index } as CSSProperties} />
      ))}
    </div>
  );
}

/** Vertical stacked columns over time, as in the reference's cost trend. */
export function StackedColumns({ columns, series, max, height = 170, className, yTicks }: { columns: { label: string; values: number[]; highlight?: boolean }[]; series: { label: string; color: string }[]; max: number; height?: number; className?: string; yTicks?: number[] }) {
  return (
    <div className={cn("flex gap-3", className)} aria-hidden="true">
      {yTicks && (
        <div className="flex flex-col justify-between pb-5 text-right font-mono text-[10px] text-[#8A94A3]" style={{ height }}>
          {[...yTicks].reverse().map((tick) => <span key={tick} className="leading-none">{tick}</span>)}
        </div>
      )}
      <div className="relative flex flex-1 items-end justify-between gap-3" style={{ height }}>
        {yTicks && (
          <div className="pointer-events-none absolute inset-x-0 bottom-5 top-0 flex flex-col justify-between">
            {yTicks.map((tick) => <span key={tick} className="block border-t border-dashed border-[#E6E9EE]" />)}
          </div>
        )}
        {columns.map((column, ci) => {
          const total = column.values.reduce((a, b) => a + b, 0);
          return (
            <div key={column.label} className="relative z-[1] flex h-full flex-1 flex-col items-center justify-end gap-1.5">
              <div className="grow-y flex w-full max-w-[30px] flex-col-reverse overflow-hidden rounded-[3px]" style={{ height: `calc(${(total / max) * 100}% - 20px)`, ["--i" as string]: ci } as CSSProperties}>
                {column.values.map((value, si) => (
                  <span key={series[si].label} style={{ height: `${(value / total) * 100}%`, background: series[si].color }} className="block w-full border-t border-white/70 first:border-t-0" />
                ))}
              </div>
              <span className={cn("font-mono text-[10px] leading-none", column.highlight ? "font-semibold text-[#0B0F17]" : "text-[#8A94A3]")}>{column.label}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/** Simple vertical bars (priority counts etc.). */
export function Bars({ bars, max, height = 120, className }: { bars: { label: string; value: number; color: string }[]; max: number; height?: number; className?: string }) {
  return (
    <div className={cn("flex items-end justify-between gap-3", className)} style={{ height }} aria-hidden="true">
      {bars.map((bar, index) => (
        <div key={bar.label} className="flex h-full flex-1 flex-col items-center justify-end gap-1.5">
          <span className="font-mono text-[10.5px] font-semibold text-[#0B0F17]">{bar.value}</span>
          <span className="grow-y block w-full rounded-t-[4px]" style={{ height: `calc(${(bar.value / max) * 100}% - 34px)`, background: bar.color, ["--i" as string]: index } as CSSProperties} />
          <span className="font-mono text-[10px] text-[#8A94A3]">{bar.label}</span>
        </div>
      ))}
    </div>
  );
}

/** Semi-circular gauge. */
export function Gauge({ value, label, size = 150, className }: { value: number; label: string; size?: number; className?: string }) {
  const r = size / 2 - 12;
  const c = Math.PI * r;
  const length = (value / 100) * c;
  return (
    <div className={cn("relative", className)} style={{ width: size, height: size / 2 + 26 }}>
      <svg viewBox={`0 0 ${size} ${size / 2 + 8}`} width={size} height={size / 2 + 8} aria-hidden="true">
        <path d={`M 12 ${size / 2} A ${r} ${r} 0 0 1 ${size - 12} ${size / 2}`} fill="none" stroke="#EEF1F5" strokeWidth="14" strokeLinecap="round" />
        <path d={`M 12 ${size / 2} A ${r} ${r} 0 0 1 ${size - 12} ${size / 2}`} fill="none" stroke="#059669" strokeWidth="14" strokeLinecap="round" strokeDasharray={`${length} ${c}`} className="draw" style={{ ["--len" as string]: length } as CSSProperties} />
      </svg>
      <div className="absolute inset-x-0 bottom-0 text-center">
        <span className="block font-serif text-[28px] leading-none text-[#0B0F17]">{value}%</span>
        <span className="text-[11px] text-[#566072]">{label}</span>
      </div>
    </div>
  );
}
