import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  EmptyState,
  ErrorState,
  Skeleton,
  StatusPill,
  Table,
  TBody,
  TD,
  TH,
  THead,
  TR,
} from "@/components/ui";
import { engagementApi } from "@/lib/api/endpoints";
import { useAuth } from "@/lib/auth/auth-context";
import { cn } from "@/lib/cn";
import type { ControlGap, CriterionCoverage } from "@/lib/api/types";

/**
 * Coverage — the three questions an auditor opens with, each answered as a list
 * you can act on rather than a number you cannot get to.
 *
 *   1. Which in-scope criteria have no control?
 *   2. Which controls satisfy no criterion?
 *   3. Which controls carry no evidence?
 *
 * Two figures head the page and they are deliberately different. Coverage asks
 * only whether a control *exists* for a criterion; it does not read the
 * control's status. A workspace that adopts the library and implements nothing
 * reads 100% covered, which is true and also flattering, so the evidenced
 * figure sits beside it and is the one that moves slowly. Presenting either
 * alone would mislead.
 *
 * Everything here comes from GET /engagement/coverage. Nothing is estimated,
 * and where the platform cannot yet measure something it says so rather than
 * showing a zero.
 */

function pct(part: number, whole: number): number {
  return whole === 0 ? 0 : Math.round((part / whole) * 100);
}

/** DS §6.4 progress: 7px track, radius-full, sunken + 1px border, tinted fill. */
function Meter({
  value,
  total,
  tone = "accent",
}: {
  value: number;
  total: number;
  tone?: "accent" | "success";
}) {
  const percent = pct(value, total);
  return (
    <span
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={total}
      aria-valuenow={value}
      aria-label={`${value} of ${total}`}
      className="block h-[7px] w-full overflow-hidden rounded-full border border-border bg-surface-sunken"
    >
      {/* Width transitions on data change, never on mount: DS §7.6 gives chart
          draw-in a duration of none, and motion is for state change only. */}
      <span
        className={cn(
          "block h-full rounded-full transition-[width] duration-150 ease-state motion-reduce:transition-none",
          tone === "success" ? "bg-status-success-base" : "bg-action-accent",
        )}
        style={{ width: `${percent}%` }}
      />
    </span>
  );
}

function Headline({
  label,
  value,
  total,
  caption,
  tone,
}: {
  label: string;
  value: number;
  total: number;
  caption: string;
  tone: "accent" | "success";
}) {
  return (
    <div className="rounded-lg border border-border bg-surface-primary p-5">
      <p className="type-overline mb-2">{label}</p>
      <p className="flex items-baseline gap-2">
        <span className="font-display text-numeral-lg tabular text-text-primary">
          {pct(value, total)}
          <span className="text-numeral-sm text-text-subtle">%</span>
        </span>
        <span className="text-body-sm tabular text-text-secondary">
          {value} of {total}
        </span>
      </p>
      <span className="mt-3 block">
        <Meter value={value} total={total} tone={tone} />
      </span>
      <p className="mt-2.5 text-body-sm text-text-subtle">{caption}</p>
    </div>
  );
}

/** A gap list. Empty is the good outcome here, so it gets a success voice. */
function GapSection<T>({
  title,
  description,
  rows,
  clearedTitle,
  columns,
  renderRow,
}: {
  title: string;
  description: string;
  rows: T[];
  clearedTitle: string;
  columns: string[];
  renderRow: (row: T) => React.ReactNode;
}) {
  return (
    <section className="mt-8">
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="font-display text-heading-sm text-text-primary">
          {title}
          <span className="ml-2 tabular text-body-md font-semibold text-text-subtle">
            {rows.length}
          </span>
        </h2>
        <p className="text-body-sm text-text-subtle">{description}</p>
      </div>
      {rows.length === 0 ? (
        <div className="flex items-center gap-2.5 rounded-lg border border-status-success-border bg-status-success-bg px-4 py-3">
          <StatusPill kind="inline" status="success" label="Clear" />
          <span className="text-body-sm text-status-success-text">
            {clearedTitle}
          </span>
        </div>
      ) : (
        <Table>
          <THead>
            <TR>
              {columns.map((column) => (
                <TH key={column}>{column}</TH>
              ))}
            </TR>
          </THead>
          <TBody>{rows.map(renderRow)}</TBody>
        </Table>
      )}
    </section>
  );
}

export function CoveragePage() {
  const { principal } = useAuth();
  const tenantId = principal?.tenant_id;

  const engagementQuery = useQuery({
    queryKey: ["engagement", tenantId],
    queryFn: () => engagementApi.get(),
  });
  const coverageQuery = useQuery({
    queryKey: ["engagement-coverage", tenantId],
    queryFn: () => engagementApi.coverage(),
  });

  if (engagementQuery.isLoading || coverageQuery.isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-28 w-full rounded-lg" />
        <Skeleton className="h-64 w-full rounded-lg" />
      </div>
    );
  }

  if (coverageQuery.isError) {
    return (
      <ErrorState
        title="Couldn't load coverage"
        description="The coverage report did not come back."
        onRetry={() => void coverageQuery.refetch()}
      />
    );
  }

  // Coverage is measured against the criteria an engagement elects. Without one
  // there is no denominator, and inventing 61 would measure a workspace against
  // criteria it has not taken on.
  if (!engagementQuery.data) {
    return (
      <EmptyState
        icon="shield"
        title="Set your audit scope first"
        description="Coverage is measured against the criteria your engagement covers. Choose an audit type and its Trust Services categories, and this page fills in."
        action={
          <Link
            to="/frameworks/scope"
            className="text-body-md font-semibold text-text-link"
          >
            Go to Scope
          </Link>
        }
      />
    );
  }

  const coverage = coverageQuery.data;
  if (!coverage) return null;

  const evidenced = coverage.controls_total - coverage.controls_without_evidence;

  return (
    <div>
      <div className="grid gap-3 sm:grid-cols-2">
        <Headline
          label="Criteria covered"
          value={coverage.criteria_covered}
          total={coverage.criteria_total}
          caption="In-scope criteria with at least one control that is not disabled."
          tone="accent"
        />
        <Headline
          label="Controls evidenced"
          value={evidenced}
          total={coverage.controls_total}
          caption="Live controls with at least one evidence item attached."
          tone="success"
        />
      </div>

      <p className="mt-3 text-body-sm text-text-subtle">
        Coverage asks whether a control exists for each criterion. It does not
        read the control's status, so it can reach 100% while the work is still
        ahead of you.
      </p>

      <GapSection<CriterionCoverage>
        title="Criteria with no control"
        description="Every in-scope criterion needs at least one live control."
        rows={coverage.criteria_uncovered}
        clearedTitle="Every in-scope criterion has a control."
        columns={["Criterion", "Category", "Status"]}
        renderRow={(gap) => (
          <TR key={gap.requirement_id}>
            <TD>
              <span className="font-display text-body-sm font-semibold text-text-primary">
                {gap.code}
              </span>
              <span className="ml-2 text-body-sm text-text-secondary">
                {gap.name}
              </span>
            </TD>
            <TD className="text-text-secondary">
              {gap.trust_services_category}
            </TD>
            <TD>
              <StatusPill kind="inline" status="warning" label="No control" />
            </TD>
          </TR>
        )}
      />

      <GapSection<ControlGap>
        title="Controls with no criterion"
        description="A control that maps to nothing counts towards no criterion."
        rows={coverage.controls_unmapped}
        clearedTitle="Every live control maps to at least one criterion."
        columns={["Control", "Status"]}
        renderRow={(gap) => (
          <TR key={gap.control_id}>
            <TD>
              <Link
                to={`/controls/${gap.control_id}`}
                className="font-display text-body-sm font-semibold text-text-link"
              >
                {gap.code}
              </Link>
              <span className="ml-2 text-body-sm text-text-secondary">
                {gap.name}
              </span>
            </TD>
            <TD>
              <StatusPill kind="inline" status="warning" label={gap.reason} />
            </TD>
          </TR>
        )}
      />

      <GapSection<ControlGap>
        title="Controls with no evidence"
        description="An auditor tests evidence, not intent."
        rows={coverage.controls_no_evidence}
        clearedTitle="Every live control has evidence attached."
        columns={["Control", "Status"]}
        renderRow={(gap) => (
          <TR key={gap.control_id}>
            <TD>
              <Link
                to={`/controls/${gap.control_id}`}
                className="font-display text-body-sm font-semibold text-text-link"
              >
                {gap.code}
              </Link>
              <span className="ml-2 text-body-sm text-text-secondary">
                {gap.name}
              </span>
            </TD>
            <TD>
              <StatusPill kind="inline" status="warning" label={gap.reason} />
            </TD>
          </TR>
        )}
      />

      <p className="mt-6 text-body-sm text-text-subtle">
        Controls are managed in{" "}
        <Link className="font-semibold text-text-link" to="/controls">
          Controls
        </Link>
        , evidence in{" "}
        <Link className="font-semibold text-text-link" to="/evidence">
          Evidence
        </Link>
        .
      </p>
    </div>
  );
}
