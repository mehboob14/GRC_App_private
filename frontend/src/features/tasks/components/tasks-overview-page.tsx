import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Avatar, ErrorState, Skeleton } from "@/components/ui";
import { cn } from "@/lib/cn";
import { getSummary } from "../api";
import { PRIORITIES } from "../types";
import { PRIORITY_META, SEVERITY_LABEL } from "../tokens";

/** The active statuses that make up the "Open" headline, as a register filter. */
const OPEN_STATUSES = "open,in_progress,blocked,under_review";

// The design tokens are RGB channel triplets ("5 150 105"), consumed as
// rgb(var(--x)); using the bare var yields an invalid colour (renders as none).
const DANGER = "rgb(var(--color-status-danger-base))";
const WARNING = "rgb(var(--color-status-warning-base))";
const SUCCESS = "rgb(var(--color-status-success-base))";
const ACCENT = "rgb(var(--color-action-accent))";
const TRACK = "rgb(var(--color-surface-sunken))";

export function TasksOverviewPage() {
  const query = useQuery({ queryKey: ["task-summary"], queryFn: getSummary });

  if (query.isLoading) {
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-24 rounded-lg" />
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
    return (
      <ErrorState title="Couldn’t load the overview" description="The request failed. Retry, or contact support." onRetry={() => void query.refetch()} />
    );
  }

  const s = query.data;
  const assigneeMax = Math.max(1, ...s.by_assignee.map((a) => a.open));
  const ageMax = Math.max(1, ...s.ageing.map((b) => b.count));
  const onTrack = Math.max(0, s.open_total - s.breaching_now - s.due_soon);

  return (
    <div className="space-y-4">
      {/* Headline — each tile opens the register on exactly that slice. */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Kpi label="Open" value={s.open_total} to={`/tasks?status=${OPEN_STATUSES}`} />
        <Kpi label="Breaching now" value={s.breaching_now} tone="danger" to="/tasks?sla=breached" />
        <Kpi label="Due soon" value={s.due_soon} tone="warning" to="/tasks?sla=due_soon" />
        <Kpi label="Closed this month" value={s.throughput} tone="success" to="/tasks?status=closed" />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* SLA posture — a part-to-whole of open work, the one non-bar view. */}
        <Panel title="SLA posture" meta="open work">
          {s.open_total === 0 ? (
            <Empty>No open work.</Empty>
          ) : (
            <Donut
              total={s.open_total}
              segments={[
                { key: "breached", label: "Breached", value: s.breaching_now, color: DANGER, to: "/tasks?sla=breached" },
                { key: "due_soon", label: "Due soon", value: s.due_soon, color: WARNING, to: "/tasks?sla=due_soon" },
                { key: "on_track", label: "On track", value: onTrack, color: SUCCESS, to: `/tasks?status=${OPEN_STATUSES}` },
              ]}
            />
          )}
        </Panel>

        {/* Open by priority — magnitude across an ordered, semantically-coloured category. */}
        <Panel title="Open by priority">
          <ul className="-mx-2">
            {PRIORITIES.map((p) => (
              <BarRow
                key={p}
                to={`/tasks?priority=${p}&status=${OPEN_STATUSES}`}
                label={
                  <span className={cn("flex items-center gap-1.5", PRIORITY_META[p].text)}>
                    <span className={cn("size-2 rounded-full", PRIORITY_META[p].dot)} />
                    {PRIORITY_META[p].label}
                  </span>
                }
                value={s.open_by_priority[p]}
                fraction={s.open_total ? s.open_by_priority[p] / s.open_total : 0}
                barClass={PRIORITY_META[p].dot}
              />
            ))}
          </ul>
        </Panel>

        {/* Ageing — a distribution across ordered bins reads as columns, not rows. */}
        <Panel title="Ageing" meta="open work by age">
          <Columns bands={s.ageing} max={ageMax} />
        </Panel>

        {/* Load by assignee — a ranking by person. */}
        <Panel title="Load by assignee" meta="open, by person">
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
                  barColor={ACCENT}
                />
              ))}
            </ul>
          )}
        </Panel>
      </div>

      {/* MTTR — the mean ships with its sample size, so a 1-sample figure reads honestly. */}
      <Panel title="Mean time to resolve" meta="closed issues, by severity">
        {s.mttr.length === 0 ? (
          <Empty>No issues closed yet.</Empty>
        ) : (
          <div className="flex flex-wrap gap-x-10 gap-y-4">
            {s.mttr.map((m) => (
              <div key={m.severity}>
                <p className="text-caption text-text-subtle">{SEVERITY_LABEL[m.severity]}</p>
                <p className="mt-0.5 flex items-baseline gap-1.5">
                  <span className="font-display text-heading-sm tabular text-text-primary">{m.days}</span>
                  <span className="text-body-sm text-text-subtle">days</span>
                  <span className={cn("tabular text-caption", m.count < 3 ? "text-status-warning-text" : "text-text-subtle")}>
                    n={m.count}
                  </span>
                </p>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}

function Kpi({ label, value, tone, to }: { label: string; value: number; tone?: "danger" | "warning" | "success"; to: string }) {
  const toneClass =
    tone === "danger"
      ? "text-status-danger-text"
      : tone === "warning"
        ? "text-status-warning-text"
        : tone === "success"
          ? "text-status-success-text"
          : "text-text-primary";
  return (
    <Link
      to={to}
      className="block rounded-lg border border-border bg-surface-primary p-4 transition-colors hover:border-border-strong"
    >
      <p className="type-overline text-text-subtle">{label}</p>
      <p className={cn("mt-1 font-display text-numeral-lg tabular", toneClass)}>{value}</p>
    </Link>
  );
}

type Segment = { key: string; label: string; value: number; color: string; to: string };

/** SVG donut — a ring of segments with the open total in the middle and a
 *  clickable legend. Segments start at 12 o'clock (the -90° rotation). */
function Donut({ total, segments }: { total: number; segments: Segment[] }) {
  const sum = segments.reduce((n, x) => n + x.value, 0) || 1;
  const r = 54;
  const c = 2 * Math.PI * r;
  let acc = 0;
  return (
    <div className="flex items-center gap-6">
      <div className="relative shrink-0">
        <svg viewBox="0 0 132 132" className="size-32 -rotate-90" role="img" aria-label="SLA posture of open work">
          <circle cx="66" cy="66" r={r} fill="none" strokeWidth="15" style={{ stroke: TRACK }} />
          {segments.map((seg) => {
            if (seg.value <= 0) return null;
            const len = (seg.value / sum) * c;
            const node = (
              <circle
                key={seg.key}
                cx="66"
                cy="66"
                r={r}
                fill="none"
                strokeWidth="15"
                style={{ stroke: seg.color }}
                strokeDasharray={`${len} ${c - len}`}
                strokeDashoffset={-acc}
              >
                <title>{`${seg.label}: ${seg.value}`}</title>
              </circle>
            );
            acc += len;
            return node;
          })}
        </svg>
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-display text-heading-md tabular text-text-primary">{total}</span>
          <span className="text-caption text-text-subtle">open</span>
        </div>
      </div>
      <ul className="space-y-2">
        {segments.map((seg) => (
          <li key={seg.key}>
            <Link to={seg.to} className="group flex items-center gap-2 text-body-sm">
              <span className="size-2.5 rounded-sm" style={{ background: seg.color }} />
              <span className="text-text-secondary group-hover:text-text-primary">{seg.label}</span>
              <span className="tabular font-semibold text-text-primary">{seg.value}</span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** One clickable magnitude row: label · bar · count, the whole row a filter link. */
function BarRow({
  to,
  label,
  value,
  fraction,
  barClass,
  barColor,
  labelWidth = "w-24",
}: {
  to: string;
  label: React.ReactNode;
  value: number;
  fraction: number;
  barClass?: string;
  barColor?: string;
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
        <span className="h-2 flex-1 overflow-hidden rounded-full" style={{ background: TRACK }}>
          <span className={cn("block h-full rounded-full", barClass)} style={{ width, background: barColor }} />
        </span>
        <span className="w-6 shrink-0 text-right tabular font-semibold">{value}</span>
      </Link>
    </li>
  );
}

/** Vertical age-distribution columns, sharing a baseline. */
function Columns({ bands, max }: { bands: { band: string; count: number }[]; max: number }) {
  const H = 128;
  return (
    <div className="flex items-end gap-3 pt-2">
      {bands.map((b) => (
        <div key={b.band} className="flex flex-1 flex-col items-center gap-1.5">
          <span className="tabular text-body-sm font-semibold text-text-primary">{b.count}</span>
          <div
            className="w-full rounded-t-sm"
            style={{ height: Math.max(b.count > 0 ? 4 : 0, (b.count / max) * H), background: ACCENT }}
            title={`${b.band}: ${b.count}`}
          />
          <span className="text-center text-caption text-text-subtle">{b.band}</span>
        </div>
      ))}
    </div>
  );
}

function Empty({ children }: { children: React.ReactNode }) {
  return <p className="py-6 text-center text-body-sm text-text-subtle">{children}</p>;
}

function Panel({ title, meta, children }: { title: string; meta?: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-border bg-surface-primary p-5">
      <div className="mb-3 flex items-baseline gap-2">
        <h2 className="font-display text-title-sm text-text-primary">{title}</h2>
        {meta ? <span className="text-caption text-text-subtle">{meta}</span> : null}
      </div>
      {children}
    </div>
  );
}
