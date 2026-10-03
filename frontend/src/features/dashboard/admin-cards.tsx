import { Link } from "react-router-dom";
import { BarList, Donut, StatRow, type BarListItem, type ChartSegment } from "@/components/ui";
import { cn } from "@/lib/cn";
import { ProgressRing } from "./donut";
import { useAssets, usePolicies, usePosture, useRisks, useTasks, useVendors, useVulnerabilities } from "./hooks";
import { heatCells, pct, ringToneFor } from "./model";
import { Empty, FOCUS, Panel, ViewAll } from "./section";
import type { RiskPicture } from "./types";

/**
 * The module cards under the posture. Each one reads that module's own summary
 * endpoint, links into the module (using the filters its register already
 * reads), and says what to do when the module is still empty.
 */

// Literal class names throughout: Tailwind's JIT scans source text, so a class
// assembled at runtime would be purged from the build.

const SEVERITIES = [
  { key: "critical", label: "Critical", stroke: "stroke-severity-critical", dot: "bg-severity-critical" },
  { key: "high", label: "High", stroke: "stroke-severity-high", dot: "bg-severity-high" },
  { key: "medium", label: "Medium", stroke: "stroke-severity-medium", dot: "bg-severity-medium" },
  { key: "low", label: "Low", stroke: "stroke-severity-low", dot: "bg-severity-low" },
  { key: "info", label: "Info", stroke: "stroke-severity-info", dot: "bg-severity-info" },
] as const;

/** A risk band's cell: solid when it holds risks, a pale tint of the same hue when empty. */
const BAND: Record<string, { solid: string; tint: string }> = {
  low: { solid: "bg-severity-low text-white", tint: "bg-severity-low/15" },
  medium: { solid: "bg-severity-medium text-white", tint: "bg-severity-medium/15" },
  high: { solid: "bg-severity-high text-white", tint: "bg-severity-high/15" },
  critical: { solid: "bg-severity-critical text-white", tint: "bg-severity-critical/15" },
};

const BigNumber = ({ value, unit }: { value: string | number; unit: string }) => (
  <p className="text-center">
    <span className="font-display text-numeral-lg tabular text-text-primary">
      {typeof value === "number" ? value.toLocaleString() : value}
    </span>
    <span className="ml-1.5 text-body-sm text-text-subtle">{unit}</span>
  </p>
);

// -- vulnerabilities ----------------------------------------------------------

export function VulnerabilitiesCard() {
  const query = useVulnerabilities();
  return (
    <Panel
      title="Vulnerabilities"
      subject="vulnerability summary"
      query={query}
      action={<ViewAll to="/vulnerabilities/overview" label="Overview" describe="Vulnerabilities overview" />}
    >
      {(kpis) => {
        if (kpis.open_total === 0) {
          return (
            <Empty to="/vulnerabilities/import" cta="Import a scan">
              No open findings.
            </Empty>
          );
        }
        const segments: ChartSegment[] = SEVERITIES.map((s) => ({
          key: s.key,
          label: s.label,
          value: kpis.open_by_severity[s.key] ?? 0,
          strokeClass: s.stroke,
          dotClass: s.dot,
        })).filter((segment) => segment.value > 0);
        const flagged = (count: number) => (count > 0 ? "text-status-danger-text" : "text-text-subtle");
        return (
          <>
            <Donut segments={segments} size={150} thickness={16} centerValue={kpis.open_total} centerLabel="Open" />
            <p className="mt-3 text-center text-body-sm">
              <Link
                to="/vulnerabilities?kev=1"
                className={cn("rounded-2xs hover:underline", FOCUS, flagged(kpis.kev_open))}
              >
                {kpis.kev_open} known exploited
              </Link>
              <span className="text-text-subtle"> · </span>
              <Link
                to="/vulnerabilities?overdue=1"
                className={cn("rounded-2xs hover:underline", FOCUS, flagged(kpis.overdue))}
              >
                {kpis.overdue} past SLA
              </Link>
            </p>
          </>
        );
      }}
    </Panel>
  );
}

// -- evidence -----------------------------------------------------------------

/** Evidence freshness, read off the posture so it matches the Frameworks page. */
export function EvidenceCard() {
  const query = usePosture();
  return (
    <Panel title="Evidence" subject="evidence summary" query={query} action={<ViewAll to="/evidence" describe="All evidence" />}>
      {(p) => {
        if (p.evidence_total === 0) {
          return (
            <Empty to="/evidence" cta="Add evidence">
              No evidence yet.
            </Empty>
          );
        }
        const current = pct(p.evidence_fresh, p.evidence_total);
        const noExpiry = Math.max(p.evidence_total - p.evidence_fresh - p.evidence_aging - p.evidence_stale, 0);
        return (
          <div className="flex flex-col items-center gap-3">
            <ProgressRing
              percent={current}
              tone={ringToneFor(current)}
              size={132}
              stroke={16}
              label={`${p.evidence_fresh} current, ${p.evidence_aging} expiring within 30 days, ${p.evidence_stale} expired, ${noExpiry} with no expiry, of ${p.evidence_total} items`}
            >
              <span className="font-display text-numeral-md tabular text-text-primary">{current}%</span>
              <span className="text-caption text-text-subtle">current</span>
            </ProgressRing>
            <p className="text-center text-body-sm text-text-secondary">
              <span className="tabular font-semibold text-text-primary">{p.evidence_total}</span>{" "}
              {p.evidence_total === 1 ? "item" : "items"}
            </p>
            <p
              className={cn(
                "text-center text-body-sm",
                p.evidence_aging + p.evidence_stale > 0 ? "text-status-warning-text" : "text-text-subtle",
              )}
            >
              {p.evidence_aging} expiring · {p.evidence_stale} expired
            </p>
          </div>
        );
      }}
    </Panel>
  );
}

// -- risks --------------------------------------------------------------------

function RiskBody({ picture }: { picture: RiskPicture }) {
  const { register, summary } = picture;
  // Residual is what is left after treatment, so it leads once any risk has it.
  const residual = summary.heatmap_residual.flat().some((count) => count > 0);
  const { cols, cells } = heatCells(
    residual ? summary.heatmap_residual : summary.heatmap_inherent,
    register.severity_bands,
  );
  const bands = summary.by_band;
  const high = (bands.critical ?? 0) + (bands.high ?? 0);
  const legend = [
    { label: "High or critical", value: high, dot: "bg-severity-high" },
    { label: "Medium", value: bands.medium ?? 0, dot: "bg-severity-medium" },
    { label: "Low", value: bands.low ?? 0, dot: "bg-severity-low" },
    ...(bands.unscored ? [{ label: "Not scored", value: bands.unscored, dot: "bg-status-neutral-base" }] : []),
  ];
  const view = residual ? "Residual" : "Inherent";
  return (
    <>
      <div className="flex items-center justify-center gap-5">
        <div
          className="grid shrink-0 gap-1"
          style={{ gridTemplateColumns: `repeat(${cols}, auto)` }}
          role="img"
          aria-label={`${view} risk heatmap, likelihood by impact: ${high} high or critical, ${bands.medium ?? 0} medium, ${bands.low ?? 0} low`}
        >
          {cells.map((cell) => (
            <span
              key={cell.key}
              className={cn(
                "flex items-center justify-center rounded-xs text-caption font-semibold",
                cols > 5 ? "size-6" : "size-7",
                cell.count > 0 ? (BAND[cell.band] ?? BAND.low).solid : (BAND[cell.band] ?? BAND.low).tint,
              )}
            >
              {cell.count > 0 ? cell.count : ""}
            </span>
          ))}
        </div>
        <div>
          <p className="font-display text-numeral-lg tabular text-text-primary">{summary.total}</p>
          <p className="mb-2 text-caption text-text-subtle">active risks</p>
          <div className="space-y-1 text-body-sm">
            {legend.map((row) => (
              <div key={row.label} className="flex items-center gap-1.5">
                <span className={cn("h-2.5 w-4 shrink-0 rounded-2xs", row.dot)} />
                {row.label}
                <span className="tabular ml-auto pl-2 font-medium">{row.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
      <p className="mt-3 text-center text-caption text-text-subtle">
        {view} · Likelihood × impact{picture.registers > 1 ? ` · ${register.name}` : ""}
      </p>
    </>
  );
}

export function RiskCard() {
  const query = useRisks();
  return (
    <Panel title="Risk register" subject="risk summary" query={query} action={<ViewAll to="/risks/overview" label="Overview" describe="Risk overview" />}>
      {(picture) =>
        picture === null || picture.summary.total === 0 ? (
          <Empty to="/risks/library" cta="Start from the library">
            No risks yet.
          </Empty>
        ) : (
          <RiskBody picture={picture} />
        )
      }
    </Panel>
  );
}

export function TopRisksCard() {
  const query = useRisks();
  return (
    <Panel
      title="Top risks"
      subject="risk summary"
      query={query}
      className="lg:col-span-2"
      action={<ViewAll to="/risks" describe="All risks" />}
    >
      {(picture) => {
        const top = picture?.summary.top_risks ?? [];
        if (top.length === 0) {
          return (
            <Empty to="/risks" cta="Open the register">
              No scored risks yet.
            </Empty>
          );
        }
        return (
          <ul className="divide-y divide-border">
            {top.map((risk) => {
              const band = risk.residual_band ?? risk.inherent_band ?? "low";
              return (
                <li key={risk.id}>
                  <Link
                    to={`/risks/${risk.id}`}
                    className="flex items-center gap-2.5 rounded-sm py-2 transition-colors hover:bg-surface-hover focus-visible:outline focus-visible:outline-2 focus-visible:outline-action-accent"
                  >
                    <span
                      className={cn(
                        "flex size-8 shrink-0 items-center justify-center rounded-md font-display text-body-md font-bold",
                        (BAND[band] ?? BAND.low).solid,
                      )}
                    >
                      {risk.residual_score ?? risk.inherent_score}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-body-sm font-medium text-text-primary">{risk.title}</span>
                      <span className="block text-caption text-text-subtle">
                        {risk.code} · {risk.category_name}
                      </span>
                    </span>
                  </Link>
                </li>
              );
            })}
          </ul>
        );
      }}
    </Panel>
  );
}

// -- assets -------------------------------------------------------------------

const TIERS = [
  { key: "critical", label: "Critical", bar: "bg-severity-critical" },
  { key: "high", label: "High", bar: "bg-severity-high" },
  { key: "medium", label: "Medium", bar: "bg-severity-medium" },
  { key: "low", label: "Low", bar: "bg-severity-low" },
  { key: "unassessed", label: "Not assessed", bar: "bg-status-neutral-base" },
] as const;

export function AssetsCard() {
  const query = useAssets();
  return (
    <Panel title="Assets" subject="asset summary" query={query} action={<ViewAll to="/assets/overview" label="Overview" describe="Asset overview" />}>
      {(assets) => {
        if (assets.total === 0) {
          return (
            <Empty to="/assets/import" cta="Add or import assets">
              No assets yet.
            </Empty>
          );
        }
        const items: BarListItem[] = TIERS.map((tier) => ({
          key: tier.key,
          label: tier.label,
          value: assets.by_tier[tier.key] ?? 0,
          barClass: tier.bar,
        })).filter((item) => item.value > 0);
        return (
          <>
            <BigNumber value={assets.total} unit="in inventory" />
            <div className="mt-4">
              <BarList items={items} total={assets.total} />
            </div>
          </>
        );
      }}
    </Panel>
  );
}

// -- tasks --------------------------------------------------------------------

const PRIORITIES = [
  { key: "critical", label: "Critical", bar: "bg-status-danger-base" },
  { key: "high", label: "High", bar: "bg-status-warning-base" },
  { key: "medium", label: "Medium", bar: "bg-action-accent" },
  { key: "low", label: "Low", bar: "bg-status-neutral-base" },
] as const;

export function TasksCard() {
  const query = useTasks();
  return (
    <Panel title="Tasks" subject="task summary" query={query} action={<ViewAll to="/tasks/overview" label="Overview" describe="Task overview" />}>
      {(tasks) => {
        if (tasks.open_total === 0) {
          return (
            <Empty to="/tasks" cta="Open tasks">
              No open tasks.
            </Empty>
          );
        }
        const items: BarListItem[] = PRIORITIES.map((priority) => ({
          key: priority.key,
          label: priority.label,
          value: tasks.open_by_priority[priority.key] ?? 0,
          barClass: priority.bar,
        })).filter((item) => item.value > 0);
        return (
          <>
            <BigNumber value={tasks.open_total} unit="open" />
            <div className="-mx-2 mt-3 space-y-1">
              <StatRow icon="alert" label="Breaching SLA" value={tasks.breaching_now} tone="danger" to="/tasks?sla=breached" />
              <StatRow icon="clock" label="Due soon" value={tasks.due_soon} tone="warning" to="/tasks?sla=due_soon" />
            </div>
            <div className="mt-4">
              <BarList items={items} total={tasks.open_total} />
            </div>
          </>
        );
      }}
    </Panel>
  );
}

// -- vendors ------------------------------------------------------------------

export function VendorsCard() {
  const query = useVendors();
  return (
    <Panel title="Vendors" subject="vendor summary" query={query} action={<ViewAll to="/vendors/overview" label="Overview" describe="Vendor overview" />}>
      {(vendors) => {
        if (vendors.total === 0 && vendors.intake_pending === 0) {
          return (
            <Empty to="/vendors" cta="Add a vendor">
              No vendors yet.
            </Empty>
          );
        }
        const attention = new Map(vendors.attention.map((item) => [item.code, item.count]));
        return (
          <>
            <BigNumber value={vendors.total} unit={vendors.total === 1 ? "vendor" : "vendors"} />
            <div className="-mx-2 mt-3 space-y-1">
              <StatRow
                icon="gauge"
                label="Not tiered"
                value={attention.get("not_tiered") ?? 0}
                tone="warning"
                to="/vendors?attention=not_tiered"
              />
              <StatRow
                icon="clock"
                label="Reassessment overdue"
                value={attention.get("reassessment_overdue") ?? 0}
                tone="danger"
                to="/vendors?attention=reassessment_overdue"
              />
              <StatRow
                icon="alert"
                label="Open findings"
                value={vendors.findings_open}
                tone={vendors.critical_overdue > 0 ? "danger" : "warning"}
                to="/vendors/findings"
              />
              <StatRow
                icon="vendor"
                label="Intake waiting"
                value={vendors.intake_pending}
                tone="progress"
                to="/vendors/intake"
              />
            </div>
          </>
        );
      }}
    </Panel>
  );
}

// -- policies -----------------------------------------------------------------

export function PoliciesCard() {
  const query = usePolicies();
  return (
    <Panel title="Policies" subject="policy summary" query={query} action={<ViewAll to="/documents" describe="All policies" />}>
      {(policies) => {
        if (policies.total === 0) {
          return (
            <Empty to="/documents" cta="Start from a template">
              No policies yet.
            </Empty>
          );
        }
        return (
          <>
            <BigNumber value={`${policies.published}/${policies.total}`} unit="published" />
            <p
              className={cn(
                "mt-1 text-center text-body-sm",
                policies.renewalOverdue > 0 ? "text-status-warning-text" : "text-text-subtle",
              )}
            >
              {policies.renewalOverdue} {policies.renewalOverdue === 1 ? "renewal" : "renewals"} overdue
              {policies.needsApproval > 0 ? ` · ${policies.needsApproval} awaiting approval` : ""}
            </p>
            {policies.acknowledged !== null ? (
              <>
                <div className="mt-5 flex items-center justify-between text-body-sm">
                  <span className="text-text-secondary">Average acknowledged</span>
                  <span className="tabular font-semibold text-status-success-text">{policies.acknowledged}%</span>
                </div>
                <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-surface-sunken" aria-hidden>
                  <div
                    className="h-full rounded-full bg-status-success-base"
                    style={{ width: `${policies.acknowledged}%` }}
                  />
                </div>
              </>
            ) : null}
          </>
        );
      }}
    </Panel>
  );
}
