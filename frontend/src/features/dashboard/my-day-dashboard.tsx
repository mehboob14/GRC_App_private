import { useMemo, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import {
  Badge,
  Button,
  Card,
  ChartCard,
  Donut,
  FAMILY_CHART,
  Icon,
  Skeleton,
  StatTile,
  type ChartSegment,
  type IconName,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { useAuth } from "@/lib/auth/auth-context";
import { useAccess, useMyDay } from "./hooks";
import {
  buildQueue,
  countTasks,
  localDay,
  slaClocks,
  upcomingDeadlines,
  type Deadline,
  type DueTone,
  type QueueItem,
  type QueueKind,
  type SlaClock,
} from "./model";
import { LINK, Panel, Tile, ViewAll } from "./section";

/**
 * Operations, My Day: the signed-in person's own work queue, for every role
 * that is not an Admin. It shows what is assigned to them (tasks), what is
 * waiting on them (document approvals and acknowledgements) and the controls
 * they own that lack current evidence. Every row opens its own record, and a
 * source the role cannot read is simply not asked for.
 */

/** Rows in the queue before it says how many more there are. */
const QUEUE_LIMIT = 10;

/** The register filter for "my open tasks", the same statuses the overview counts. */
const MY_OPEN_TASKS = "/tasks?assignee=me&status=open,in_progress,blocked,under_review";

const KIND_META: Record<QueueKind, { icon: IconName; label: string; tile: string }> = {
  task: { icon: "list", label: "Task", tile: "bg-status-progress-bg text-status-progress-text" },
  approval: { icon: "shield", label: "Approval", tile: "bg-status-pending-bg text-status-pending-text" },
  acknowledge: { icon: "doc", label: "Acknowledge", tile: "bg-status-warning-bg text-status-warning-text" },
  evidence: { icon: "controls", label: "Evidence", tile: "bg-status-neutral-bg text-status-neutral-text" },
};

const DUE_TONE: Record<DueTone, string> = {
  overdue: "bg-status-danger-bg text-status-danger-text",
  today: "bg-status-warning-bg text-status-warning-text",
  later: "bg-status-neutral-bg text-status-neutral-text",
};

const SLA_FILL: Record<SlaClock["tone"], string> = {
  danger: "bg-status-danger-base",
  warning: "bg-status-warning-base",
  success: "bg-status-success-base",
};

function greeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 18) return "Good afternoon";
  return "Good evening";
}

export function MyDayDashboard() {
  const { principal } = useAuth();
  const access = useAccess();
  const day = useMyDay(access);
  const firstName = (principal?.user.full_name ?? "there").split(" ")[0];
  const membershipId = principal?.membership_id ?? "";
  const today = localDay(new Date());

  const tasks = day.tasks.data?.items;
  const approvals = day.approvals.data;
  const campaigns = day.campaigns.data;
  const gaps = day.gaps.data;
  const queue = useMemo(
    () => buildQueue({ tasks, approvals, campaigns, gaps, today }),
    [tasks, approvals, campaigns, gaps, today],
  );
  const [showAll, setShowAll] = useState(false);
  const rows = showAll ? queue : queue.slice(0, QUEUE_LIMIT);

  // Where "evidence needed" leads: the person's own controls, where the
  // Evidence column shows which of them have none.
  const evidenceTo = `/controls?owner=${membershipId}`;
  // A source that failed is left out of the ring, not drawn as a zero: the
  // note under the ring says some counts are missing.
  const readable = (state: { on: boolean; failed: boolean }) => state.on && !state.failed;
  const segments = openWork({
    tasks: readable(day.states.tasks) ? (day.tasks.data?.total ?? 0) : null,
    approvals: readable(day.states.approvals) ? (approvals?.length ?? 0) : null,
    campaigns: readable(day.states.campaigns) ? (campaigns?.length ?? 0) : null,
    gaps: readable(day.states.gaps) ? (gaps?.length ?? 0) : null,
    evidenceTo,
  });
  const deadlinesOn = day.states.tasks.on || day.states.campaigns.on;
  const deadlinesLoading = day.states.tasks.pending || day.states.campaigns.pending;
  const deadlinesFailed = day.states.tasks.failed || day.states.campaigns.failed;

  return (
    <div className="w-full">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          {/* No summary line: the overdue and due-today counts are the first
              tiles of the stat row directly below. */}
          <h1 className="font-display text-heading-lg text-text-primary">
            {greeting()}, {firstName}
          </h1>
        </div>
        {access.tasks ? (
          <Button asChild variant="secondary" size="sm">
            <Link to="/tasks?assignee=me">
              <Icon name="list" className="size-4" />
              My tasks
            </Link>
          </Button>
        ) : null}
      </div>

      {/* Stat row. Each tile is its own source: a role without tasks or
          documents simply has fewer tiles, and the row fills the width. */}
      <div className="mt-6 grid grid-cols-[repeat(auto-fit,minmax(11rem,1fr))] gap-3">
        {access.tasks ? (
          <Tile label="My tasks" subject="task list" query={day.tasks} count={3}>
            {(page) => {
              const { overdue, dueToday } = countTasks(page.items, today);
              return (
                <>
                  <StatTile icon="alert" label="Overdue tasks" value={overdue} tone="danger" to={MY_OPEN_TASKS} />
                  <StatTile icon="clock" label="Due today" value={dueToday} tone="warning" to={MY_OPEN_TASKS} />
                  <StatTile icon="list" label="Open tasks" value={page.total} tone="progress" to={MY_OPEN_TASKS} />
                </>
              );
            }}
          </Tile>
        ) : null}
        {access.documents ? (
          <>
            <Tile label="Approvals" subject="approval list" query={day.approvals}>
              {(items) => (
                <StatTile icon="shield" label="To approve" value={items.length} tone="progress" to="/documents" />
              )}
            </Tile>
            <Tile label="Acknowledgements" subject="acknowledgement list" query={day.campaigns}>
              {(items) => (
                <StatTile icon="doc" label="To acknowledge" value={items.length} tone="warning" to="/documents" />
              )}
            </Tile>
          </>
        ) : null}
        {access.compliance && access.evidence ? (
          <Tile label="Evidence" subject="control list" query={day.gaps}>
            {(items) => (
              <StatTile icon="controls" label="Evidence gaps" value={items.length} tone="warning" to={evidenceTo} />
            )}
          </Tile>
        ) : null}
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-[1.6fr_1fr]">
        {/* Needs your attention: overdue first, then what is waiting on you */}
        <Card className="p-0">
          <div className="border-b border-border px-5 py-4">
            <h2 className="font-display text-title-md text-text-primary">Needs your attention</h2>
            <p className="mt-0.5 text-body-sm text-text-subtle">
              Your tasks, approvals and acknowledgements
            </p>
          </div>
          {!day.hasSources ? (
            <Notice icon="lock" title="Nothing to show yet">
              Your role does not include tasks, documents or controls. Ask a workspace admin for access.
            </Notice>
          ) : day.loading ? (
            <QueueSkeleton />
          ) : (
            <>
              {day.failed ? (
                <div
                  role="alert"
                  className="flex items-center justify-between gap-3 border-b border-border bg-status-warning-bg px-5 py-2.5"
                >
                  <p className="text-body-sm text-status-warning-text">Some items could not load.</p>
                  <Button variant="secondary" size="sm" className="shrink-0" onClick={day.retryFailed}>
                    Try again
                  </Button>
                </div>
              ) : null}
              {queue.length > 0 ? (
                <>
                  <ul className="divide-y divide-border">
                    {rows.map((item) => (
                      <QueueRow key={item.key} item={item} />
                    ))}
                  </ul>
                  {queue.length > QUEUE_LIMIT ? (
                    <div className="flex items-center justify-between gap-3 border-t border-border px-5 py-3 text-body-sm">
                      <span className="text-text-subtle">
                        Showing {rows.length} of {queue.length}
                      </span>
                      <button type="button" onClick={() => setShowAll((all) => !all)} className={`rounded-2xs ${LINK}`}>
                        {showAll ? "Show fewer" : "Show all"}
                      </button>
                    </div>
                  ) : null}
                </>
              ) : day.failed ? null : (
                // Only an all clear when every source answered: a failed read
                // must never be reported as "nothing to do".
                <Notice icon="check" title="Nothing needs you right now" tone="success">
                  New assignments, approvals and acknowledgements show up here.
                  <Link
                    to={access.tasks ? "/tasks" : access.documents ? "/documents" : "/controls"}
                    className={`mt-3 block rounded-2xs ${LINK}`}
                  >
                    {access.tasks ? "Open tasks" : access.documents ? "Open documents" : "Open controls"}
                  </Link>
                </Notice>
              )}
            </>
          )}
        </Card>

        {/* Right rail */}
        <div className="flex flex-col gap-6">
          {day.hasSources ? (
            <ChartCard title="My open work">
              {day.loading ? (
                <Skeleton className="mx-auto size-40 rounded-full" />
              ) : (
                <>
                  <Donut
                    size={160}
                    centerValue={segments.reduce((sum, segment) => sum + segment.value, 0)}
                    centerLabel="Open"
                    segments={segments}
                  />
                  {day.failed ? (
                    <p className="mt-3 text-center text-caption text-status-warning-text">
                      Some counts could not load.
                    </p>
                  ) : null}
                </>
              )}
            </ChartCard>
          ) : null}

          {access.tasks ? (
            <Panel
              title="SLA countdown"
              subject="task list"
              query={day.tasks}
              action={<ViewAll to="/tasks?assignee=me&sla=due_soon" label="Due soon" />}
              skeleton={<Skeleton className="h-24 w-full" />}
            >
              {(page) => <SlaCountdown clocks={slaClocks(page.items, Date.now())} />}
            </Panel>
          ) : null}

          {deadlinesOn ? (
            <ChartCard title="Upcoming deadlines">
              {deadlinesLoading ? (
                <Skeleton className="h-32 w-full" />
              ) : (
                <Deadlines items={upcomingDeadlines(tasks ?? [], campaigns ?? [], today)} failed={deadlinesFailed} />
              )}
            </ChartCard>
          ) : null}
        </div>
      </div>
    </div>
  );
}

/** The ring's segments, for the sources this role can read. A source the role
 *  cannot read is left out entirely rather than drawn as a zero. */
function openWork(counts: {
  tasks: number | null;
  approvals: number | null;
  campaigns: number | null;
  gaps: number | null;
  evidenceTo: string;
}): ChartSegment[] {
  const parts = [
    { key: "tasks", label: "Tasks", family: "progress", value: counts.tasks, to: MY_OPEN_TASKS },
    { key: "approvals", label: "Approvals", family: "pending", value: counts.approvals, to: "/documents" },
    { key: "acknowledge", label: "Acknowledgements", family: "warning", value: counts.campaigns, to: "/documents" },
    { key: "evidence", label: "Evidence gaps", family: "neutral", value: counts.gaps, to: counts.evidenceTo },
  ] as const;
  return parts.flatMap((part) =>
    part.value === null
      ? []
      : [
          {
            key: part.key,
            label: part.label,
            value: part.value,
            strokeClass: FAMILY_CHART[part.family].stroke,
            dotClass: FAMILY_CHART[part.family].dot,
            to: part.to,
          },
        ],
  );
}

function QueueRow({ item }: { item: QueueItem }) {
  const meta = KIND_META[item.kind];
  return (
    <li className="flex items-center gap-3 px-5 py-3">
      <span className={cn("flex size-8 shrink-0 items-center justify-center rounded-md", meta.tile)}>
        <Icon name={meta.icon} className="size-4" />
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-body-md font-medium text-text-primary">{item.title}</p>
        <p className="flex items-center gap-1.5 text-body-sm text-text-subtle">
          <Badge variant="neutral">{meta.label}</Badge>
          <span className="truncate">{item.detail}</span>
        </p>
      </div>
      {item.due ? (
        <span
          className={cn(
            "inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 text-caption font-medium",
            DUE_TONE[item.due.tone],
          )}
        >
          <Icon name="clock" className="size-3" />
          {item.due.label}
        </span>
      ) : null}
      <Button asChild size="sm" className="shrink-0">
        <Link to={item.to} aria-label={`${item.action}: ${item.title}`}>
          {item.action}
        </Link>
      </Button>
    </li>
  );
}

function QueueSkeleton() {
  return (
    <ul className="divide-y divide-border" aria-busy="true">
      {Array.from({ length: 4 }, (_, index) => (
        <li key={index} className="flex items-center gap-3 px-5 py-3">
          <Skeleton className="size-8 shrink-0 rounded-md" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-3.5 w-2/3" />
            <Skeleton className="h-3 w-1/3" />
          </div>
          <Skeleton className="h-7 w-16 shrink-0 rounded-sm" />
        </li>
      ))}
    </ul>
  );
}

/** A message that fills the queue when it has nothing to list. */
function Notice({
  icon,
  title,
  tone,
  children,
}: {
  icon: IconName;
  title: string;
  tone?: "success";
  children: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center px-8 py-12 text-center">
      <span
        className={cn(
          "mb-3 flex size-10 items-center justify-center rounded-md",
          tone === "success" ? "bg-status-success-bg" : "bg-surface-hover",
        )}
      >
        <Icon
          name={icon}
          className={cn("size-5", tone === "success" ? "text-status-success-text" : "text-text-subtle")}
        />
      </span>
      <h3 className="font-display text-title-md text-text-primary">{title}</h3>
      <div className="mt-1.5 max-w-md text-body-sm text-text-subtle">{children}</div>
    </div>
  );
}

/** Bars fill as each task's SLA window is used up, so a full bar is a deadline
 *  that has arrived. The label says it in words as well. */
function SlaCountdown({ clocks }: { clocks: SlaClock[] }) {
  if (clocks.length === 0) {
    return <p className="py-4 text-center text-body-sm text-text-subtle">No SLA clocks running.</p>;
  }
  return (
    <ul className="space-y-1">
      {clocks.map((clock) => (
        <li key={clock.key}>
          <Link
            to={clock.to}
            className="flex items-center gap-3 rounded-sm px-1 py-1 transition-colors hover:bg-surface-hover focus-visible:outline focus-visible:outline-2 focus-visible:outline-action-accent"
          >
            <span className="tabular w-20 shrink-0 text-caption text-text-secondary">{clock.code}</span>
            <span className="h-2 flex-1 overflow-hidden rounded-full bg-surface-sunken" aria-hidden>
              <span
                className={cn("block h-full rounded-full", SLA_FILL[clock.tone])}
                style={{ width: `${Math.max(8, Math.round(clock.share * 100))}%` }}
              />
            </span>
            <span
              className={cn(
                "w-24 shrink-0 text-right text-caption font-medium",
                clock.overdue ? "text-status-danger-text" : "text-text-subtle",
              )}
            >
              {clock.label}
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}

function Deadlines({ items, failed }: { items: Deadline[]; failed: boolean }) {
  if (items.length === 0) {
    return (
      <p className="py-4 text-center text-body-sm text-text-subtle">
        {failed ? "Deadlines could not load." : "Nothing due soon."}
      </p>
    );
  }
  return (
    <>
      <ul className="space-y-1">
        {items.map((item) => (
          <li key={item.key}>
            <Link
              to={item.to}
              className="flex items-center gap-3 rounded-sm px-1 py-1.5 transition-colors hover:bg-surface-hover focus-visible:outline focus-visible:outline-2 focus-visible:outline-action-accent"
            >
              <span className="flex size-11 shrink-0 flex-col items-center justify-center rounded-md border border-border bg-surface-sunken leading-none">
                <span className="font-display text-body-md font-bold text-text-primary">{item.day}</span>
                <span className="mt-0.5 text-overline uppercase text-text-subtle">{item.month}</span>
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-body-md font-medium text-text-primary">{item.title}</span>
                <span className="block truncate text-body-sm text-text-subtle">{item.detail}</span>
              </span>
              <span
                aria-hidden
                className={cn(
                  "size-2 shrink-0 rounded-full",
                  item.delta === 0 ? "bg-status-danger-base" : item.delta <= 3 ? "bg-status-warning-base" : "bg-action-accent",
                )}
              />
            </Link>
          </li>
        ))}
      </ul>
      {failed ? (
        <p className="mt-2 text-center text-caption text-status-warning-text">Some deadlines could not load.</p>
      ) : null}
    </>
  );
}
