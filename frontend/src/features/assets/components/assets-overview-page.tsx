import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  BarList,
  ChartCard,
  Donut,
  ErrorState,
  FAMILY_CHART,
  Gauge,
  StatRow,
  StatTile,
  type BarListItem,
  type ChartSegment,
} from "@/components/ui";
import { describeError } from "@/lib/api/describe-error";
import { getFacets, getSummary } from "../api";
import { ASSET_STATUSES, ASSET_TYPES, CRITICALITY_TIERS, type CriticalityTier } from "../types";
import { ASSET_TYPE_META, ENVIRONMENT_LABEL, STATUS_META, TIER_META } from "../tokens";

/** Criticality reads as an intuitive hot to cool ramp (red, orange, amber,
 *  green), mirroring severity, so a critical asset is unmistakable at a glance. */
const TIER_TONE: Record<CriticalityTier | "unassessed", { stroke: string; dot: string }> = {
  critical: { stroke: "stroke-severity-critical", dot: "bg-severity-critical" },
  high: { stroke: "stroke-severity-high", dot: "bg-severity-high" },
  medium: { stroke: "stroke-severity-medium", dot: "bg-severity-medium" },
  low: { stroke: "stroke-severity-low", dot: "bg-severity-low" },
  unassessed: { stroke: "stroke-status-neutral-base", dot: "bg-status-neutral-base" },
};

export function AssetsOverviewPage() {
  const navigate = useNavigate();
  const query = useQuery({ queryKey: ["asset-summary"], queryFn: getSummary });
  const facetsQuery = useQuery({ queryKey: ["asset-facets"], queryFn: getFacets });
  const s = query.data;

  if (query.isError) {
    const e = describeError(query.error, "asset overview");
    return (
      <ErrorState
        title={e.title}
        description={e.message}
        referenceId={e.referenceId}
        onRetry={e.retryable ? () => void query.refetch() : undefined}
      />
    );
  }

  if (query.isPending || !s) {
    return <OverviewSkeleton />;
  }

  const tierSegments: ChartSegment[] = ([...CRITICALITY_TIERS, "unassessed"] as const).map((tier) => ({
    key: tier,
    label: tier === "unassessed" ? "Not assessed" : TIER_META[tier].label,
    value: s.by_tier[tier],
    strokeClass: TIER_TONE[tier].stroke,
    dotClass: TIER_TONE[tier].dot,
  }));

  const byTypeItems: BarListItem[] = ASSET_TYPES.map((t) => ({
    key: t,
    label: ASSET_TYPE_META[t].label,
    value: s.by_type.find((x) => x.type === t)?.count ?? 0,
    barClass: "bg-action-accent",
  })).filter((i) => i.value > 0);

  const lifecycleItems: BarListItem[] = ASSET_STATUSES.map((st) => ({
    key: st,
    label: STATUS_META[st].label,
    value: s.by_status[st],
    barClass: FAMILY_CHART[STATUS_META[st].family].bar,
  })).filter((i) => i.value > 0);

  const environmentItems: BarListItem[] | null = facetsQuery.data
    ? (Object.entries(facetsQuery.data.environment) as Array<[keyof typeof ENVIRONMENT_LABEL, number]>)
        .map(([env, count]) => ({ key: env, label: ENVIRONMENT_LABEL[env], value: count, barClass: "bg-action-accent" }))
        .filter((i) => i.value > 0)
        .sort((a, b) => b.value - a.value)
    : null;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatTile icon="box" label="Total assets" value={s.total} />
        <StatTile
          icon="alert"
          label="Critical"
          value={s.by_tier.critical}
          tone="danger"
          onClick={() => navigate("/assets?tier=critical")}
        />
        <StatTile icon="clock" label="Stale over 90 days" value={s.stale} tone="warning" />
        <StatTile icon="shield" label="Regulated data" value={s.regulated} tone="progress" />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <ChartCard title="Criticality">
          <Donut segments={tierSegments} centerValue={s.total} />
        </ChartCard>

        <ChartCard title="Inventory hygiene">
          <div className="flex flex-col items-center py-1">
            <Gauge
              value={s.hygiene_avg}
              label="of fields complete"
              badge={s.needs_cia > 0 ? { text: `${s.needs_cia} missing CIA`, toneClass: "bg-status-warning-bg text-status-warning-text" } : undefined}
            />
          </div>
        </ChartCard>

        <ChartCard title="Needs attention">
          <div className="-mx-2 space-y-1">
            <StatRow icon="alert" label="Missing a CIA rating" value={s.needs_cia} tone="warning" onClick={() => navigate("/assets?attention=1")} />
            <StatRow icon="clock" label="Not reviewed in 90 days" value={s.stale} tone="warning" onClick={() => navigate("/assets?attention=1")} />
            <StatRow icon="shield" label="Regulated data in scope" value={s.regulated} tone="progress" />
          </div>
        </ChartCard>

        <ChartCard title="Lifecycle">
          <BarList items={lifecycleItems} total={s.total} />
        </ChartCard>

        <ChartCard title="By type">
          <BarList items={byTypeItems} total={s.total} />
        </ChartCard>

        <ChartCard title="By environment">
          {environmentItems && environmentItems.length > 0 ? (
            <BarList items={environmentItems} />
          ) : (
            <p className="text-center text-body-sm text-text-subtle">No environment set on any asset yet.</p>
          )}
        </ChartCard>
      </div>
    </div>
  );
}

function OverviewSkeleton() {
  return (
    <div className="space-y-4" aria-busy="true">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="flex items-center gap-3.5 rounded-lg border border-border bg-surface-primary p-4">
            <div className="size-10 animate-pulse rounded-md bg-surface-sunken" />
            <div className="flex-1 space-y-2">
              <div className="h-5 w-1/3 animate-pulse rounded-md bg-surface-sunken" />
              <div className="h-3 w-1/2 animate-pulse rounded-full bg-surface-sunken" />
            </div>
          </div>
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="rounded-lg border border-border bg-surface-primary p-5">
            <div className="mx-auto mb-4 h-4 w-1/3 animate-pulse rounded-full bg-surface-sunken" />
            <ul className="space-y-3">
              {Array.from({ length: 4 }).map((__, j) => (
                <li key={j} className="space-y-1.5">
                  <div className="h-3 w-1/3 animate-pulse rounded-full bg-surface-sunken" />
                  <div className="h-1.5 w-full animate-pulse rounded-full bg-surface-sunken" />
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
