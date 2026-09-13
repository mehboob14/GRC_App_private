/**
 * One solid ramp for tier, shared by the badge, the scale, the donut and
 * anything else that paints a tier: green, amber, orange, red.
 *
 * It is the severity ramp the assets module already uses for criticality, so a
 * "High" reads the same colour whether it labels an asset or a vendor.
 *
 * Full literal class strings, because Tailwind purges interpolated ones.
 */
export const TIER_TONE: Record<string, { fill: string; stroke: string }> = {
  critical: { fill: "bg-severity-critical", stroke: "stroke-severity-critical" },
  high: { fill: "bg-severity-high", stroke: "stroke-severity-high" },
  medium: { fill: "bg-severity-medium", stroke: "stroke-severity-medium" },
  low: { fill: "bg-severity-low", stroke: "stroke-severity-low" },
};

/** Untiered is an absence, so it is the quietest grey on the page. */
export const UNTIERED_TONE = { fill: "bg-border-strong", stroke: "stroke-border-strong" };
