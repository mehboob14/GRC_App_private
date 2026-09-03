import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  BarList,
  Donut,
  ErrorState,
  FAMILY_CHART,
  Gauge,
  Icon,
  type BarListItem,
  type ChartSegment,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { describeError } from "@/lib/api/describe-error";
import { getFacets, getSummary } from "../api";
import { ASSET_STATUSES, ASSET_TYPES, CRITICALITY_TIERS, type CriticalityTier } from "../types";
import { ASSET_TYPE_META, ENVIRONMENT_LABEL, STATUS_META, TIER_META } from "../tokens";

/** Criticality reads as an intuitive hot→cool ramp (red→orange→amber→green),
 *  mirroring severity, so a critical asset is unmistakable at a glance. */
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
    <div className="space-y-5">
      {/* Stat tiles */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Total assets" value={s.total} />
        <Stat label="Critical" value={s.by_tier.critical} tone="danger" onClick={() => navigate("/assets?tier=critical")} />
        <Stat label="Stale > 90d" value={s.stale} tone="warning" />
        <Stat label="Regulated data" value={s.regulated} />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {/* Criticality distribution */}
        <Panel title="Criticality">
          <Donut segments={tierSegments} centerValue={s.total} centerLabel="assets" />
        </Panel>

        {/* Inventory hygiene */}
        <Panel title="Inventory hygiene">
          <div className="flex flex-col items-center py-1">
            <Gauge
              value={s.hygiene_avg}
              label="of fields complete"
              badge={s.needs_cia > 0 ? { text: `${s.needs_cia} missing CIA`, toneClass: "bg-status-warning-bg text-status-warning-text" } : undefined}
            />
          </div>
        </Panel>

        {/* Lifecycle */}
        <Panel title="Lifecycle">
          <BarList items={lifecycleItems} total={s.total} />
        </Panel>

        {/* By type */}
        <Panel title="By type">
          <BarList items={byTypeItems} total={s.total} />
        </Panel>

        {/* By environment */}
        <Panel title="By environment">
          {environmentItems && environmentItems.length > 0 ? (
            <BarList items={environmentItems} />
          ) : (
            <p className="text-body-sm text-text-subtle">No environment set on any asset yet.</p>
          )}
        </Panel>

        {/* Attention */}
        <Panel title="Needs attention">
          <ul className="space-y-2">
            <AttentionRow icon="alert" label="Missing a CIA rating" count={s.needs_cia} onClick={() => navigate("/assets?attention=1")} />
            <AttentionRow icon="clock" label="Stale (not reviewed in 90 days)" count={s.stale} onClick={() => navigate("/assets?attention=1")} />
            <AttentionRow icon="shield" label="Regulated data in scope" count={s.regulated} />
          </ul>
        </Panel>
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  tone,
  onClick,
}: {
  label: string;
  value: number | string;
  tone?: "success" | "warning" | "danger";
  onClick?: () => void;
}) {
  const toneClass =
    tone === "success" ? "text-status-success-text" : tone === "warning" ? "text-status-warning-text" : tone === "danger" ? "text-status-danger-text" : "text-text-primary";
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={!onClick}
      className={cn(
        "rounded-lg border border-border bg-surface-primary px-4 py-3.5 text-left",
        onClick ? "transition-colors hover:border-border-strong" : "cursor-default",
      )}
    >
      <p className="text-caption text-text-subtle">{label}</p>
      <p className={cn("mt-1 font-display text-heading-md tabular", toneClass)}>{value}</p>
    </button>
  );
}

function AttentionRow({ icon, label, count, onClick }: { icon: "alert" | "clock" | "shield"; label: string; count: number; onClick?: () => void }) {
  return (
    <li>
      <button
        type="button"
        onClick={onClick}
        disabled={!onClick}
        className={cn(
          "flex w-full items-center gap-2.5 rounded-sm px-1 py-1.5 text-left",
          onClick ? "hover:bg-surface-hover" : "cursor-default",
        )}
      >
        <Icon name={icon} className="size-4 text-text-subtle" />
        <span className="flex-1 text-body-sm text-text-secondary">{label}</span>
        <span className="tabular text-body-md font-semibold text-text-primary">{count}</span>
      </button>
    </li>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-border bg-surface-primary p-5">
      <h2 className="mb-4 font-display text-title-sm text-text-primary">{title}</h2>
      {children}
    </div>
  );
}

function OverviewSkeleton() {
  return (
    <div className="space-y-5" aria-busy="true">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="rounded-lg border border-border bg-surface-primary px-4 py-3.5">
            <div className="h-3 w-1/2 animate-pulse rounded-full bg-surface-sunken" />
            <div className="mt-2 h-6 w-1/3 animate-pulse rounded-md bg-surface-sunken" />
          </div>
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="rounded-lg border border-border bg-surface-primary p-5">
            <div className="mb-4 h-4 w-1/3 animate-pulse rounded-full bg-surface-sunken" />
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
