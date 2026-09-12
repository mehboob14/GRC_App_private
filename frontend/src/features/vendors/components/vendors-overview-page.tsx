import { Link, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  BarList,
  Donut,
  ErrorState,
  Gauge,
  Icon,
  SeverityChip,
  Skeleton,
  StatusPill,
  type BarListItem,
  type ChartSegment,
  type Severity,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { describeError } from "@/lib/api/describe-error";
import { getSummary, listIntake } from "../api";
import { ATTENTION_META, fmtDate, LIFECYCLE_META, TIER_META } from "../tokens";
import { Panel } from "./panel";

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

/**
 * Full literal class strings — Tailwind scans source text, so a stroke or bar
 * class built by interpolation is purged and the chart paints nothing.
 *
 * Untiered gets its own grey because `TIER_META` puts both `low` and untiered on
 * neutral, and they would otherwise be one indistinguishable ring segment. The
 * two mean opposite things: low is a decision, untiered is its absence.
 */
const TIER_CHART: Record<string, { stroke: string; dot: string; bar: string }> = {
  critical: {
    stroke: "stroke-status-danger-base",
    dot: "bg-status-danger-base",
    bar: "bg-status-danger-base",
  },
  high: {
    stroke: "stroke-status-warning-base",
    dot: "bg-status-warning-base",
    bar: "bg-status-warning-base",
  },
  medium: {
    stroke: "stroke-status-pending-base",
    dot: "bg-status-pending-base",
    bar: "bg-status-pending-base",
  },
  low: {
    stroke: "stroke-status-neutral-base",
    dot: "bg-status-neutral-base",
    bar: "bg-status-neutral-base",
  },
  untiered: {
    stroke: "stroke-border-strong",
    dot: "bg-border-strong",
    bar: "bg-border-strong",
  },
};

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
      strokeClass: TIER_CHART[tier].stroke,
      dotClass: TIER_CHART[tier].dot,
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
          caption="No risk decision yet"
          tone="warning"
          to="/vendors?attention=not_tiered"
        />
        <Stat
          label="No business owner"
          value={attention.get("unowned") ?? 0}
          caption="Nobody answers for them"
          tone="warning"
          to="/vendors?owner=unassigned"
        />
        <Stat
          label="Reassessment overdue"
          value={attention.get("reassessment_overdue") ?? 0}
          caption="Past their review date"
          tone="danger"
          to="/vendors?attention=reassessment_overdue"
        />
        <Stat
          label="Open critical findings"
          value={s.findings_by_severity.critical ?? 0}
          caption={
            s.findings_overdue > 0
              ? `${s.findings_overdue} past their remediation date`
              : "None past their remediation date"
          }
          tone="danger"
          to="/vendors/findings"
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
        <Panel
          title="What the register is waiting on"
          description={
            s.attention.length === 0
              ? undefined
              : "One line per vendor's most pressing item. Click to work that queue."
          }
        >
          {s.attention.length === 0 ? (
            <p className="flex items-center gap-2 text-body-md text-status-success-text">
              <Icon name="check" className="size-4 shrink-0" />
              Nothing is outstanding across {s.total}{" "}
              {s.total === 1 ? "vendor" : "vendors"}.
            </p>
          ) : (
            <ul className="divide-y divide-border">
              {s.attention.map((a) => {
                const meta = ATTENTION_META[a.code];
                return (
                  <li key={a.code}>
                    <Link
                      to={`/vendors?attention=${a.code}`}
                      className="-mx-2 flex items-center justify-between gap-3 rounded-md px-2 py-2.5 transition-colors duration-80 ease-state hover:bg-surface-hover"
                    >
                      <span className="flex min-w-0 items-center gap-2.5">
                        <StatusPill
                          status={meta?.family ?? "neutral"}
                          label={a.label}
                          kind="inline"
                        />
                      </span>
                      <span className="flex shrink-0 items-center gap-2">
                        <span className="tabular text-body-md font-semibold text-text-primary">
                          {a.count}
                        </span>
                        <Icon name="chevr" className="size-4 text-text-subtle" />
                      </span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
        </Panel>

        <Panel
          title="Assessment coverage"
          description="Critical and high vendors inside their reassessment window."
        >
          {s.coverage_in_scope === 0 ? (
            <p className="text-body-sm text-text-subtle">
              No critical or high vendors yet. Coverage is measured over the tiers a cadence
              actually applies to, so this stays empty until one is tiered.
            </p>
          ) : (
            <div className="flex flex-col items-center gap-3 sm:flex-row sm:items-center">
              <Gauge
                value={coveragePct}
                zones={COVERAGE_ZONES}
                label="Current"
                size={170}
              />
              <div className="min-w-0 flex-1">
                <p className="text-body-md text-text-secondary">
                  <span className="tabular font-semibold text-text-primary">
                    {s.coverage_current} of {s.coverage_in_scope}
                  </span>{" "}
                  are inside their window.
                </p>
                {s.coverage_in_scope - s.coverage_current > 0 ? (
                  <Link
                    to="/vendors?attention=reassessment_overdue"
                    className="mt-1.5 inline-flex items-center gap-1 text-label-sm text-text-link"
                  >
                    {s.coverage_in_scope - s.coverage_current} outside it
                    <Icon name="chevr" className="size-4" />
                  </Link>
                ) : null}
                <p className="mt-2 text-caption text-text-subtle">
                  Medium and low vendors have cadences too. This measures the ones an auditor
                  samples first.
                </p>
              </div>
            </div>
          )}
        </Panel>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Panel title="Portfolio by tier">
          {tierSegments.length === 0 ? (
            <p className="text-body-sm text-text-subtle">No vendors yet.</p>
          ) : (
            <Donut
              segments={tierSegments}
              centerValue={s.total}
              centerLabel={s.total === 1 ? "vendor" : "vendors"}
            />
          )}
        </Panel>

        <Panel title="Where they are">
          <BarList items={statusBars} total={s.total} />
        </Panel>

        <Panel
          title="Open findings"
          count={s.findings_open || undefined}
          action={
            s.findings_open > 0 ? (
              <Link to="/vendors/findings" className="text-label-sm text-text-link">
                Work the queue
              </Link>
            ) : null
          }
        >
          {severityBars.length === 0 ? (
            <p className="flex items-center gap-2 text-body-md text-status-success-text">
              <Icon name="check" className="size-4 shrink-0" />
              No open findings.
            </p>
          ) : (
            <>
              <div className="mb-3 flex flex-wrap gap-1.5">
                {severityBars.map((b) => (
                  <SeverityChip
                    key={b.key}
                    severity={b.key as Severity}
                    label={`${b.label} ${b.value}`}
                  />
                ))}
              </div>
              <BarList items={severityBars} total={s.findings_open} />
            </>
          )}
        </Panel>
      </div>

      <Panel
        title="Waiting to come in"
        count={s.intake_pending || undefined}
        action={
          <Link to="/vendors/intake" className="text-label-sm text-text-link">
            Open the queue
          </Link>
        }
        description="Requests from the business that are not vendors yet."
      >
        {s.intake_pending === 0 ? (
          <p className="text-body-sm text-text-subtle">Nothing waiting on a decision.</p>
        ) : intakeQuery.isLoading ? (
          <Skeleton className="h-16 w-full" />
        ) : (
          <ul className="divide-y divide-border">
            {(intakeQuery.data?.items ?? []).slice(0, 3).map((r) => (
              <li key={r.id} className="flex flex-wrap items-center justify-between gap-3 py-2.5">
                <span className="min-w-0">
                  <span className="block truncate text-body-md text-text-primary">
                    {r.vendor_name}
                  </span>
                  <span className="text-caption text-text-subtle">
                    {[r.requested_by_name, r.department].filter(Boolean).join(" · ") ||
                      "Unattributed"}{" "}
                    · {fmtDate(r.created_at)}
                  </span>
                </span>
                {r.screening_status === "flagged" ? (
                  <StatusPill status="warning" label="Possible duplicate" kind="inline" />
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </Panel>
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
  caption: string;
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
      <p className="mt-0.5 text-caption text-text-subtle">{caption}</p>
    </button>
  );
}
