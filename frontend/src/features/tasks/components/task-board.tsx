import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Avatar, ErrorState, Skeleton, StatusPill } from "@/components/ui";
import { cn } from "@/lib/cn";
import { listTasks } from "../api";
import type { Task, TaskFilters, TaskStatus } from "../types";
import { PRIORITY_META, SLA_META, STATUS_META } from "../tokens";

/** Columns shown on the board. `cancelled` is reachable from the table/filters
 *  but kept off the board — a wall of cancelled cards helps no one. */
const COLUMNS: TaskStatus[] = ["open", "in_progress", "blocked", "under_review", "closed"];

export function TaskBoard({ filters }: { filters: Partial<TaskFilters> }) {
  const navigate = useNavigate();
  // One query for the whole board; grouping is client-side.
  const query = useQuery({
    queryKey: ["tasks", "board", filters],
    queryFn: () => listTasks(filters, 1, 500),
  });

  if (query.isError) {
    return (
      <ErrorState
        title="Couldn’t load the board"
        description="The request failed. Retry, or contact support if it keeps happening."
        onRetry={() => void query.refetch()}
      />
    );
  }

  const byStatus = new Map<TaskStatus, Task[]>();
  for (const c of COLUMNS) byStatus.set(c, []);
  for (const t of query.data?.items ?? []) byStatus.get(t.status)?.push(t);

  return (
    <div className="overflow-x-auto">
      <div className="flex min-w-max gap-3 pb-2">
        {COLUMNS.map((status) => {
          const items = byStatus.get(status) ?? [];
          const meta = STATUS_META[status];
          return (
            <div key={status} className="flex w-72 shrink-0 flex-col">
              <div className="mb-2 flex items-center justify-between px-1">
                <span className="flex items-center gap-2">
                  <StatusPill kind="inline" status={meta.family} label={meta.label} />
                </span>
                <span className="tabular text-caption text-text-subtle">
                  {query.isLoading ? "" : items.length}
                </span>
              </div>
              <div className="flex flex-col gap-2 rounded-lg bg-surface-sunken p-2">
                {query.isLoading ? (
                  <>
                    <Skeleton className="h-24 w-full rounded-md" />
                    <Skeleton className="h-24 w-full rounded-md" />
                  </>
                ) : items.length === 0 ? (
                  <p className="px-2 py-6 text-center text-caption text-text-subtle">Nothing here</p>
                ) : (
                  items.map((t) => <BoardCard key={t.id} task={t} onOpen={() => navigate(`/tasks/${t.id}`)} />)
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function BoardCard({ task, onOpen }: { task: Task; onOpen: () => void }) {
  const prio = PRIORITY_META[task.priority];
  const sla = SLA_META[task.sla_state];
  return (
    <button
      type="button"
      onClick={onOpen}
      className="w-full rounded-md border border-border bg-surface-primary p-3 text-left shadow-1 transition-colors hover:border-border-strong"
    >
      <div className="mb-1.5 flex items-center gap-2">
        <span className="font-mono text-caption text-text-subtle">{task.code}</span>
        {task.sla_state !== "none" && task.sla_state !== "on_track" ? (
          <span className="ml-auto">
            <StatusPill kind="inline" status={sla.family} label={sla.label} />
          </span>
        ) : null}
      </div>
      <p className="line-clamp-2 text-body-sm font-medium text-text-primary">{task.title}</p>
      <div className="mt-2.5 flex items-center justify-between">
        <span className={cn("inline-flex items-center gap-1.5 text-caption", prio.text)}>
          <span className={cn("size-1.5 rounded-full", prio.dot)} />
          {prio.label}
        </span>
        <div className="flex items-center -space-x-1.5">
          {task.assignees.slice(0, 3).map((m) => (
            <Avatar key={m.membership_id} name={m.name} size="sm" className="ring-2 ring-surface-primary" />
          ))}
        </div>
      </div>
    </button>
  );
}
