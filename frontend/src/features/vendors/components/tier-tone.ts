/**
 * One solid ramp for tier, hottest first, shared by the badge, the ruler, the
 * donut and anything else that paints a tier.
 *
 * Tier is how much a vendor could hurt us, so it borrows the severity axis
 * rather than the six workflow families: the workflow families gave Medium a
 * violet that belonged to nothing. Low is slate, not green. A low tier vendor is
 * less exposed, not a good one.
 *
 * Full literal class strings, because Tailwind purges interpolated ones.
 */
export const TIER_TONE: Record<string, { fill: string; stroke: string }> = {
  critical: { fill: "bg-severity-critical", stroke: "stroke-severity-critical" },
  high: { fill: "bg-severity-high", stroke: "stroke-severity-high" },
  medium: { fill: "bg-severity-medium", stroke: "stroke-severity-medium" },
  low: { fill: "bg-status-neutral-base", stroke: "stroke-status-neutral-base" },
};

/** Untiered is an absence, so it is the quietest grey on the page. */
export const UNTIERED_TONE = { fill: "bg-border-strong", stroke: "stroke-border-strong" };
