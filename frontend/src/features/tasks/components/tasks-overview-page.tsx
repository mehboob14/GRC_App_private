import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Avatar,
  ChartCard,
  Donut,
  ErrorState,
  FAMILY_CHART,
  Skeleton,
  StackedBars,
  StatTile,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { describeError } from "@/lib/api/describe-error";
import { getSummary } from "../api";
import { PRIORITIES } from "../types";
import { PRIORITY_META, SEVERITY_LABEL } from "../tokens";

/** The active statuses that make up the "Open" headline, as a register filter. */
const OPEN_STATUSES = "open,in_progress,blocked,under_review";

export function TasksOverviewPage() {
  const query = useQuery({ queryKey: ["task-summary"], queryFn: getSummary });

  if (query.isLoading) {
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-[4.75rem] rounded-lg" />
          ))}
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          <Skeleton className="h-64 rounded-lg" />
          <Skeleton className="h-64 rounded-lg" />
        </div>
      </div>
    );
  }
  if (query.isError || !query.data) {
    const e = describeError(query.error, "overview");
    return (
      <ErrorState
        title={e.title}
        description={e.message}
        referenceId={e.referenceId}
        onRetry={e.retryable ? () => void query.refetch() : undefined}
      />
    );
  }

  const s = query.data;
  const assigneeMax = Math.max(1, ...s.by_assignee.map((a) => a.open));
  const onTrack = Math.max(0, s.open_total - s.breaching_now - s.due_soon);

  return (
    <div className="space-y-4">
      {/* Headline: each tile opens the register on exactly that slice. */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatTile icon="list" label="Open" value={s.open_total} tone="progress" to={`/tasks?status=${OPEN_STATUSES}`} />
        <StatTile icon="alert" label="Breaching now" value={s.breaching_now} tone="danger" to="/tasks?sla=breached" />
        <StatTile icon="clock" label="Due soon" value={s.due_soon} tone="warning" to="/tasks?sla=due_soon" />
        <StatTile icon="check" label="Closed this month" value={s.throughput} tone="success" to="/tasks?status=closed" />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* SLA posture: a part-to-whole of open work. The legend links to each slice. */}
        <ChartCard title="SLA posture">
          {s.open_total === 0 ? (
            <Empty>No open work.</Empty>
          ) : (
            <Donut
              centerValue={s.open_total}
              centerLabel="Open"
              segments={[
                { key: "breached", label: "Breached", value: s.breaching_now, strokeClass: FAMILY_CHART.danger.stroke, dotClass: FAMILY_CHART.danger.dot, to: "/tasks?sla=breached" },
                { key: "due_soon", label: "Due soon", value: s.due_soon, strokeClass: FAMILY_CHART.warning.stroke, dotClass: FAMILY_CHART.warning.dot, to: "/tasks?sla=due_soon" },
                { key: "on_track", label: "On track", value: onTrack, strokeClass: FAMILY_CHART.success.stroke, dotClass: FAMILY_CHART.success.dot, to: `/tasks?status=${OPEN_STATUSES}` },
              ]}
            />
          )}
        </ChartCard>

        {/* Open by priority: magnitude across an ordered, semantically coloured category. */}
        <ChartCard title="Open by priority">
          <ul className="-mx-2">
            {PRIORITIES.map((p) => (
              <BarRow
                key={p}
                to={`/tasks?priority=${p}&status=${OPEN_STATUSES}`}
                label={
                  <span className={cn("flex items-center gap-1.5", PRIORITY_META[p].text)}>
                    <span className={cn("h-2.5 w-4 rounded-2xs", PRIORITY_META[p].dot)} />
                    {PRIORITY_META[p].label}
                  </span>
                }
                value={s.open_by_priority[p]}
                fraction={s.open_total ? s.open_by_priority[p] / s.open_total : 0}
                barClass={PRIORITY_META[p].dot}
              />
            ))}
          </ul>
        </ChartCard>

        {/* Ageing: a distribution across ordered bins reads as columns. */}
        <ChartCard title="Open work by age">
          <StackedBars
            series={[{ key: "open", label: "Open", fillClass: "bg-action-accent" }]}
            columns={s.ageing.map((b) => ({ key: b.band, label: b.band, values: { open: b.count } }))}
          />
        </ChartCard>

        {/* Load by assignee: a ranking by person. */}
        <ChartCard title="Load by assignee">
          {s.by_assignee.length === 0 ? (
            <Empty>No open work assigned.</Empty>
          ) : (
            <ul className="-mx-2">
              {s.by_assignee.map(({ member, open }) => (
                <BarRow
                  key={member.membership_id}
                  to={`/tasks?assignee=${member.membership_id}&status=${OPEN_STATUSES}`}
                  label={
                    <span className="flex items-center gap-2">
                      <Avatar name={member.name} size="sm" />
                      <span className="truncate">{member.name}</span>
                    </span>
                  }
                  labelWidth="w-36"
                  value={open}
                  fraction={open / assigneeMax}
                  barClass="bg-action-accent"
                />
              ))}
            </ul>
          )}
        </ChartCard>
      </div>

      {/* MTTR: the mean ships with its sample size, so a 1-sample figure reads honestly. */}
      <ChartCard title="Mean time to resolve">
        {s.mttr.length === 0 ? (
          <Empty>No issues closed yet.</Empty>
        ) : (
          <div className="flex flex-wrap justify-center gap-x-12 gap-y-4">
            {s.mttr.map((m) => (
              <div key={m.severity} className="text-center">
                <p className="flex items-baseline justify-center gap-1.5">
                  <span className="font-display text-numeral-md tabular text-text-primary">{m.days}</span>
                  <span className="text-body-sm text-text-subtle">days</span>
                </p>
                <p className="text-body-sm text-text-secondary">{SEVERITY_LABEL[m.severity]}</p>
                <p className={cn("tabular text-caption", m.count < 3 ? "text-status-warning-text" : "text-text-subtle")}>
                  n={m.count}
                </p>
              </div>
            ))}
          </div>
        )}
      </ChartCard>
    </div>
  );
}

/** One clickable magnitude row: label, bar, count. The whole row is a filter link. */
function BarRow({
  to,
  label,
  value,
  fraction,
  barClass,
  labelWidth = "w-24",
}: {
  to: string;
  label: React.ReactNode;
  value: number;
  fraction: number;
  barClass: string;
  labelWidth?: string;
}) {
  const width = `${Math.max(fraction * 100, value > 0 ? 3 : 0)}%`;
  return (
    <li>
      <Link
        to={to}
        className="flex items-center gap-3 rounded-md px-2 py-1.5 text-body-sm text-text-primary transition-colors hover:bg-surface-hover"
      >
        <span className={cn("shrink-0 truncate", labelWidth)}>{label}</span>
        <span className="h-2.5 flex-1 overflow-hidden rounded-full bg-surface-sunken">
          <span className={cn("block h-full rounded-full", barClass)} style={{ width }} />
        </span>
        <span className="w-6 shrink-0 text-right tabular font-semibold">{value}</span>
      </Link>
    </li>
  );
}

function Empty({ children }: { children: React.ReactNode }) {
  return <p className="py-6 text-center text-body-sm text-text-subtle">{children}</p>;
}
