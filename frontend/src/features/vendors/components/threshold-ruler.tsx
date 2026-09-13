import { TIER_META } from "../tokens";
import { TIER_TONE } from "./tier-tone";

/** Left to right, matching the score axis. */
const ORDER = ["low", "medium", "high", "critical"] as const;

/**
 * The tier scale: four solid bands drawn to the tenant's thresholds, each named
 * inside its own colour, with the score pinned above.
 *
 * A tier shown as a word is a verdict. Shown on the scale it is an argument:
 * the reader sees how close the score sits to the next line, which is the first
 * question a vendor owner asks when they disagree with the tier.
 *
 * Pass `score={null}` to show the scale on its own, before there is a score.
 */
export function ThresholdRuler({
  score,
  thresholds,
  effectiveTier,
  pointsToHigher,
  className,
}: {
  score: number | null;
  /** Lower bound per tier, from the tenant's policy. `low` has none. */
  thresholds: Record<string, number>;
  effectiveTier: string | null;
  pointsToHigher?: number | null;
  className?: string;
}) {
  const bands = ORDER.map((tier, index) => {
    const from = tier === "low" ? 0 : (thresholds[tier] ?? 0);
    const next = ORDER[index + 1];
    const to = next ? (thresholds[next] ?? 100) : 100;
    return { tier, from, width: Math.max(0, to - from) };
  });
  const marker = score === null ? null : Math.min(100, Math.max(0, score));
  const higher = effectiveTier
    ? ORDER[ORDER.indexOf(effectiveTier as (typeof ORDER)[number]) + 1]
    : undefined;

  return (
    <div className={className}>
      {/* The pin row is kept even without a score, so the bar does not jump
          when the first score arrives and lines up with charts beside it. */}
      <div className="relative mb-1 h-6" aria-hidden>
        {marker !== null ? (
          <span
            className="absolute bottom-0 flex -translate-x-1/2 flex-col items-center"
            style={{ left: `${marker}%` }}
          >
            <span className="tabular rounded-xs bg-surface-inverse px-1.5 py-1 text-caption font-bold leading-none text-text-inverse">
              {score}
            </span>
            <span className="size-0 border-x-[5px] border-t-[5px] border-x-transparent border-t-surface-inverse" />
          </span>
        ) : null}
      </div>

      <div
        className="flex h-8 gap-0.5 overflow-hidden rounded-md"
        role="img"
        aria-label={
          score === null
            ? `Tier scale: ${bands.map((b) => `${TIER_META[b.tier]?.label} from ${b.from}`).join(", ")}`
            : `Score ${score} of 100, ${TIER_META[effectiveTier ?? ""]?.label ?? "no"} tier`
        }
      >
        {bands.map((band) => (
          <span
            key={band.tier}
            className={`flex min-w-0 items-center justify-center px-1 ${TIER_TONE[band.tier].fill}`}
            style={{ width: `${band.width}%` }}
          >
            <span className="truncate text-caption font-bold text-white">
              {TIER_META[band.tier]?.label ?? band.tier}
            </span>
          </span>
        ))}
      </div>

      <div className="relative mt-1 h-4" aria-hidden>
        {bands.map((band, index) => (
          <span
            key={band.tier}
            className={`tabular absolute text-caption text-text-subtle ${index === 0 ? "" : "-translate-x-1/2"}`}
            style={{ left: `${band.from}%` }}
          >
            {band.from}
          </span>
        ))}
        <span className="tabular absolute right-0 text-caption text-text-subtle">100</span>
      </div>

      {pointsToHigher !== null && pointsToHigher !== undefined && higher ? (
        <p className="mt-1 text-caption text-text-subtle">
          <span className="tabular font-semibold text-text-primary">{pointsToHigher}</span> points
          below {TIER_META[higher]?.label}
        </p>
      ) : null}
    </div>
  );
}
