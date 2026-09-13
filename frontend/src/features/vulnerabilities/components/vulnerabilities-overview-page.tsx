import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { BarList, Donut, ErrorState, FAMILY_CHART, Gauge, PageHeader, TabStrip, type BarListItem, type ChartSegment } from "@/components/ui";
import { cn } from "@/lib/cn";
import { describeError } from "@/lib/api/describe-error";
import { listAssetOptions, listVulnerabilities, vulnerabilityKpis, vulnerabilityThroughput } from "../api";
import { ALL_STATES, OPEN_STATES, STATE_FAMILY, STATE_META } from "../tokens";
import { vulnerabilityTabs } from "./vulnerability-tabs";

const PRIORITY_TEXT: Record<string, string> = {
  P1: "text-status-danger-text",
  P2: "text-status-warning-text",
  P3: "text-action-accent",
  P4: "text-text-subtle",
};

const SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"];

const SEVERITY_TONE: Record<string, { stroke: string; dot: string; text: string }> = {
  critical: { stroke: "stroke-severity-critical", dot: "bg-severity-critical", text: "text-severity-critical" },
  high: { stroke: "stroke-severity-high", dot: "bg-severity-high", text: "text-severity-high" },
  medium: { stroke: "stroke-severity-medium", dot: "bg-severity-medium", text: "text-severity-medium" },
  low: { stroke: "stroke-severity-low", dot: "bg-severity-low", text: "text-severity-low" },
  info: { stroke: "stroke-severity-info", dot: "bg-severity-info", text: "text-severity-info" },
};

/** Vulnerabilities don't carry a category of their own — this stands in for
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

function Panel({ title, children, action }: { title: string; children: React.ReactNode; action?: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-border bg-surface-primary p-5">
      <div className="mb-4 flex items-center justify-between gap-2">
        <h2 className="font-display text-title-sm text-text-primary">{title}</h2>
        {action}
      </div>
      {children}
    </div>
  );
}

function Stat({ label, value, tone }: { label: string; value: number | string; tone?: "success" | "warning" | "danger" }) {
  const toneClass =
    tone === "success" ? "text-status-success-text" : tone === "warning" ? "text-status-warning-text" : tone === "danger" ? "text-status-danger-text" : "text-text-primary";
  return (
    <div className="rounded-lg border border-border bg-surface-primary px-4 py-3.5">
      <p className="text-caption text-text-subtle">{label}</p>
      <p className={cn("mt-1 font-display text-heading-md tabular", toneClass)}>{value}</p>
    </div>
  );
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

  const severityTotal = SEVERITY_ORDER.reduce((sum, sev) => sum + (k?.open_by_severity[sev] ?? 0), 0);
  const severitySegments: ChartSegment[] = SEVERITY_ORDER.map((sev) => ({
    key: sev,
    label: sev.charAt(0).toUpperCase() + sev.slice(1),
    value: k?.open_by_severity[sev] ?? 0,
    strokeClass: SEVERITY_TONE[sev].stroke,
    dotClass: SEVERITY_TONE[sev].dot,
  }));

  const slaPct = openTotal > 0 ? ((openTotal - (k?.overdue ?? 0)) / openTotal) * 100 : 100;

  const all = allQuery.data ?? [];
  const open = all.filter((v) => OPEN_STATES.includes(v.state));

  // Per-severity SLA rate: real, computed by cross-referencing severity and
  // overdue on the same open finding — not derivable from the kpis endpoint,
  // whose severity and SLA-posture counts are two separate marginal totals.
  const slaRows = ["critical", "high", "medium", "low"].map((sev) => {
    const rows = open.filter((v) => v.severity === sev);
    const pct = rows.length ? Math.round(((rows.length - rows.filter((v) => v.overdue).length) / rows.length) * 100) : 100;
    return { sev, pct };
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
      <TabStrip label="Vulnerability sections" items={vulnerabilityTabs(k?.open_total)} />

      {/* KPI tiles */}
      <div className="mb-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Open findings" value={openTotal} />
        <Stat label="P1, act now" value={k?.open_by_priority.P1 ?? 0} tone="danger" />
        <Stat label="Overdue" value={k?.overdue ?? 0} tone="warning" />
        <Stat label="Known exploited" value={k?.kev_open ?? 0} tone={k?.kev_open ? "danger" : undefined} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="SLA compliance">
          <div className="flex flex-col items-center py-1">
            <Gauge
              value={slaPct}
              label="overall SLA rate"
              badge={k.overdue > 0 ? { text: `${k.overdue} overdue`, toneClass: "bg-status-danger-bg text-status-danger-text" } : undefined}
            />
          </div>
          <ul className="mt-4 space-y-2 border-t border-border pt-3">
            {slaRows.map((r) => (
              <li key={r.sev}>
                <div className="mb-1 flex items-center gap-2 text-body-sm">
                  <span className={cn("size-2.5 shrink-0 rounded-full", SEVERITY_TONE[r.sev].dot)} aria-hidden />
                  <span className="flex-1 capitalize text-text-secondary">{r.sev}</span>
                  <span className="tabular font-semibold text-text-primary">{r.pct}%</span>
                </div>
                <div className="h-1.5 overflow-hidden rounded-full bg-surface-sunken">
                  <div
                    className={cn(
                      "h-full rounded-full",
                      r.pct >= 80 ? "bg-status-success-base" : r.pct >= 50 ? "bg-status-warning-base" : "bg-status-danger-base",
                    )}
                    style={{ width: `${r.pct}%` }}
                  />
                </div>
              </li>
            ))}
          </ul>
        </Panel>

        <Panel title="Severity distribution">
          <Donut segments={severitySegments} centerValue={severityTotal} centerLabel="open" />
        </Panel>

        <Panel title="Status breakdown">
          {allQuery.isError ? (
            <p className="text-body-sm text-status-danger-text">{describeError(allQuery.error, "status breakdown").message}</p>
          ) : allQuery.isPending ? (
            <PanelLoading rows={6} />
          ) : statusItems.length > 0 ? (
            <BarList items={statusItems} />
          ) : (
            <p className="text-body-sm text-text-subtle">No findings recorded yet.</p>
          )}
        </Panel>

        <Panel title="Raw severity → priority">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="mb-2 text-caption font-semibold uppercase tracking-wide text-text-faint">Raw CVSS severity</p>
              <ul className="space-y-1.5">
                {["critical", "high", "medium", "low"].map((sev) => (
                  <li key={sev} className="flex items-center justify-between text-body-sm">
                    <span className={cn("font-semibold capitalize", SEVERITY_TONE[sev].text)}>{sev}</span>
                    <span className="tabular font-semibold text-text-primary">{k?.open_by_severity[sev] ?? 0}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <p className="mb-2 text-caption font-semibold uppercase tracking-wide text-text-faint">Risk-adjusted priority</p>
              <ul className="space-y-1.5">
                {["P1", "P2", "P3", "P4"].map((band) => (
                  <li key={band} className="flex items-center justify-between text-body-sm">
                    <span className={cn("font-semibold", PRIORITY_TEXT[band])}>{band}</span>
                    <span className="tabular font-semibold text-text-primary">{k?.open_by_priority[band] ?? 0}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
          <p className="mt-3 text-caption text-text-subtle">
            Priority weighs exploitability (KEV, EPSS, public exploits) on top of raw CVSS. A critical CVSS score does not automatically mean P1.
          </p>
        </Panel>

        <Panel title="By asset type">
          {assetOptQuery.isError || allQuery.isError ? (
            <p className="text-body-sm text-status-danger-text">{describeError(assetOptQuery.error ?? allQuery.error, "asset type breakdown").message}</p>
          ) : assetOptQuery.isPending || allQuery.isPending ? (
            <PanelLoading rows={4} />
          ) : byTypeItems.length > 0 ? (
            <BarList items={byTypeItems} />
          ) : (
            <p className="text-body-sm text-text-subtle">No open findings yet.</p>
          )}
        </Panel>

        <Panel
          title="Known exploited (KEV)"
          action={
            <Link to="/vulnerabilities?kev=1" className="text-caption font-semibold text-text-link">
              View →
            </Link>
          }
        >
          <div className="flex items-center gap-4">
            <span
              className={cn(
                "flex size-14 items-center justify-center rounded-lg font-display text-heading-md tabular",
                k?.kev_open ? "bg-status-danger-bg text-status-danger-text" : "bg-surface-hover text-text-subtle",
              )}
            >
              {k?.kev_open ?? 0}
            </span>
            <div>
              <p className="text-body-sm text-text-primary">open findings on CISA&rsquo;s KEV list</p>
              <p className="text-caption text-text-subtle">
                Exploited in the wild, prioritise regardless of CVSS.
              </p>
            </div>
          </div>
        </Panel>

        <Panel title="Remediation throughput (30 days)">
          {tpQuery.isError ? (
            <p className="text-body-sm text-status-danger-text">
              {describeError(tpQuery.error, "throughput summary").message}
            </p>
          ) : (
            <>
            <div className="grid grid-cols-2 gap-3">
              <Metric label="Closed" value={tp?.closed_30d ?? 0} />
              <Metric label="Opened" value={tp?.opened_30d ?? 0} />
              <Metric
                label="Median MTTR"
                value={tp?.median_mttr_days != null ? `${tp.median_mttr_days}d` : "No data"}
              />
              <Metric
                label="Net change"
                value={tp ? tp.opened_30d - tp.closed_30d : 0}
                tone={tp && tp.opened_30d > tp.closed_30d ? "text-status-danger-text" : "text-status-success-text"}
              />
            </div>
            <div className="mt-4 border-t border-border pt-3">
              <p className="mb-2 text-caption font-semibold text-text-subtle">Mean time-to-remediate</p>
              <dl className="space-y-1">
                {SEVERITY_ORDER.filter((s) => tp?.mttr_days_by_severity[s] != null).map((s) => (
                  <div key={s} className="flex justify-between text-body-sm">
                    <dt className="capitalize text-text-secondary">{s}</dt>
                    <dd className="tabular text-text-primary">{tp?.mttr_days_by_severity[s]}d</dd>
                  </div>
                ))}
                {SEVERITY_ORDER.every((s) => tp?.mttr_days_by_severity[s] == null) ? (
                  <p className="text-caption text-text-subtle">No closures in the window yet.</p>
                ) : null}
              </dl>
            </div>
            </>
          )}
        </Panel>
      </div>
    </div>
  );
}

function Metric({ label, value, tone }: { label: string; value: number | string; tone?: string }) {
  return (
    <div className="rounded-md border border-border px-3 py-2">
      <p className="text-caption text-text-subtle">{label}</p>
      <p className={cn("mt-0.5 font-display text-title-md tabular", tone ?? "text-text-primary")}>{value}</p>
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
          <div key={i} className="rounded-lg border border-border bg-surface-primary px-4 py-3.5">
            <div className="h-3 w-1/2 animate-pulse rounded-full bg-surface-sunken" />
            <div className="mt-2 h-6 w-1/3 animate-pulse rounded-md bg-surface-sunken" />
          </div>
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="rounded-lg border border-border bg-surface-primary p-5">
            <div className="mb-4 h-4 w-1/3 animate-pulse rounded-full bg-surface-sunken" />
            <PanelLoading rows={5} />
          </div>
        ))}
      </div>
    </div>
  );
}
