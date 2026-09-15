import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  BarList,
  ChartCard,
  Donut,
  ErrorState,
  Gauge,
  Icon,
  Skeleton,
  StatRow,
  StatTile,
  StatusPill,
  type BarListItem,
  type ChartSegment,
  type IconName,
  type StatTone,
  type StatusFamily,
} from "@/components/ui";
import { describeError } from "@/lib/api/describe-error";
import { getSummary, listIntake } from "../api";
import { ATTENTION_META, fmtDate, GRADE_META, LIFECYCLE_META, TIER_META } from "../tokens";
import { TierBadge } from "./tier-badge";
import { TIER_TONE, UNTIERED_TONE } from "./tier-tone";

/**
 * The portfolio, before the table.
 *
 * Every number here comes from one `/vendors/summary` call and almost every
 * one of them is a link into the register with the matching filter applied, so
 * the picture is a way in rather than a poster.
 */

const SEVERITY_TONE: Record<string, { stroke: string; fill: string }> = {
  critical: { stroke: "stroke-severity-critical", fill: "bg-severity-critical" },
  high: { stroke: "stroke-severity-high", fill: "bg-severity-high" },
  medium: { stroke: "stroke-severity-medium", fill: "bg-severity-medium" },
  low: { stroke: "stroke-severity-low", fill: "bg-severity-low" },
};

const STATUS_BAR: Record<string, string> = {
  success: "bg-status-success-base",
  danger: "bg-status-danger-base",
  warning: "bg-status-warning-base",
  progress: "bg-status-progress-base",
  pending: "bg-status-pending-base",
  neutral: "bg-status-neutral-base",
};

/** Coverage runs the healthy way round: more is better, so green is the top band. */
const COVERAGE_ZONES = [
  { to: 60, strokeClass: "stroke-status-danger-base", textClass: "text-status-danger-text" },
  { to: 85, strokeClass: "stroke-status-warning-base", textClass: "text-status-warning-text" },
  { to: 100, strokeClass: "stroke-status-success-base", textClass: "text-status-success-text" },
];

const FAMILY_TONE: Record<StatusFamily, StatTone> = {
  success: "success",
  danger: "danger",
  warning: "warning",
  progress: "progress",
  pending: "progress",
  neutral: "neutral",
};

const ATTENTION_ICON: Record<string, IconName> = {
  flagged: "alert",
  reassessment_overdue: "clock",
  not_tiered: "gauge",
  awaiting_gate: "controls",
  on_hold: "clock",
  weak_grade: "bug",
  unowned: "users",
  reassessment_due: "clock",
  offboarding: "signout",
};

export function VendorsOverviewPage() {
  const query = useQuery({ queryKey: ["vendor-summary"], queryFn: getSummary });
  const intakeQuery = useQuery({
    queryKey: ["vendor-intake", "pending"],
    queryFn: () => listIntake("pending"),
  });

  if (query.isError) {
    const error = describeError(query.error, "vendor overview");
    return (
      <div>
        <ErrorState
          title={error.title}
          description={error.message}
          referenceId={error.referenceId}
          onRetry={error.retryable ? () => void query.refetch() : undefined}
        />
      </div>
    );
  }

  if (query.isLoading || !query.data) {
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-[4.75rem] w-full" />
          ))}
        </div>
        <div className="grid gap-4 lg:grid-cols-3">
          <Skeleton className="h-64 w-full" />
          <Skeleton className="h-64 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      </div>
    );
  }

  const s = query.data;
  const attention = new Map(s.attention.map((a) => [a.code, a.count]));
  const coveragePct =
    s.coverage_in_scope === 0
      ? 100
      : Math.round((s.coverage_current / s.coverage_in_scope) * 100);

  const tierSegments: ChartSegment[] = ["critical", "high", "medium", "low", "untiered"]
    .filter((tier) => (s.by_tier[tier] ?? 0) > 0)
    .map((tier) => ({
      key: tier,
      label: tier === "untiered" ? "Not tiered" : (TIER_META[tier]?.label ?? tier),
      value: s.by_tier[tier] ?? 0,
      strokeClass: (TIER_TONE[tier] ?? UNTIERED_TONE).stroke,
      dotClass: (TIER_TONE[tier] ?? UNTIERED_TONE).fill,
      to: tier === "untiered" ? "/vendors?attention=not_tiered" : `/vendors?tiers=${tier}`,
    }));

  const statusBars: BarListItem[] = Object.entries(s.by_status)
    .filter(([, n]) => n > 0)
    .sort((a, b) => b[1] - a[1])
    .map(([status, n]) => ({
      key: status,
      label: LIFECYCLE_META[status]?.label ?? status,
      value: n,
      barClass: STATUS_BAR[LIFECYCLE_META[status]?.family ?? "neutral"],
    }));

  const severitySegments: ChartSegment[] = ["critical", "high", "medium", "low"]
    .filter((sev) => (s.findings_by_severity[sev] ?? 0) > 0)
    .map((sev) => ({
      key: sev,
      label: sev.charAt(0).toUpperCase() + sev.slice(1),
      value: s.findings_by_severity[sev] ?? 0,
      strokeClass: SEVERITY_TONE[sev].stroke,
      dotClass: SEVERITY_TONE[sev].fill,
    }));

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatTile
          icon="gauge"
          label="Not tiered"
          value={attention.get("not_tiered") ?? 0}
          tone="warning"
          to="/vendors?attention=not_tiered"
        />
        <StatTile
          icon="users"
          label="No business owner"
          value={attention.get("unowned") ?? 0}
          tone="warning"
          to="/vendors?owner=unassigned"
        />
        <StatTile
          icon="clock"
          label="Reassessment overdue"
          value={attention.get("reassessment_overdue") ?? 0}
          tone="danger"
          to="/vendors?attention=reassessment_overdue"
        />
        <StatTile
          icon="alert"
          label="Critical findings"
          value={s.findings_by_severity.critical ?? 0}
          caption={s.findings_overdue > 0 ? `${s.findings_overdue} overdue` : undefined}
          tone="danger"
          to="/vendors/findings"
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <ChartCard title="Needs attention">
          {s.attention.length === 0 ? (
            <p className="flex items-center justify-center gap-2 py-6 text-body-md text-status-success-text">
              <Icon name="check" className="size-4 shrink-0" />
              All clear
            </p>
          ) : (
            <div className="-mx-2 space-y-1">
              {s.attention.map((a) => (
                <StatRow
                  key={a.code}
                  icon={ATTENTION_ICON[a.code] ?? "alert"}
                  label={a.label}
                  value={a.count}
                  tone={FAMILY_TONE[ATTENTION_META[a.code]?.family ?? "neutral"]}
                  to={`/vendors?attention=${a.code}`}
                />
              ))}
            </div>
          )}
        </ChartCard>

        <ChartCard title="Portfolio by tier">
          {tierSegments.length === 0 ? (
            <p className="py-6 text-center text-body-sm text-text-subtle">No vendors yet.</p>
          ) : (
            <Donut segments={tierSegments} size={152} thickness={16} centerValue={s.total} />
          )}
        </ChartCard>

        <ChartCard title="Assessment coverage">
          {s.coverage_in_scope === 0 ? (
            <p className="py-6 text-center text-body-sm text-text-subtle">No critical or high vendors yet.</p>
          ) : (
            <div className="flex flex-col items-center">
              <Gauge value={coveragePct} zones={COVERAGE_ZONES} label="In window" size={150} />
              <p className="mt-1 text-body-sm text-text-secondary">
                <span className="tabular font-semibold text-text-primary">
                  {s.coverage_current}/{s.coverage_in_scope}
                </span>{" "}
                critical and high
              </p>
              {s.coverage_in_scope - s.coverage_current > 0 ? (
                <Link
                  to="/vendors?attention=reassessment_overdue"
                  className="mt-1 inline-flex items-center gap-0.5 text-label-sm text-text-link"
                >
                  {s.coverage_in_scope - s.coverage_current} outside
                  <Icon name="chevr" className="size-4" />
                </Link>
              ) : null}
            </div>
          )}
        </ChartCard>

        <ChartCard
          title="Open findings"
          action={
            s.findings_open > 0 ? (
              <Link to="/vendors/findings" className="text-label-sm text-text-link">
                View all
              </Link>
            ) : null
          }
        >
          {severitySegments.length === 0 ? (
            <p className="flex items-center justify-center gap-2 py-6 text-body-md text-status-success-text">
              <Icon name="check" className="size-4 shrink-0" />
              None open
            </p>
          ) : (
            <Donut segments={severitySegments} size={152} thickness={16} centerValue={s.findings_open} centerLabel="Open" />
          )}
        </ChartCard>

        <ChartCard title="By status">
          <BarList items={statusBars} total={s.total} />
        </ChartCard>

        <ChartCard
          title="Intake"
          action={
            <Link to="/vendors/intake" className="text-label-sm text-text-link">
              View all
            </Link>
          }
        >
          {s.intake_pending === 0 ? (
            <p className="py-6 text-center text-body-sm text-text-subtle">Nothing waiting.</p>
          ) : intakeQuery.isLoading ? (
            <Skeleton className="h-16 w-full" />
          ) : (
            <ul className="-my-1 divide-y divide-border">
              {(intakeQuery.data?.items ?? []).slice(0, 4).map((r) => (
                <li key={r.id} className="flex items-center justify-between gap-3 py-2">
                  <span className="min-w-0">
                    <span className="block truncate text-body-sm font-semibold text-text-primary">
                      {r.vendor_name}
                    </span>
                    <span className="block truncate text-caption text-text-subtle">
                      {[r.requested_by_name, fmtDate(r.created_at)].filter(Boolean).join(" · ")}
                    </span>
                  </span>
                  {r.screening_status === "flagged" ? (
                    <StatusPill status="warning" label="Duplicate?" kind="inline" />
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </ChartCard>

        <ChartCard
          title="Highest residual risk"
          className="lg:col-span-3"
          action={
            s.highest_residual.length > 0 ? (
              <Link to="/vendors" className="text-label-sm text-text-link">
                View register
              </Link>
            ) : null
          }
        >
          {s.highest_residual.length === 0 ? (
            <p className="py-6 text-center text-body-sm text-text-subtle">No scored assessments yet.</p>
          ) : (
            <ol className="-my-1 divide-y divide-border">
              {s.highest_residual.map((v) => (
                <li key={v.id}>
                  <Link
                    to={`/vendors/${v.id}`}
                    className="grid grid-cols-[minmax(0,1fr)_auto_minmax(6rem,14rem)_auto] items-center gap-4 rounded-sm py-2 transition-colors hover:bg-surface-hover focus-visible:outline focus-visible:outline-2 focus-visible:outline-action-accent"
                  >
                    <span className="truncate text-body-sm font-semibold text-text-primary">{v.name}</span>
                    <TierBadge tier={v.tier} />
                    <span className="flex items-center gap-2" aria-label={`Residual score ${Math.round(v.residual_score)} of 100`}>
                      <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-surface-sunken">
                        <span
                          className="block h-full rounded-full bg-status-danger-base"
                          style={{ width: `${Math.min(100, Math.max(0, v.residual_score))}%` }}
                        />
                      </span>
                      <span className="tabular w-8 text-right text-caption font-semibold text-text-secondary">
                        {Math.round(v.residual_score)}
                      </span>
                    </span>
                    {v.grade ? (
                      <StatusPill status={GRADE_META[v.grade]?.family ?? "neutral"} label={`Grade ${v.grade}`} kind="inline" />
                    ) : (
                      <span />
                    )}
                  </Link>
                </li>
              ))}
            </ol>
          )}
        </ChartCard>
      </div>
    </div>
  );
}
