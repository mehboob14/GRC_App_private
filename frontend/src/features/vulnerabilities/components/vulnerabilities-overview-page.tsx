import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  BarList,
  ChartCard,
  Donut,
  ErrorState,
  FAMILY_CHART,
  Gauge,
  PageHeader,
  StackedBars,
  StatTile,
  TabStrip,
  type BarListItem,
  type ChartSegment,
} from "@/components/ui";
import { describeError } from "@/lib/api/describe-error";
import { listAssetOptions, listVulnerabilities, vulnerabilityKpis, vulnerabilityThroughput } from "../api";
import { ALL_STATES, OPEN_STATES, STATE_FAMILY, STATE_META } from "../tokens";
import { vulnerabilityTabs } from "./vulnerability-tabs";

const PRIORITY_FILL: Record<string, string> = {
  P1: "bg-status-danger-base",
  P2: "bg-status-warning-base",
  P3: "bg-action-accent",
  P4: "bg-status-neutral-base",
};

const PRIORITY_BANDS = ["P1", "P2", "P3", "P4"];

const SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"];

const SEVERITY_TONE: Record<string, { stroke: string; dot: string; text: string }> = {
  critical: { stroke: "stroke-severity-critical", dot: "bg-severity-critical", text: "text-severity-critical" },
  high: { stroke: "stroke-severity-high", dot: "bg-severity-high", text: "text-severity-high" },
  medium: { stroke: "stroke-severity-medium", dot: "bg-severity-medium", text: "text-severity-medium" },
  low: { stroke: "stroke-severity-low", dot: "bg-severity-low", text: "text-severity-low" },
  info: { stroke: "stroke-severity-info", dot: "bg-severity-info", text: "text-severity-info" },
};

/** Vulnerabilities don't carry a category of their own: this stands in for
 *  "domain" by joining a finding's asset to that asset's type. Kept local
 *  (not imported from the assets feature) since no feature currently reaches
 *  into another feature's tokens. */
const ASSET_TYPE_LABEL: Record<string, string> = {
  application: "Application",
  infrastructure: "Infrastructure",
  data: "Data store",
  cloud: "Cloud resource",
  third_party: "Third party",
  business_service: "Business service",
};

function capitalize(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

export function VulnerabilitiesOverviewPage() {
  const kpisQuery = useQuery({ queryKey: ["vuln-kpis"], queryFn: vulnerabilityKpis });
  const tpQuery = useQuery({ queryKey: ["vuln-throughput"], queryFn: vulnerabilityThroughput });
  const allQuery = useQuery({ queryKey: ["vuln-all"], queryFn: () => listVulnerabilities({ state: "all" }) });
  const assetOptQuery = useQuery({ queryKey: ["vuln-asset-options"], queryFn: listAssetOptions });

  const k = kpisQuery.data;
  const tp = tpQuery.data;
  const openTotal = k?.open_total ?? 0;

  // The KPI query feeds most of the panels. Without it they would all read
  // zero, which says "nothing is open" when nothing actually loaded.
  if (kpisQuery.isError) {
    const e = describeError(kpisQuery.error, "vulnerability overview");
    return (
      <div className="w-full">
        <PageHeader eyebrow="Risk" title="Vulnerabilities" />
        <TabStrip label="Vulnerability sections" items={vulnerabilityTabs(k?.open_total)} />
        <ErrorState
          title={e.title}
          description={e.message}
          referenceId={e.referenceId}
          onRetry={e.retryable ? () => void kpisQuery.refetch() : undefined}
        />
      </div>
    );
  }

  // Until the KPI query resolves, every count is a placeholder zero and the
  // gauge would read a misleading 100%. Show a skeleton instead of fake data.
  if (kpisQuery.isPending || !k) {
    return (
      <div className="w-full">
        <PageHeader eyebrow="Risk" title="Vulnerabilities" />
        <TabStrip label="Vulnerability sections" items={vulnerabilityTabs(k?.open_total)} />
        <OverviewSkeleton />
      </div>
    );
  }

  const severityTotal = SEVERITY_ORDER.reduce((sum, sev) => sum + (k.open_by_severity[sev] ?? 0), 0);
  const severitySegments: ChartSegment[] = SEVERITY_ORDER.map((sev) => ({
    key: sev,
    label: capitalize(sev),
    value: k.open_by_severity[sev] ?? 0,
    strokeClass: SEVERITY_TONE[sev].stroke,
    dotClass: SEVERITY_TONE[sev].dot,
  }));

  const slaPct = openTotal > 0 ? ((openTotal - k.overdue) / openTotal) * 100 : 100;

  const all = allQuery.data ?? [];
  const open = all.filter((v) => OPEN_STATES.includes(v.state));

  // Per-severity SLA split: real, computed by cross-referencing severity and
  // overdue on the same open finding. Not derivable from the kpis endpoint,
  // whose severity and SLA-posture counts are two separate marginal totals.
  const slaColumns = ["critical", "high", "medium", "low"].map((sev) => {
    const rows = open.filter((v) => v.severity === sev);
    const overdue = rows.filter((v) => v.overdue).length;
    return { key: sev, label: capitalize(sev), values: { within: rows.length - overdue, overdue } };
  });

  const statusItems: BarListItem[] = allQuery.isSuccess
    ? ALL_STATES.map((st) => ({
        key: st,
        label: STATE_META[st].label,
        value: all.filter((v) => v.state === st).length,
        barClass: FAMILY_CHART[STATE_FAMILY[st]].bar,
      })).filter((i) => i.value > 0)
    : [];

  const assetTypeById = new Map((assetOptQuery.data ?? []).map((a) => [a.id, a.asset_type]));
  const typeCounts = new Map<string, number>();
  for (const v of open) {
    const t = assetTypeById.get(v.asset_id) ?? "unknown";
    typeCounts.set(t, (typeCounts.get(t) ?? 0) + 1);
  }
  const byTypeItems: BarListItem[] = [...typeCounts.entries()]
    .map(([type, count]) => ({ key: type, label: ASSET_TYPE_LABEL[type] ?? "Unknown type", value: count, barClass: "bg-action-accent" }))
    .sort((a, b) => b.value - a.value);

  return (
    <div className="w-full">
      <PageHeader eyebrow="Risk" title="Vulnerabilities" />
      <TabStrip label="Vulnerability sections" items={vulnerabilityTabs(k.open_total)} />

      <div className="mb-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatTile icon="bug" label="Open findings" value={openTotal} tone="progress" />
        <StatTile icon="alert" label="P1, act now" value={k.open_by_priority.P1 ?? 0} tone="danger" />
        <StatTile icon="clock" label="Overdue" value={k.overdue} tone="warning" />
        <StatTile icon="risk" label="Known exploited" value={k.kev_open} tone="danger" to="/vulnerabilities?kev=1" />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <ChartCard title="Severity distribution">
          <Donut segments={severitySegments} centerValue={severityTotal} centerLabel="Open" />
        </ChartCard>

        <ChartCard title="SLA compliance">
          <div className="flex flex-col items-center py-1">
            <Gauge
              value={slaPct}
              label="overall SLA rate"
              badge={k.overdue > 0 ? { text: `${k.overdue} overdue`, toneClass: "bg-status-danger-bg text-status-danger-text" } : undefined}
            />
          </div>
        </ChartCard>

        <ChartCard title="Priority">
          <StackedBars
            height={160}
            series={PRIORITY_BANDS.map((band) => ({ key: band, label: band, fillClass: PRIORITY_FILL[band] }))}
            columns={PRIORITY_BANDS.map((band) => ({ key: band, label: band, values: { [band]: k.open_by_priority[band] ?? 0 } }))}
          />
        </ChartCard>

        <ChartCard title="SLA by severity">
          {allQuery.isError ? (
            <p className="text-center text-body-sm text-status-danger-text">{describeError(allQuery.error, "SLA breakdown").message}</p>
          ) : allQuery.isPending ? (
            <PanelLoading rows={5} />
          ) : (
            <StackedBars
              series={[
                { key: "within", label: "Within SLA", fillClass: "bg-status-success-base" },
                { key: "overdue", label: "Overdue", fillClass: "bg-status-danger-base" },
              ]}
              columns={slaColumns}
            />
          )}
        </ChartCard>

        <ChartCard title="Status breakdown">
          {allQuery.isError ? (
            <p className="text-center text-body-sm text-status-danger-text">{describeError(allQuery.error, "status breakdown").message}</p>
          ) : allQuery.isPending ? (
            <PanelLoading rows={6} />
          ) : statusItems.length > 0 ? (
            <BarList items={statusItems} />
          ) : (
            <p className="text-center text-body-sm text-text-subtle">No findings recorded yet.</p>
          )}
        </ChartCard>

        <ChartCard title="By asset type">
          {assetOptQuery.isError || allQuery.isError ? (
            <p className="text-center text-body-sm text-status-danger-text">{describeError(assetOptQuery.error ?? allQuery.error, "asset type breakdown").message}</p>
          ) : assetOptQuery.isPending || allQuery.isPending ? (
            <PanelLoading rows={4} />
          ) : byTypeItems.length > 0 ? (
            <BarList items={byTypeItems} />
          ) : (
            <p className="text-center text-body-sm text-text-subtle">No open findings yet.</p>
          )}
        </ChartCard>

        <ChartCard
          title="Remediation, last 30 days"
          className="lg:col-span-3"
        >
          {tpQuery.isError ? (
            <p className="text-center text-body-sm text-status-danger-text">
              {describeError(tpQuery.error, "throughput summary").message}
            </p>
          ) : (
            <div className="grid gap-5 lg:grid-cols-[1fr_1fr]">
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-2">
                <StatTile icon="check" label="Closed" value={tp?.closed_30d ?? 0} tone="success" />
                <StatTile icon="plus" label="Opened" value={tp?.opened_30d ?? 0} tone="progress" />
                <StatTile
                  icon="clock"
                  label="Median time to fix"
                  value={tp?.median_mttr_days != null ? `${tp.median_mttr_days}d` : "No data"}
                />
                <StatTile
                  icon="activity"
                  label="Net change"
                  value={tp ? tp.opened_30d - tp.closed_30d : 0}
                  tone={tp && tp.opened_30d > tp.closed_30d ? "danger" : "success"}
                />
              </div>
              <div>
                <p className="mb-3 text-center text-body-sm text-text-secondary">Mean time to remediate, by severity</p>
                {SEVERITY_ORDER.every((s) => tp?.mttr_days_by_severity[s] == null) ? (
                  <p className="text-center text-caption text-text-subtle">No closures in the window yet.</p>
                ) : (
                  <StackedBars
                    height={140}
                    series={[{ key: "days", label: "Days", fillClass: "bg-action-accent" }]}
                    columns={SEVERITY_ORDER.filter((s) => tp?.mttr_days_by_severity[s] != null).map((s) => ({
                      key: s,
                      label: capitalize(s),
                      values: { days: tp?.mttr_days_by_severity[s] ?? 0 },
                    }))}
                  />
                )}
              </div>
            </div>
          )}
        </ChartCard>
      </div>

      <p className="mt-4 text-center text-caption text-text-subtle">
        Priority weighs exploitability (KEV, EPSS, public exploits) on top of raw CVSS.{" "}
        <Link to="/vulnerabilities?kev=1" className="font-semibold text-text-link">
          View known exploited
        </Link>
      </p>
    </div>
  );
}

function PanelLoading({ rows = 4 }: { rows?: number }) {
  return (
    <ul className="space-y-3" aria-busy="true">
      {Array.from({ length: rows }).map((_, i) => (
        <li key={i} className="space-y-1.5">
          <div className="h-3 w-1/3 animate-pulse rounded-full bg-surface-sunken" />
          <div className="h-1.5 w-full animate-pulse rounded-full bg-surface-sunken" />
        </li>
      ))}
    </ul>
  );
}

function OverviewSkeleton() {
  return (
    <div className="w-full" aria-busy="true">
      <div className="mb-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
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
            <PanelLoading rows={5} />
          </div>
        ))}
      </div>
    </div>
  );
}
