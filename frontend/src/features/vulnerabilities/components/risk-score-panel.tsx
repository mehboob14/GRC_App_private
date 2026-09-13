import { Gauge, Icon } from "@/components/ui";
import { cn } from "@/lib/cn";
import type { AssetCriticality, RiskBreakdown } from "../types";

/**
 * How this finding's priority was reached.
 *
 * The model is not a flat sum, so this is not a flat bar chart. Three threat
 * signals add to a base out of 100; the asset's criticality and exposure then
 * *multiply* it; and two overrides can bind afterwards — the 100 cap and the
 * KEV floor. Showing only the bars would print a total that does not match the
 * score, which is exactly the arithmetic a reader cannot check. Every step is
 * on screen, in order, so the number is reproducible by eye.
 */

/** Risk runs the other way from readiness: high is bad, so the bands are
 *  inverted against the default gauge. The boundaries are the P-band
 *  thresholds in scoring.py, not decoration.
 *
 *  Every family here must exist in tokens.css — `status-info` does not, and an
 *  undefined CSS variable paints nothing, which showed as a hole in the arc. */
const RISK_ZONES = [
  { to: 25, strokeClass: "stroke-status-success-base", textClass: "text-status-success-text" },
  { to: 50, strokeClass: "stroke-status-progress-base", textClass: "text-status-progress-text" },
  { to: 75, strokeClass: "stroke-status-warning-base", textClass: "text-status-warning-text" },
  { to: 100, strokeClass: "stroke-status-danger-base", textClass: "text-status-danger-text" },
];

const BAND_NOTE: Record<string, string> = {
  P1: "Act now",
  P2: "Schedule this sprint",
  P3: "Plan it in",
  P4: "Track only",
};

export function RiskScorePanel({
  breakdown,
  asset,
  assetName,
}: {
  breakdown: RiskBreakdown;
  asset: AssetCriticality | null;
  assetName: string | null;
}) {
  return (
    <section className="rounded-lg border border-border bg-surface-primary p-5">
      <div className="flex flex-col gap-5 sm:flex-row sm:items-center">
        <div className="shrink-0 self-center">
          <Gauge value={breakdown.score} max={100} size={150} zones={RISK_ZONES} label="Risk score" unit="" />
        </div>

        <div className="min-w-0 flex-1">
          <div className="mb-1 flex flex-wrap items-baseline gap-2">
            <span className="font-display text-heading-md text-text-primary">
              {breakdown.band}
            </span>
            <span className="text-body-sm text-text-subtle">
              {BAND_NOTE[breakdown.band] ?? ""}
            </span>
          </div>
          <p className="text-body-sm text-text-secondary">{breakdown.reason}</p>

          {breakdown.kev_floor_applied ? (
            <p className="mt-2 flex items-start gap-2 rounded-md border border-status-danger-border bg-status-danger-bg px-3 py-2 text-caption text-status-danger-text">
              <Icon name="alert" className="mt-0.5 size-3.5 shrink-0" aria-hidden />
              <span>
                Known-exploited floor applied. The signals scored{" "}
                <strong className="tabular">{breakdown.adjusted_score}</strong>, but a CVE on
                CISA&rsquo;s catalogue is never below P1, so the score is held at 75.
              </span>
            </p>
          ) : null}
          {breakdown.capped ? (
            <p className="mt-2 text-caption text-text-subtle">
              Signals scored <span className="tabular">{breakdown.adjusted_score}</span>; the
              scale stops at 100.
            </p>
          ) : null}
        </div>
      </div>

      <div className="mt-5 border-t border-border pt-4">
        <div className="mb-2.5 flex items-baseline justify-between">
          <h3 className="type-overline text-text-subtle">How this was calculated</h3>
          <span className="text-caption text-text-subtle">
            Base <span className="tabular text-text-primary">{breakdown.base_score}</span> / 100
          </span>
        </div>

        <ul className="space-y-2.5">
          {breakdown.factors.map((factor) => {
            const pct = factor.max_points > 0 ? (factor.points / factor.max_points) * 100 : 0;
            return (
              <li key={factor.key} className="grid grid-cols-[minmax(9rem,13rem)_1fr_auto] items-center gap-3">
                <span className="min-w-0">
                  <span className="block truncate text-body-sm text-text-primary">
                    {factor.label}
                  </span>
                  <span className="block text-caption text-text-subtle">
                    {factor.detail}
                  </span>
                </span>
                <span
                  className="h-1.5 rounded-full bg-surface-sunken"
                  role="img"
                  aria-label={`${factor.points} of ${factor.max_points}`}
                >
                  <span
                    className="block h-1.5 rounded-full bg-action-accent"
                    style={{ width: `${Math.max(pct, factor.points > 0 ? 2 : 0)}%` }}
                  />
                </span>
                <span className="tabular text-caption text-text-secondary">
                  {factor.points} / {factor.max_points}
                </span>
              </li>
            );
          })}
        </ul>

        {/* The asset is a multiplier, not another bar — rendered as the step it
            actually is so the arithmetic on screen adds up. */}
        <div className="mt-3 flex flex-wrap items-baseline justify-between gap-2 border-t border-border pt-3">
          <span className="min-w-0">
            <span className="block text-body-sm text-text-primary">
              {assetName ? `On ${assetName}` : "Asset weighting"}
            </span>
            <span className="block text-caption text-text-subtle">{breakdown.asset_detail}</span>
          </span>
          <span className="tabular text-caption text-text-secondary">
            &times;{breakdown.asset_multiplier} &rarr;{" "}
            <span className="font-semibold text-text-primary">{breakdown.adjusted_score}</span>
          </span>
        </div>

        {asset ? <CiaRow asset={asset} /> : null}
      </div>
    </section>
  );
}

/** The asset's C/I/A ratings. Shown for context, and labelled as such: only the
 *  collapsed criticality tier and the two exposure flags actually move the
 *  score, so presenting C/I/A as an input would overstate their part. */
function CiaRow({ asset }: { asset: AssetCriticality }) {
  const values: Array<[string, number | null]> = [
    ["Confidentiality", asset.confidentiality],
    ["Integrity", asset.integrity],
    ["Availability", asset.availability],
  ];
  if (values.every(([, v]) => v === null)) return null;

  return (
    <div className="mt-3 border-t border-border pt-3">
      <p className="mb-2 type-overline text-text-subtle">
        Asset C/I/A: <span className="normal-case">context, not a score input</span>
      </p>
      <div className="flex flex-wrap gap-4">
        {values.map(([label, value]) => (
          <span key={label} className="flex items-center gap-2">
            <span className="text-caption text-text-subtle">{label}</span>
            <span className="flex gap-0.5" aria-label={value ? `${value} of 5` : "not assessed"}>
              {value === null ? (
                <span className="text-caption text-text-faint">Not assessed</span>
              ) : (
                [1, 2, 3, 4, 5].map((step) => (
                  <span
                    key={step}
                    className={cn(
                      "h-3 w-1.5 rounded-xs",
                      step <= value ? "bg-action-accent" : "bg-surface-sunken",
                    )}
                  />
                ))
              )}
            </span>
          </span>
        ))}
      </div>
    </div>
  );
}
