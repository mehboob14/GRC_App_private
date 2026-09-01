import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Avatar,
  Button,
  EmptyState,
  ErrorState,
  FilterFacet,
  Icon,
  Pagination,
  SearchInput,
  StatusPill,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { getSummary, listMembers, listSavedViews, listTasks } from "../api";
import {
  CATEGORIES,
  PRIORITIES,
  TASK_STATUSES,
  type Category,
  type Priority,
  type SavedView,
  type Task,
  type TaskFilters,
  type TaskStatus,
} from "../types";
import { PRIORITY_META, STATUS_META } from "../tokens";
import { TaskFormDialog } from "./task-form-dialog";
import { TaskBoard } from "./task-board";
import { TaskDetail } from "./task-detail-page";

const PAGE_SIZE = 40;

const EMPTY: TaskFilters = {
  search: "",
  kind: "all",
  statuses: [],
  priorities: [],
  categories: [],
  assignee: null,
  sla_state: "all",
  source_type: null,
  source_id: null,
};

const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

const SLA_STATES = ["breached", "due_soon", "paused", "on_track", "none"] as const;

/** Seed the filters from the URL once, so charts and cross-links can deep-link
 *  into a pre-filtered register (e.g. /tasks?priority=critical, ?search=TSK-0002). */
function filtersFromParams(p: URLSearchParams): TaskFilters {
  const f: TaskFilters = { ...EMPTY };
  if (p.get("search")) f.search = p.get("search")!;
  const kind = p.get("kind");
  if (kind === "task" || kind === "issue") f.kind = kind;
  const prio = p.get("priority");
  if (prio && (PRIORITIES as readonly string[]).includes(prio)) f.priorities = [prio as Priority];
  const status = p.get("status");
  if (status) f.statuses = status.split(",").filter((s) => (TASK_STATUSES as readonly string[]).includes(s)) as TaskStatus[];
  const sla = p.get("sla");
  if (sla && (SLA_STATES as readonly string[]).includes(sla)) f.sla_state = sla as TaskFilters["sla_state"];
  const assignee = p.get("assignee");
  if (assignee) f.assignee = assignee;
  return f;
}

export function TasksRegisterPage() {
  const [searchParams] = useSearchParams();
  const [filters, setFilters] = useState<TaskFilters>(() => filtersFromParams(searchParams));
  const [activeView, setActiveView] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [creating, setCreating] = useState(false);
  const [view, setView] = useState<"list" | "board">("list");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const set = <K extends keyof TaskFilters>(key: K, value: TaskFilters[K]) => {
    setFilters((f) => ({ ...f, [key]: value }));
    setActiveView(null);
    setPage(1);
  };

  const viewsQuery = useQuery({ queryKey: ["task-saved-views"], queryFn: listSavedViews });
  const membersQuery = useQuery({ queryKey: ["task-members"], queryFn: listMembers });
  const summaryQuery = useQuery({ queryKey: ["task-summary"], queryFn: getSummary });

  const query = useQuery({
    queryKey: ["tasks", filters, page],
    queryFn: () => listTasks(filters, page, PAGE_SIZE),
    enabled: view === "list",
  });

  const items = useMemo(() => query.data?.items ?? [], [query.data]);

  // Keep a valid selection: default to the first row, and re-point if the
  // selected task falls out of the filtered list (e.g. it was cancelled).
  useEffect(() => {
    if (items.length === 0) {
      if (selectedId !== null) setSelectedId(null);
    } else if (!items.some((t) => t.id === selectedId)) {
      setSelectedId(items[0].id);
    }
  }, [items, selectedId]);

  const assigneeOptions = useMemo(
    () => [
      { value: "me", label: "Assigned to me" },
      { value: "unassigned", label: "Unassigned" },
      ...(membersQuery.data ?? []).map((m) => ({ value: m.membership_id, label: m.name })),
    ],
    [membersQuery.data],
  );

  function applyView(v: SavedView) {
    setFilters({ ...EMPTY, ...v.filters });
    setActiveView(v.id);
    setPage(1);
  }

  const activeCount =
    filters.statuses.length +
    filters.priorities.length +
    filters.categories.length +
    (filters.assignee ? 1 : 0) +
    (filters.sla_state !== "all" ? 1 : 0) +
    (filters.kind !== "all" ? 1 : 0);

  const total = query.data?.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const savedViews = viewsQuery.data ?? [];

  return (
    <div>
      {/* Toolbar — search, scope, filters, counts, view toggle and New task all on one line. */}
      <div className="flex flex-wrap items-center gap-2">
        <SearchInput
          value={filters.search}
          onChange={(v) => set("search", v)}
          placeholder="Search title or code…"
          className="w-56"
        />
        <div className="flex rounded-sm border border-border p-0.5">
          {(["all", "task", "issue"] as const).map((k) => (
            <button
              key={k}
              type="button"
              onClick={() => set("kind", k)}
              className={cn(
                "rounded-xs px-2.5 py-1 text-body-sm transition-colors",
                filters.kind === k ? "bg-surface-sunken font-medium text-text-primary" : "text-text-subtle",
              )}
            >
              {k === "all" ? "All" : cap(k) + "s"}
            </button>
          ))}
        </div>
        <FilterFacet
          label="Status"
          options={TASK_STATUSES.map((s) => ({ value: s, label: STATUS_META[s].label }))}
          values={filters.statuses}
          onChange={(v) => set("statuses", v as TaskStatus[])}
        />
        <FilterFacet
          label="Priority"
          options={PRIORITIES.map((p) => ({ value: p, label: PRIORITY_META[p].label }))}
          values={filters.priorities}
          onChange={(v) => set("priorities", v as Priority[])}
        />
        <FilterFacet
          label="Category"
          options={CATEGORIES.map((c) => ({ value: c, label: cap(c) }))}
          values={filters.categories}
          onChange={(v) => set("categories", v as Category[])}
        />
        <FilterFacet
          label="Assignee"
          options={assigneeOptions}
          values={filters.assignee ? [filters.assignee] : []}
          onChange={(v) => set("assignee", v[v.length - 1] ?? null)}
        />
        {activeCount > 0 || filters.search ? (
          <button
            type="button"
            onClick={() => {
              setFilters(EMPTY);
              setActiveView(null);
              setPage(1);
            }}
            className="text-body-sm font-semibold text-text-link"
          >
            Clear
          </button>
        ) : null}

        <div className="ml-auto flex items-center gap-2.5">
          {summaryQuery.data ? (
            <span className="hidden text-caption text-text-subtle sm:inline">
              <span className="tabular font-medium text-text-secondary">{summaryQuery.data.open_total}</span> open
              {" · "}
              <span className={cn("tabular font-medium", summaryQuery.data.breaching_now > 0 ? "text-status-danger-text" : "text-text-secondary")}>
                {summaryQuery.data.breaching_now}
              </span>{" "}
              overdue
            </span>
          ) : null}
          <div className="flex rounded-sm border border-border p-0.5">
            {(["list", "board"] as const).map((v) => (
              <button
                key={v}
                type="button"
                onClick={() => setView(v)}
                aria-label={`${cap(v)} view`}
                className={cn(
                  "rounded-xs px-2 py-1 transition-colors",
                  view === v ? "bg-surface-sunken text-text-primary" : "text-text-subtle",
                )}
              >
                <Icon name={v === "list" ? "list" : "grid"} className="size-4" />
              </button>
            ))}
          </div>
          <Button onClick={() => setCreating(true)}>New task</Button>
        </div>
      </div>

      {/* Saved views — only when the tenant has some. */}
      {savedViews.length > 0 ? (
        <div className="mt-3 flex flex-wrap items-center gap-1.5">
          {savedViews.map((v) => (
            <button
              key={v.id}
              type="button"
              onClick={() => applyView(v)}
              className={cn(
                "rounded-full border px-3 py-1 text-body-sm transition-colors",
                activeView === v.id
                  ? "border-action-accent bg-action-accent-tint text-action-accent"
                  : "border-border bg-surface-primary text-text-secondary hover:border-border-strong",
              )}
            >
              {v.name}
            </button>
          ))}
        </div>
      ) : null}

      {view === "board" ? (
        <div className="mt-4">
          <TaskBoard filters={filters} />
        </div>
      ) : query.isError ? (
        <ErrorState
          title="Couldn’t load tasks"
          description="The request failed. Retry, or contact support if it keeps happening."
          onRetry={() => void query.refetch()}
          className="mt-6"
        />
      ) : !query.isLoading && total === 0 ? (
        <EmptyState
          icon="audit"
          title={activeCount || filters.search ? "No tasks match these filters" : "No tasks yet"}
          description={
            activeCount || filters.search
              ? "Adjust or clear the filters to see more."
              : "Raise a task or issue to start tracking remediation work."
          }
          action={<Button onClick={() => setCreating(true)}>New task</Button>}
          className="mt-6"
        />
      ) : (
        // Split view: the master list on the left, the selected task on the right.
        <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-[minmax(300px,360px)_1fr] lg:h-[calc(100vh-13rem)]">
          <div className="flex min-h-0 flex-col">
            <div className="min-h-0 flex-1 space-y-1.5 overflow-y-auto pr-1">
              {query.isLoading
                ? [0, 1, 2, 3, 4, 5].map((i) => (
                    <div key={i} className="h-[58px] animate-pulse rounded-md border border-border bg-surface-sunken/40" />
                  ))
                : items.map((t) => (
                    <TaskListCard
                      key={t.id}
                      task={t}
                      selected={t.id === selectedId}
                      onSelect={() => setSelectedId(t.id)}
                    />
                  ))}
            </div>
            {pageCount > 1 ? (
              <div className="mt-2 flex items-center justify-between border-t border-border pt-2">
                <span className="text-caption text-text-subtle">{total} total</span>
                <Pagination page={page} pageCount={pageCount} onPageChange={setPage} />
              </div>
            ) : null}
          </div>

          <div className="min-h-0 overflow-y-auto rounded-lg border border-border bg-surface-primary p-5 lg:p-6">
            {selectedId ? (
              <TaskDetail taskId={selectedId} />
            ) : (
              <p className="text-body-sm text-text-subtle">Select a task to see its detail.</p>
            )}
          </div>
        </div>
      )}

      <TaskFormDialog mode="create" open={creating} onOpenChange={setCreating} />
    </div>
  );
}

function TaskListCard({
  task,
  selected,
  onSelect,
}: {
  task: Task;
  selected: boolean;
  onSelect: () => void;
}) {
  const prio = PRIORITY_META[task.priority];
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-current={selected}
      className={cn(
        "w-full rounded-md border px-3 py-2.5 text-left transition-colors",
        selected
          ? "border-action-accent bg-action-accent-tint"
          : "border-border bg-surface-primary hover:border-border-strong",
      )}
    >
      <div className="flex items-start gap-2.5">
        <div className="min-w-0 flex-1">
          <span className="block truncate text-body-sm font-medium text-text-primary">{task.title}</span>
          <span className="mt-1 flex items-center gap-2 text-caption text-text-subtle">
            <span className={cn("size-2 shrink-0 rounded-full", prio.dot)} aria-label={prio.label} />
            <span className="font-mono">{task.code}</span>
            <StatusPill kind="inline" status={STATUS_META[task.status].family} label={STATUS_META[task.status].label} />
          </span>
        </div>
        {task.assignees.length > 0 ? (
          <Avatar name={task.assignees[0].name} size="sm" className="mt-0.5 shrink-0" />
        ) : null}
      </div>
    </button>
  );
}
