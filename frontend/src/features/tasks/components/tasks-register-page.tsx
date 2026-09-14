import { useEffect, useMemo, useState } from "react";
import { useOutletContext, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Avatar,
  Button,
  ColumnPicker,
  type ColumnDef,
  EmptyState,
  ErrorState,
  FilterFacet,
  Pagination,
  SearchInput,
  SegmentedControl,
  type SegmentedItem,
  StatusPill,
  Table,
  TableSkeleton,
  TBody,
  TD,
  TH,
  THead,
  Toolbar,
  TR,
  useColumnPrefs,
  useTableSort,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { describeError } from "@/lib/api/describe-error";
import { listMembers, listSavedViews, listTasks } from "../api";
import {
  CATEGORIES,
  PRIORITIES,
  TASK_STATUSES,
  type Category,
  type Priority,
  type SavedView,
  type SlaState,
  type Task,
  type TaskFilters,
  type TaskKind,
  type TaskStatus,
} from "../types";
import { PRIORITY_META, SLA_META, STATUS_META, fmtDate } from "../tokens";
import { TaskBoard } from "./task-board";
import { TaskDetail } from "./task-detail-page";
import type { TasksOutlet } from "./tasks-outlet";

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

/** Sort weight for the SLA column: the hottest state first when sorted desc. */
const SLA_RANK: Record<SlaState, number> = {
  breached: 4,
  due_soon: 3,
  paused: 2,
  on_track: 1,
  none: 0,
};

const KIND_ITEMS: readonly SegmentedItem<TaskKind | "all">[] = [
  { id: "all", label: "All" },
  { id: "task", label: "Tasks" },
  { id: "issue", label: "Issues" },
];

const VIEW_ITEMS: readonly SegmentedItem<"list" | "board">[] = [
  { id: "list", label: "List view", icon: "list" },
  { id: "board", label: "Board view", icon: "grid" },
];

type SortKey = "title" | "status" | "priority" | "assignee" | "due" | "sla";

/** Optional columns only — Task is the identity column and always renders. */
const TASK_COLUMNS = [
  { key: "status", label: "Status" },
  { key: "priority", label: "Priority" },
  { key: "assignee", label: "Assignee" },
  { key: "due", label: "Due" },
  { key: "sla", label: "SLA" },
] as const satisfies readonly ColumnDef<Exclude<SortKey, "title">>[];

type ColKey = (typeof TASK_COLUMNS)[number]["key"];

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
  const { addTask } = useOutletContext<TasksOutlet>();
  const [view, setView] = useState<"list" | "board">("list");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const cols = useColumnPrefs("verity.tasks.columns", TASK_COLUMNS);

  const set = <K extends keyof TaskFilters>(key: K, value: TaskFilters[K]) => {
    setFilters((f) => ({ ...f, [key]: value }));
    setActiveView(null);
    setPage(1);
  };

  const viewsQuery = useQuery({ queryKey: ["task-saved-views"], queryFn: listSavedViews });
  const membersQuery = useQuery({ queryKey: ["task-members"], queryFn: listMembers });

  const query = useQuery({
    queryKey: ["tasks", filters, page],
    queryFn: () => listTasks(filters, page, PAGE_SIZE),
    enabled: view === "list",
  });

  const items = useMemo(() => query.data?.items ?? [], [query.data]);

  // Sorts the page the server returned, not the whole register.
  const { thProps, sortRows } = useTableSort<Task, SortKey>(
    null,
    {
      title: (t) => t.title,
      status: (t) => STATUS_META[t.status].label,
      // Critical is the highest number, so "desc" reads critical first.
      priority: (t) => PRIORITIES.length - PRIORITIES.indexOf(t.priority),
      assignee: (t) => t.assignees[0]?.name ?? null,
      due: (t) => (t.due_at ? new Date(t.due_at) : null),
      sla: (t) => SLA_RANK[t.sla_state],
    },
    "desc",
  );

  const rows = useMemo(() => sortRows(items), [sortRows, items]);

  // Keep a valid selection: default to the first row, and re-point if the
  // selected task falls out of the filtered list (e.g. it was cancelled).
  useEffect(() => {
    if (rows.length === 0) {
      if (selectedId !== null) setSelectedId(null);
    } else if (!rows.some((t) => t.id === selectedId)) {
      setSelectedId(rows[0].id);
    }
  }, [rows, selectedId]);

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

  const listError = query.isError ? describeError(query.error, "task list") : null;
  const total = query.data?.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const savedViews = viewsQuery.data ?? [];

  return (
    <div>
      {/* Toolbar — search, scope, filters, counts, view toggle and New task all on one line. */}
      <Toolbar
        searchLabel="Filter tasks"
        search={
          <SearchInput
            value={filters.search}
            onChange={(v) => set("search", v)}
            placeholder="Search title or code…"
            aria-label="Search tasks"
          />
        }
        actions={
          <>
            <SegmentedControl items={VIEW_ITEMS} value={view} onChange={setView} label="Task view" />
          </>
        }
      >
        <SegmentedControl
          items={KIND_ITEMS}
          value={filters.kind}
          onChange={(k) => set("kind", k)}
          label="Task kind"
        />
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
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setFilters(EMPTY);
              setActiveView(null);
              setPage(1);
            }}
          >
            Clear filters
          </Button>
        ) : null}
      </Toolbar>

      {/* The people behind the Assignee facet are their own request; say so quietly
          rather than showing a filter that silently has no one in it. */}
      {membersQuery.isError ? (
        <p className="mt-2 text-body-sm text-status-danger-text">
          {describeError(membersQuery.error, "assignee list").message}
        </p>
      ) : null}

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
      ) : listError ? (
        <ErrorState
          title={listError.title}
          description={listError.message}
          referenceId={listError.referenceId}
          onRetry={listError.retryable ? () => void query.refetch() : undefined}
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
          action={<Button onClick={addTask}>New task</Button>}
          className="mt-6"
        />
      ) : (
        // Split view: the master table on the left, the selected task on the right.
        <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)] lg:h-[calc(100vh-13rem)]">
          <div className="flex min-h-0 flex-col">
            <div className="min-h-0 flex-1">
              {query.isLoading ? (
                <TableSkeleton rows={8} density="compact" />
              ) : (
                <Table density="compact" className="h-full" actions={<ColumnPicker {...cols} />}>
                  <THead>
                    <TR>
                      <TH {...thProps("title")}>Task</TH>
                      {cols.isVisible("status") ? <TH {...thProps("status")}>Status</TH> : null}
                      {cols.isVisible("priority") ? <TH {...thProps("priority")}>Priority</TH> : null}
                      {cols.isVisible("assignee") ? <TH {...thProps("assignee")}>Assignee</TH> : null}
                      {cols.isVisible("due") ? <TH {...thProps("due")}>Due</TH> : null}
                      {cols.isVisible("sla") ? <TH {...thProps("sla")}>SLA</TH> : null}
                    </TR>
                  </THead>
                  <TBody>
                    {rows.map((t) => (
                      <TaskRow
                        key={t.id}
                        task={t}
                        selected={t.id === selectedId}
                        onSelect={() => setSelectedId(t.id)}
                        isVisible={cols.isVisible}
                      />
                    ))}
                  </TBody>
                </Table>
              )}
            </div>
            {pageCount > 1 ? (
              <div className="mt-2 flex items-center justify-between border-t border-border pt-2">
                <span className="text-caption text-text-subtle">
                  {total} {total === 1 ? "task" : "tasks"}
                </span>
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

    </div>
  );
}

function TaskRow({
  task,
  selected,
  onSelect,
  isVisible,
}: {
  task: Task;
  selected: boolean;
  onSelect: () => void;
  isVisible: (key: ColKey) => boolean;
}) {
  const prio = PRIORITY_META[task.priority];
  const sla = SLA_META[task.sla_state];
  const overdue = task.sla_state === "breached";
  return (
    <TR
      selected={selected}
      onClick={onSelect}
      // The rows were buttons before the table; keep them reachable by keyboard.
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onSelect();
        }
      }}
      className="cursor-pointer"
    >
      <TD>
        <div className="min-w-0">
          <span className="block truncate text-body-sm font-medium text-text-primary">{task.title}</span>
          <span className="font-mono text-caption text-text-subtle">{task.code}</span>
        </div>
      </TD>
      {isVisible("status") ? (
        <TD>
          <StatusPill kind="inline" status={STATUS_META[task.status].family} label={STATUS_META[task.status].label} />
        </TD>
      ) : null}
      {isVisible("priority") ? (
        <TD>
          <span className={cn("inline-flex items-center gap-1.5 whitespace-nowrap text-body-sm", prio.text)}>
            <span className={cn("size-2 shrink-0 rounded-full", prio.dot)} aria-hidden />
            {prio.label}
          </span>
        </TD>
      ) : null}
      {isVisible("assignee") ? (
        <TD>
          {task.assignees.length > 0 ? (
            <span className="inline-flex min-w-0 items-center gap-2">
              <Avatar name={task.assignees[0].name} size="sm" className="shrink-0" />
              <span className="truncate text-body-sm text-text-secondary">{task.assignees[0].name}</span>
            </span>
          ) : (
            <span className="text-body-sm text-text-subtle">Unassigned</span>
          )}
        </TD>
      ) : null}
      {isVisible("due") ? (
        <TD>
          <span
            className={cn(
              "whitespace-nowrap text-body-sm",
              overdue ? "text-status-danger-text" : "text-text-secondary",
            )}
          >
            {fmtDate(task.due_at)}
          </span>
        </TD>
      ) : null}
      {isVisible("sla") ? (
        <TD>
          {task.sla_state === "none" ? (
            <span className="text-body-sm text-text-subtle">No SLA</span>
          ) : (
            <StatusPill kind="inline" status={sla.family} label={sla.label} />
          )}
        </TD>
      ) : null}
    </TR>
  );
}
