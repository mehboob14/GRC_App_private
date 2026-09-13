import { cn } from "@/lib/cn";
import { TIER_META } from "../tokens";
import { TIER_TONE } from "./tier-tone";

/** Left to right, matching the score axis. */
const ORDER = ["low", "medium", "high", "critical"] as const;

/**
 * The tier bands drawn to scale, with the score standing on them.
 *
 * A tier shown as a word is a verdict. Shown against the bands it is an
 * argument: the reader sees how close the score sits to the line, which is the
 * first question a vendor owner asks when they disagree with the tier.
 *
 * Every band is solid. Fading the bands the score is not in made the ramp read
 * as washed out rather than as four distinct levels.
 */
export function ThresholdRuler({
  score,
  thresholds,
  effectiveTier,
  pointsToHigher,
  hideScore = false,
  className,
}: {
  score: number;
  /** Lower bound per tier, from the tenant's policy. `low` has none. */
  thresholds: Record<string, number>;
  effectiveTier: string;
  pointsToHigher?: number | null;
  /** Drop the score chip where the number is already shown large beside it. */
  hideScore?: boolean;
  className?: string;
}) {
  const bands = ORDER.map((tier, index) => {
    const from = tier === "low" ? 0 : (thresholds[tier] ?? 0);
    const next = ORDER[index + 1];
    const to = next ? (thresholds[next] ?? 100) : 100;
    return { tier, from, width: Math.max(0, to - from) };
  });
  const marker = Math.min(100, Math.max(0, score));
  const higher = ORDER[ORDER.indexOf(effectiveTier as (typeof ORDER)[number]) + 1];

  return (
    <div className={className}>
      <div className={cn("relative", hideScore ? "pt-2" : "pt-7")}>
        <span
          hidden={hideScore}
          className="tabular absolute top-0 -translate-x-1/2 rounded-xs bg-surface-inverse px-1.5 py-0.5 text-caption font-bold text-text-inverse"
          style={{ left: `${marker}%` }}
        >
          {score}
        </span>
        <div
          className="flex h-2.5 gap-0.5"
          role="img"
          aria-label={`Score ${score} of 100, ${TIER_META[effectiveTier]?.label ?? effectiveTier} tier`}
        >
          {bands.map((band) => (
            <span
              key={band.tier}
              className={cn("h-full first:rounded-l-full last:rounded-r-full", TIER_TONE[band.tier].fill)}
              style={{ width: `${band.width}%` }}
            />
          ))}
        </div>
        <span
          className="absolute bottom-[-3px] h-4 w-1 -translate-x-1/2 rounded-full bg-text-primary ring-2 ring-surface-primary"
          style={{ left: `${marker}%` }}
          aria-hidden
        />
      </div>

      <div className="mt-2 flex gap-0.5">
        {bands.map((band) => (
          <span key={band.tier} className="min-w-0" style={{ width: `${band.width}%` }}>
            <span
              className={cn(
                "block truncate text-caption",
                band.tier === effectiveTier ? "font-bold text-text-primary" : "text-text-subtle",
              )}
            >
              {TIER_META[band.tier]?.label ?? band.tier}
            </span>
            <span className="tabular block text-caption text-text-faint">{band.from}</span>
          </span>
        ))}
      </div>

      {pointsToHigher !== null && pointsToHigher !== undefined && higher ? (
        <p className="mt-2 text-caption text-text-subtle">
          <span className="tabular font-semibold text-text-primary">{pointsToHigher}</span> points
          below {TIER_META[higher]?.label}
        </p>
      ) : null}
    </div>
  );
}
