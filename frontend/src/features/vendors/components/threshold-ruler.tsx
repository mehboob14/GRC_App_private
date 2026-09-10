import { cn } from "@/lib/cn";
import { TIER_META } from "../tokens";

/** Worst first, matching the backend's `TIER_ORDER`. */
const ORDER = ["critical", "high", "medium", "low"] as const;

/** Full literal class strings — a class built by interpolation is purged. */
const BAND_FILL: Record<string, string> = {
  critical: "bg-status-danger-base",
  high: "bg-status-warning-base",
  medium: "bg-status-pending-base",
  low: "bg-status-neutral-base",
};

/**
 * The tier bands drawn to scale, with the score standing on them.
 *
 * A tier shown as a word is a verdict. Shown against the bands it is an
 * argument: the reader sees how close the score sits to the line, which is the
 * question a vendor owner asks first when they disagree with the tier.
 */
export function ThresholdRuler({
  score,
  thresholds,
  effectiveTier,
  pointsToHigher,
  pointsToLower,
  className,
}: {
  score: number;
  /** Lower bound per tier, from the tenant's policy. `low` has none. */
  thresholds: Record<string, number>;
  effectiveTier: string;
  pointsToHigher?: number | null;
  pointsToLower?: number | null;
  className?: string;
}) {
  // Bands run low → critical left to right, each sized by the gap between its
  // own lower bound and the next one up.
  const bounds = ORDER.map((tier) => ({ tier, from: thresholds[tier] ?? 0 }));
  const bands = [...bounds].reverse().map((band, index, all) => {
    const next = all[index + 1];
    const to = next ? next.from : 100;
    return { tier: band.tier, from: band.from, to, width: Math.max(0, to - band.from) };
  });

  const marker = Math.min(100, Math.max(0, score));

  return (
    <div className={className}>
      <div className="relative pt-6">
        <div
          className="absolute top-0 -translate-x-1/2 whitespace-nowrap"
          style={{ left: `${marker}%` }}
        >
          <span className="tabular rounded-2xs bg-surface-inverse px-1.5 py-0.5 text-caption font-semibold text-text-inverse">
            {score}
          </span>
        </div>
        <div
          className="flex h-2 w-full overflow-hidden rounded-full"
          role="img"
          aria-label={`Inherent score ${score} of 100, which is ${TIER_META[effectiveTier]?.label ?? effectiveTier} tier`}
        >
          {bands.map((band, index) => (
            <div
              key={band.tier}
              className={cn(
                BAND_FILL[band.tier],
                band.tier === effectiveTier ? "opacity-100" : "opacity-35",
                // A 2px surface gap so two bands never read as one.
                index > 0 && "ml-0.5",
              )}
              style={{ width: `${band.width}%` }}
            />
          ))}
        </div>
        <div
          className="absolute bottom-0 h-4 w-0.5 -translate-x-1/2 rounded-full bg-text-primary"
          style={{ left: `${marker}%` }}
          aria-hidden
        />
      </div>

      <div className="mt-2 flex justify-between">
        {bands.map((band) => (
          <span
            key={band.tier}
            className={cn(
              "text-caption",
              band.tier === effectiveTier
                ? "font-semibold text-text-primary"
                : "text-text-subtle",
            )}
          >
            {TIER_META[band.tier]?.label ?? band.tier}
            <span className="tabular ml-1 text-text-subtle">{band.from}+</span>
          </span>
        ))}
      </div>

      {pointsToHigher !== null && pointsToHigher !== undefined ? (
        <p className="mt-2 text-body-sm text-text-subtle">
          <span className="tabular font-semibold text-text-primary">{pointsToHigher}</span> more
          points would move this up a tier.
          {pointsToLower !== null && pointsToLower !== undefined ? (
            <>
              {" "}
              It is <span className="tabular font-semibold text-text-primary">{pointsToLower}</span>{" "}
              above the band below.
            </>
          ) : null}
        </p>
      ) : null}
    </div>
  );
}
