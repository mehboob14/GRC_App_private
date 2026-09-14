import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  BarList,
  ChartCard,
  Donut,
  ErrorState,
  Icon,
  SegmentedControl,
  Skeleton,
  StatTile,
  StatusPill,
  type BarListItem,
  type ChartSegment,
} from "@/components/ui";
import { describeError } from "@/lib/api/describe-error";
import { getSummary } from "../api";
import { BAND_TONE, STATUS_META, TREATMENT_META } from "../tokens";
import { BandLegend, Heatmap } from "./heatmap";
import { ScoreChip } from "./score";
import { useRisksOutlet } from "./risks-outlet";
import { SoonCard } from "./soon";

const TREATMENT_BAR: Record<string, string> = {
  mitigate: "bg-action-accent",
  accept: "bg-status-warning-base",
  avoid: "bg-status-danger-base",
  transfer: "bg-status-progress-base",
  undecided: "bg-status-neutral-base",
};

/** The register's picture before its table. Every number is a way in. */
export function RisksOverviewPage() {
  const navigate = useNavigate();
  const { register } = useRisksOutlet();
  const [view, setView] = useState<"residual" | "inherent">("residual");
  const query = useQuery({ queryKey: ["risk-summary", register.id], queryFn: () => getSummary(register.id) });

  if (query.isError) {
    const error = describeError(query.error, "risk overview");
    return <ErrorState title={error.title} description={error.message} onRetry={() => void query.refetch()} />;
  }
  if (!query.data) {
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-[4.75rem] w-full" />
          ))}
        </div>
        <div className="grid gap-4 lg:grid-cols-3">
          <Skeleton className="h-96 w-full lg:col-span-2" />
          <Skeleton className="h-96 w-full" />
        </div>
      </div>
    );
  }

  const s = query.data;
  const bands = register.severity_bands;
  const high = (s.by_band.critical ?? 0) + (s.by_band.high ?? 0);
  const grid = view === "residual" ? s.heatmap_residual : s.heatmap_inherent;
  const scored = grid.flat().reduce((a, b) => a + b, 0);

  const bandSegments: ChartSegment[] = [...bands]
    .reverse()
    .filter((b) => (s.by_band[b.key] ?? 0) > 0)
    .map((b) => ({
      key: b.key,
      label: b.label,
      value: s.by_band[b.key] ?? 0,
      strokeClass: BAND_TONE[b.key].stroke,
      dotClass: BAND_TONE[b.key].dot,
      to: `/risks?bands=${b.key}`,
    }));
  if (s.by_band.unscored) {
    bandSegments.push({
      key: "unscored",
      label: "Not scored",
      value: s.by_band.unscored,
      strokeClass: "stroke-status-neutral-base",
      dotClass: "bg-status-neutral-base",
      to: "/risks?bands=unscored",
    });
  }

  const treatmentBars: BarListItem[] = ["mitigate", "accept", "avoid", "transfer", "undecided"]
    .filter((t) => (s.by_treatment[t] ?? 0) > 0)
    .map((t) => ({
      key: t,
      label: t === "undecided" ? "Undecided" : TREATMENT_META[t as keyof typeof TREATMENT_META].label,
      value: s.by_treatment[t] ?? 0,
      barClass: TREATMENT_BAR[t],
    }));

  const categoryBars: BarListItem[] = s.by_category.slice(0, 6).map((c) => ({
    key: c.name,
    label: c.name,
    value: c.count,
    barClass: "bg-action-accent",
  }));

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <StatTile icon="risk" label="Open risks" value={s.total} tone="neutral" to="/risks" />
        <StatTile icon="alert" label="High and critical" value={high} tone="danger" to="/risks?bands=critical&bands=high" />
        <StatTile
          icon="controls"
          label="No linked control"
          value={s.attention.no_controls ?? 0}
          tone="danger"
          to="/risks?attention=no_controls"
        />
        <StatTile
          icon="clock"
          label="Review overdue"
          value={s.attention.review_overdue ?? 0}
          tone="warning"
          to="/risks?attention=review_overdue"
        />
        <StatTile
          icon="scales"
          label="Acceptances expiring"
          value={s.attention.acceptance_expiring ?? 0}
          caption={s.attention.acceptance_pending ? `${s.attention.acceptance_pending} awaiting approval` : undefined}
          tone="warning"
          to="/risks?attention=acceptance_expiring"
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <ChartCard
          title="Heatmap"
          className="lg:col-span-2"
          action={
            <SegmentedControl
              label="Heatmap view"
              value={view}
              onChange={setView}
              items={[
                { id: "residual", label: "Residual" },
                { id: "inherent", label: "Inherent" },
              ]}
            />
          }
        >
          <Heatmap
            grid={grid}
            likelihoodScale={register.likelihood_scale}
            impactScale={register.impact_scale}
            bands={bands}
            onCell={(l, i) => navigate(`/risks?cell=${view}:${l}:${i}`)}
          />
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
            <BandLegend bands={bands} />
            <span className="text-caption text-text-subtle">
              {scored} of {s.total} {view === "residual" ? "assessed after controls" : "scored"}
            </span>
          </div>
        </ChartCard>

        <ChartCard
          title="Top risks"
          action={
            <Link to="/risks" className="text-label-sm text-text-link">
              View all
            </Link>
          }
        >
          {s.top_risks.length === 0 ? (
            <p className="py-10 text-center text-body-sm text-text-subtle">Nothing scored yet.</p>
          ) : (
            <ul className="-my-1 divide-y divide-border">
              {s.top_risks.map((r) => (
                <li key={r.id}>
                  <Link to={`/risks/${r.id}`} className="flex items-center gap-3 py-2.5 hover:opacity-90">
                    <ScoreChip score={r.residual_score ?? r.inherent_score} bands={bands} />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-body-sm font-semibold text-text-primary">{r.title}</span>
                      <span className="block truncate text-caption text-text-subtle">
                        {r.code} · {r.category_name}
                      </span>
                    </span>
                    <StatusPill status={STATUS_META[r.status].family} label={STATUS_META[r.status].label} kind="inline" />
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </ChartCard>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <ChartCard title="By severity">
          {bandSegments.length === 0 ? (
            <p className="py-6 text-center text-body-sm text-text-subtle">No open risks.</p>
          ) : (
            <Donut segments={bandSegments} size={150} thickness={16} centerValue={s.total} centerLabel="Open" />
          )}
        </ChartCard>
        <ChartCard title="Treatment">
          {treatmentBars.length === 0 ? (
            <p className="py-6 text-center text-body-sm text-text-subtle">No open risks.</p>
          ) : (
            <BarList items={treatmentBars} total={s.total} />
          )}
        </ChartCard>
        <ChartCard title="By category">
          {categoryBars.length === 0 ? (
            <p className="py-6 text-center text-body-sm text-text-subtle">No open risks.</p>
          ) : (
            <BarList items={categoryBars} total={s.total} />
          )}
        </ChartCard>
      </div>

      <div>
        <p className="mb-2 flex items-center gap-2 text-label-md text-text-secondary">
          <Icon name="sparkle" className="size-4 text-text-subtle" />
          Coming to risk management
        </p>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <SoonCard icon="target" title="Risk appetite" text="Appetite and tolerance per category, with breaches flagged." />
          <SoonCard icon="trend" title="Key risk indicators" text="Thresholds and trends that alert before a risk lands." />
          <SoonCard icon="camera" title="Snapshots" text="Freeze the register and compare movement over time." />
          <SoonCard icon="pulse" title="Control monitoring" text="Failing linked controls raise the risk for review." />
        </div>
      </div>
    </div>
  );
}
