import type { ReactNode } from "react";
import { cn } from "@/lib/cn";
import type { RingTone } from "./model";

// Segmented SVG donut shared by the admin posture tiles and My Day. A single
// filled segment gets round caps; multi-segment rings butt together.
export function Donut({
  size = 128,
  stroke = 14,
  segments,
  children,
}: {
  size?: number;
  stroke?: number;
  segments: { value: number; color: string }[];
  children?: ReactNode;
}) {
  const radius = (size - stroke) / 2;
  const circ = 2 * Math.PI * radius;
  const total = segments.reduce((s, seg) => s + seg.value, 0) || 1;
  const filled = segments.filter((s) => s.color !== "transparent");
  let acc = 0;
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90" aria-hidden>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgb(var(--color-surface-sunken))"
          strokeWidth={stroke}
        />
        {segments.map((seg, i) => {
          const len = (seg.value / total) * circ;
          // A zero length arc with round caps still paints a dot, which read as
          // a stray mark on a ring at 0%. Draw nothing instead.
          const node =
            seg.color === "transparent" || seg.value <= 0 ? null : (
              <circle
                key={i}
                cx={size / 2}
                cy={size / 2}
                r={radius}
                fill="none"
                stroke={seg.color}
                strokeWidth={stroke}
                strokeDasharray={`${len} ${circ - len}`}
                strokeDashoffset={-acc}
                strokeLinecap={filled.length === 1 ? "round" : "butt"}
              />
            );
          acc += len;
          return node;
        })}
      </svg>
      {children ? (
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center leading-none">
          {children}
        </div>
      ) : null}
    </div>
  );
}

// The ring paints an SVG stroke, so its colour arrives as `currentColor` from a
// literal Tailwind `text-*` class on the wrapper. Tailwind's JIT scans source
// text, so a class assembled at runtime would be purged from the build.
const RING_TONE: Record<RingTone | "accent", string> = {
  accent: "text-action-accent",
  success: "text-status-success-base",
  warning: "text-status-warning-base",
  danger: "text-status-danger-base",
};

/**
 * One value out of a hundred as a ring, with what it counts written out in
 * `label` for anyone who cannot see the arc. The centre carries the figure.
 */
export function ProgressRing({
  percent,
  tone,
  label,
  size = 132,
  stroke = 14,
  children,
}: {
  percent: number;
  tone: RingTone | "accent";
  label: string;
  size?: number;
  stroke?: number;
  children?: ReactNode;
}) {
  const value = Math.min(100, Math.max(0, percent));
  return (
    <div className={cn("shrink-0", RING_TONE[tone])} role="img" aria-label={label}>
      <Donut
        size={size}
        stroke={stroke}
        segments={[
          { value, color: "currentColor" },
          { value: 100 - value, color: "transparent" },
        ]}
      >
        {children}
      </Donut>
    </div>
  );
}
