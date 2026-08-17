import type { ReactNode } from "react";

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
          const node =
            seg.color === "transparent" ? null : (
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
