import { Link, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  BarList,
  Donut,
  ErrorState,
  Gauge,
  Icon,
  Skeleton,
  StatusPill,
  type BarListItem,
  type ChartSegment,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { describeError } from "@/lib/api/describe-error";
import { getSummary, listIntake } from "../api";
import { ATTENTION_META, fmtDate, LIFECYCLE_META, TIER_META } from "../tokens";
import { Panel } from "./panel";
import { TIER_TONE, UNTIERED_TONE } from "./tier-tone";

/**
 * The portfolio, before the table.
 *
 * The module used to open on page one of a spreadsheet, so "how many are
 * untiered", "how many reassessments are overdue" and "what share of our
 * critical vendors have a current assessment" were answerable only by paging and
 * counting by eye. Every number here comes from one `/vendors/summary` call and
 * every one of them is a link into the register with the matching filter
 * applied, so the picture is a way in rather than a poster.
 */

const SEVERITY_BAR: Record<string, string> = {
  critical: "bg-severity-critical",
  high: "bg-severity-high",
  medium: "bg-severity-medium",
  low: "bg-severity-low",
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

export function VendorsOverviewPage() {
  const query = useQuery({ queryKey: ["vendor-summary"], queryFn: getSummary });
  const intakeQuery = useQuery({
    queryKey: ["vendor-intake", "pending"],
    queryFn: () => listIntake("pending"),
  });

  if (query.isError) {
    const error = describeError(query.error, "vendor overview");
    return (
      <div className="mt-4">
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
      <div className="mt-4 space-y-4">
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-[5.5rem] w-full" />
          ))}
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
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

  const severityBars: BarListItem[] = ["critical", "high", "medium", "low"]
    .filter((sev) => (s.findings_by_severity[sev] ?? 0) > 0)
    .map((sev) => ({
      key: sev,
      label: sev.charAt(0).toUpperCase() + sev.slice(1),
      value: s.findings_by_severity[sev] ?? 0,
      barClass: SEVERITY_BAR[sev],
    }));

  return (
    <div className="mt-4 space-y-4">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat
          label="Not tiered"
          value={attention.get("not_tiered") ?? 0}
          tone="warning"
          to="/vendors?attention=not_tiered"
        />
        <Stat
          label="No business owner"
          value={attention.get("unowned") ?? 0}
          tone="warning"
          to="/vendors?owner=unassigned"
        />
        <Stat
          label="Reassessment overdue"
          value={attention.get("reassessment_overdue") ?? 0}
          tone="danger"
          to="/vendors?attention=reassessment_overdue"
        />
        <Stat
          label="Critical findings"
          value={s.findings_by_severity.critical ?? 0}
          caption={s.findings_overdue > 0 ? `${s.findings_overdue} overdue` : undefined}
          tone="danger"
          to="/vendors/findings"
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Panel title="Needs attention">
          {s.attention.length === 0 ? (
            <p className="flex items-center gap-2 text-body-md text-status-success-text">
              <Icon name="check" className="size-4 shrink-0" />
              All clear
            </p>
          ) : (
            <ul className="-my-1 divide-y divide-border">
              {s.attention.map((a) => (
                <li key={a.code}>
                  <Link
                    to={`/vendors?attention=${a.code}`}
                    className="-mx-2 flex items-center justify-between gap-3 rounded-sm px-2 py-2 transition-colors duration-80 ease-state hover:bg-surface-hover"
                  >
                    <StatusPill
                      status={ATTENTION_META[a.code]?.family ?? "neutral"}
                      label={a.label}
                      kind="inline"
                    />
                    <span className="flex shrink-0 items-center gap-1.5">
                      <span className="tabular text-body-md font-semibold text-text-primary">
                        {a.count}
                      </span>
                      <Icon name="chevr" className="size-4 text-text-subtle" />
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel title="Coverage">
          {s.coverage_in_scope === 0 ? (
            <p className="text-body-sm text-text-subtle">No critical or high vendors yet.</p>
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
        </Panel>

        <Panel title="By tier">
          {tierSegments.length === 0 ? (
            <p className="text-body-sm text-text-subtle">No vendors yet.</p>
          ) : (
            <Donut
              segments={tierSegments}
              size={112}
              thickness={12}
              centerValue={s.total}
              centerLabel={s.total === 1 ? "vendor" : "vendors"}
              showPercent={false}
            />
          )}
        </Panel>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Panel title="By status">
          <BarList items={statusBars} total={s.total} />
        </Panel>

        <Panel
          title="Open findings"
          count={s.findings_open || undefined}
          action={
            s.findings_open > 0 ? (
              <Link to="/vendors/findings" className="text-label-sm text-text-link">
                View all
              </Link>
            ) : null
          }
        >
          {severityBars.length === 0 ? (
            <p className="flex items-center gap-2 text-body-md text-status-success-text">
              <Icon name="check" className="size-4 shrink-0" />
              None open
            </p>
          ) : (
            <BarList items={severityBars} total={s.findings_open} />
          )}
        </Panel>

        <Panel
          title="Intake"
          count={s.intake_pending || undefined}
          action={
            <Link to="/vendors/intake" className="text-label-sm text-text-link">
              View all
            </Link>
          }
        >
          {s.intake_pending === 0 ? (
            <p className="text-body-sm text-text-subtle">Nothing waiting.</p>
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
        </Panel>
      </div>
    </div>
  );
}

/**
 * A headline number that is also a way in. Declared here rather than in
 * `components/ui` because both existing overviews do the same — there is no DS
 * stat primitive, and one built for three call sites would be a guess.
 */
function Stat({
  label,
  value,
  caption,
  tone,
  to,
}: {
  label: string;
  value: number;
  caption?: string;
  tone: "danger" | "warning";
  to: string;
}) {
  const navigate = useNavigate();
  const quiet = value === 0;
  return (
    <button
      type="button"
      onClick={() => navigate(to)}
      className="rounded-lg border border-border bg-surface-primary px-4 py-3 text-left transition-colors duration-80 ease-state hover:bg-surface-hover focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent"
    >
      <p className="text-caption text-text-subtle">{label}</p>
      <p
        className={cn(
          "tabular mt-1 font-display text-numeral-md",
          // A zero is good news here, so it does not wear the alarm colour.
          quiet
            ? "text-text-primary"
            : tone === "danger"
              ? "text-status-danger-text"
              : "text-status-warning-text",
        )}
      >
        {value}
      </p>
      {caption ? <p className="mt-0.5 text-caption text-text-subtle">{caption}</p> : null}
    </button>
  );
}
