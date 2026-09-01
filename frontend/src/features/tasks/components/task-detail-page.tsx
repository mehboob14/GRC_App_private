import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Avatar,
  Badge,
  Button,
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  Icon,
  PeopleSelect,
  PersonSelect,
  Select,
  SelectContent,
  SelectField,
  SelectItem,
  SelectTrigger,
  StatusPill,
  TextField,
  useToast,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import {
  addCapaAction,
  addComment,
  addSubtask,
  decideApproval,
  getTask,
  listMembers,
  promoteCapaToTask,
  setAssignees,
  transitionCapaAction,
  transitionTask,
  updateCapaAction,
} from "../api";
import { CAPA_TRANSITIONS, CAPA_TYPES, LINK_TARGET_LABEL } from "../types";
import type { CapaAction, CapaStatus, CapaType, LinkTarget, TaskDetail, TaskStatus } from "../types";
import {
  CAPA_STATUS_META,
  CAPA_TYPE_LABEL,
  PRIORITY_META,
  SEVERITY_LABEL,
  SLA_META,
  STATUS_META,
  fmtDate,
  relativeTime,
} from "../tokens";
import { TaskFormDialog } from "./task-form-dialog";

const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
const sourceLabel = (s: string) =>
  s === "manual" ? "Manual" : s === "capa" ? "CAPA" : s.charAt(0).toUpperCase() + s.slice(1);

const PRIMARY_NEXT: Record<TaskStatus, TaskStatus> = {
  open: "in_progress",
  in_progress: "under_review",
  blocked: "in_progress",
  under_review: "closed",
  closed: "in_progress",
  cancelled: "open",
};

function transitionLabel(from: TaskStatus, to: TaskStatus): string {
  if (to === "in_progress") return from === "blocked" ? "Resume" : "Start";
  if (to === "blocked") return "Block";
  if (to === "under_review") return "Send for review";
  if (to === "closed") return "Close";
  if (to === "cancelled") return "Cancel";
  return from === "cancelled" ? "Reinstate" : "Return to open";
}

const humanRelation = (r: string) => r.replace(/_/g, " ");

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "capa", label: "Actions" },
  { id: "subtasks", label: "Sub-tasks" },
  { id: "related", label: "Related" },
  { id: "comments", label: "Comments" },
  { id: "history", label: "Activity" },
] as const;
type TabId = (typeof TABS)[number]["id"];

export function TaskDetailPage() {
  const { taskId = "" } = useParams();
  const navigate = useNavigate();
  return (
    <div className="mx-auto max-w-[1100px]">
      <button
        type="button"
        onClick={() => navigate("/tasks")}
        className="mb-3 inline-flex items-center gap-1.5 text-body-sm text-text-link hover:underline"
      >
        <Icon name="arrowl" className="size-4" />
        Back to register
      </button>
      <TaskDetail taskId={taskId} />
    </div>
  );
}

export function TaskDetail({ taskId, onChanged }: { taskId: string; onChanged?: () => void }) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const [tab, setTab] = useState<TabId>("overview");
  const [transition, setTransition] = useState<TaskStatus | null>(null);
  const [editingAssignees, setEditingAssignees] = useState(false);
  const [editing, setEditing] = useState(false);

  const query = useQuery({ queryKey: ["task", taskId], queryFn: () => getTask(taskId), enabled: taskId.length > 0 });
  const doc = query.data;

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["task", taskId] });
    void queryClient.invalidateQueries({ queryKey: ["tasks"] });
    void queryClient.invalidateQueries({ queryKey: ["task-summary"] });
    onChanged?.();
  };

  const approve = useMutation({
    mutationFn: (decision: "approved" | "rejected") => decideApproval(taskId, decision),
    onSuccess: (_r, decision) => {
      invalidate();
      toast({ title: decision === "approved" ? "Approved" : "Rejected", tone: decision === "approved" ? "success" : "neutral" });
    },
    onError: () => toast({ title: "Couldn’t record the decision.", tone: "danger" }),
  });

  if (query.isLoading) {
    return <p className="text-body-md text-text-subtle">Loading…</p>;
  }
  if (!doc) {
    return <p className="text-body-md text-text-secondary">Task not found.</p>;
  }

  const sla = SLA_META[doc.sla_state];
  const prio = PRIORITY_META[doc.priority];
  // The single obvious next move stays a button; the rest fold into the ⋯ menu.
  const primaryTo = doc.allowed_transitions.find((t) => t === PRIMARY_NEXT[doc.status]) ?? null;
  const otherTransitions = doc.allowed_transitions.filter((t) => t !== primaryTo);

  return (
    <div>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-sm bg-surface-sunken px-2 py-0.5 font-mono text-caption text-text-subtle">{doc.code}</span>
            <Badge variant="neutral">{cap(doc.task_kind)}</Badge>
            <Badge variant="neutral">{cap(doc.category)}</Badge>
            {doc.recurrence_summary ? (
              <span className="text-caption text-text-subtle">{doc.recurrence_summary}</span>
            ) : null}
          </div>
          <h1 className="mt-1.5 font-display text-heading-md text-text-primary">{doc.title}</h1>
        </div>
        <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">
          {doc.approval.required && doc.approval.status === "pending" ? (
            <>
              <Button variant="secondary" loading={approve.isPending} onClick={() => approve.mutate("rejected")}>
                Reject
              </Button>
              <Button loading={approve.isPending} onClick={() => approve.mutate("approved")}>
                Approve
              </Button>
            </>
          ) : null}
          {primaryTo ? (
            <Button onClick={() => setTransition(primaryTo)}>{transitionLabel(doc.status, primaryTo)}</Button>
          ) : null}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                type="button"
                aria-label="More actions"
                className="inline-flex size-9 items-center justify-center rounded-sm border border-border text-text-secondary transition-colors hover:bg-surface-hover"
              >
                <Icon name="more" className="size-4" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onSelect={() => setEditing(true)}>Edit</DropdownMenuItem>
              {otherTransitions.length > 0 ? <DropdownMenuSeparator /> : null}
              {otherTransitions.map((to) => (
                <DropdownMenuItem
                  key={to}
                  variant={to === "cancelled" ? "danger" : "default"}
                  onSelect={() => setTransition(to)}
                >
                  {transitionLabel(doc.status, to)}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Facts */}
      <div className="mt-4 flex flex-wrap items-center gap-x-8 gap-y-2">
        <Field label="Status">
          <StatusPill status={STATUS_META[doc.status].family} label={STATUS_META[doc.status].label} />
        </Field>
        <Field label="Priority">
          <span className={cn("inline-flex items-center gap-1.5 text-body-md", prio.text)}>
            <span className={cn("size-2 rounded-full", prio.dot)} />
            {prio.label}
          </span>
        </Field>
        {doc.task_kind === "issue" && doc.severity ? (
          <Field label="Severity">
            <span className="text-body-md text-text-primary">{SEVERITY_LABEL[doc.severity]}</span>
          </Field>
        ) : null}
        <Field label="SLA">
          {doc.sla_state === "none" ? (
            <Plain>—</Plain>
          ) : (
            <span className="inline-flex items-center gap-2">
              <StatusPill kind="inline" status={sla.family} label={sla.label} />
              {doc.sla_due_at ? <span className="text-caption text-text-subtle">{relativeTime(doc.sla_due_at)}</span> : null}
            </span>
          )}
        </Field>
        <Field label="Owner">
          {doc.owner ? (
            <span className="flex items-center gap-2">
              <Avatar name={doc.owner.name} size="sm" />
              <span className="text-body-md text-text-primary">{doc.owner.name}</span>
            </span>
          ) : (
            <Plain>Unassigned</Plain>
          )}
        </Field>
        <Field label="Due">
          <Plain>{fmtDate(doc.due_at)}</Plain>
        </Field>
      </div>

      {/* Tabs */}
      <nav className="mt-6 flex items-center gap-1 border-b border-border">
        {TABS.filter((t) => t.id !== "capa" || doc.task_kind === "issue").map((t) => {
          const count =
            t.id === "capa"
              ? doc.capa_actions.length
              : t.id === "subtasks"
                ? doc.subtask_count
                : t.id === "related"
                  ? doc.link_count
                  : t.id === "comments"
                    ? doc.comment_count
                    : undefined;
          return (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              className={cn(
                "relative flex items-center gap-1.5 px-3 py-2 text-label-sm",
                tab === t.id ? "text-text-primary" : "text-text-subtle hover:text-text-secondary",
              )}
            >
              {t.label}
              {count ? <span className="tabular text-caption text-text-subtle">{count}</span> : null}
              {tab === t.id ? <span className="absolute inset-x-3 -bottom-px h-0.5 rounded-full bg-action-accent" /> : null}
            </button>
          );
        })}
      </nav>

      <div className="mt-5">
        {tab === "overview" ? (
          <OverviewTab doc={doc} onEditAssignees={() => setEditingAssignees(true)} />
        ) : null}
        {tab === "capa" && doc.task_kind === "issue" ? <CapaTab doc={doc} onChange={invalidate} /> : null}
        {tab === "subtasks" ? <SubtasksTab doc={doc} onChange={invalidate} onOpen={(id) => navigate(`/tasks/${id}`)} /> : null}
        {tab === "related" ? <RelatedTab doc={doc} /> : null}
        {tab === "comments" ? <CommentsTab doc={doc} onChange={invalidate} /> : null}
        {tab === "history" ? <HistoryTab doc={doc} /> : null}
      </div>

      {transition ? (
        <TransitionDialog
          doc={doc}
          to={transition}
          onOpenChange={(o) => !o && setTransition(null)}
          onDone={() => {
            setTransition(null);
            invalidate();
            toast({ title: "Task updated", tone: "success" });
          }}
        />
      ) : null}

      <AssigneeDialog doc={doc} open={editingAssignees} onOpenChange={setEditingAssignees} onDone={invalidate} />
      <TaskFormDialog mode="edit" task={doc} open={editing} onOpenChange={setEditing} />
    </div>
  );
}

// -- tabs --------------------------------------------------------------------

function OverviewTab({ doc, onEditAssignees }: { doc: TaskDetail; onEditAssignees: () => void }) {
  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_20rem]">
      <div className="space-y-4">
        <Panel title="Description">
          {doc.description ? (
            <p className="whitespace-pre-line text-body-md leading-relaxed text-text-secondary">{doc.description}</p>
          ) : (
            <p className="text-body-sm text-text-subtle">No description.</p>
          )}
        </Panel>

        {doc.status === "closed" && doc.closure_note ? (
          <Panel title="Closure note">
            <p className="text-body-md text-text-secondary">{doc.closure_note}</p>
          </Panel>
        ) : null}
        {doc.status === "cancelled" && doc.cancelled_reason ? (
          <Panel title="Cancelled">
            <p className="text-body-md text-text-secondary">{doc.cancelled_reason}</p>
          </Panel>
        ) : null}

        {doc.approval.required ? (
          <Panel title="Approval">
            <div className="flex items-center justify-between">
              <StatusPill
                status={doc.approval.status === "approved" ? "success" : doc.approval.status === "rejected" ? "danger" : "pending"}
                label={cap(doc.approval.status.replace("_", " "))}
              />
              {doc.approval.approver ? (
                <span className="text-body-sm text-text-secondary">Approver · {doc.approval.approver.name}</span>
              ) : null}
            </div>
          </Panel>
        ) : null}
      </div>

      <div className="space-y-4">
        <Panel
          title="Assignees"
          action={
            <Button variant="ghost" size="sm" onClick={onEditAssignees}>
              Assign
            </Button>
          }
        >
          {doc.assignees.length === 0 ? (
            <Plain>Unassigned</Plain>
          ) : (
            <ul className="space-y-2">
              {doc.assignees.map((m) => (
                <li key={m.membership_id} className="flex items-center gap-2">
                  <Avatar name={m.name} size="sm" />
                  <span className="text-body-sm text-text-primary">{m.name}</span>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel title="Details">
          <dl className="space-y-2.5 text-body-sm">
            <Meta label="Reporter" value={doc.reporter?.name ?? "—"} />
            <Meta label="Source" value={sourceLabel(doc.source)} />
            <Meta label="Detected" value={fmtDate(doc.detected_at)} />
            <Meta label="Created" value={fmtDate(doc.created_at)} />
            <Meta label="SLA level" value={doc.sla_level ?? "—"} />
            {doc.recurrence_rule ? <Meta label="Recurs" value={doc.recurrence_summary ?? doc.recurrence_rule} /> : null}
          </dl>
        </Panel>

        {doc.watchers.length > 0 ? (
          <Panel title="Watchers">
            <div className="flex flex-wrap gap-1.5">
              {doc.watchers.map((m) => (
                <span key={m.membership_id} className="inline-flex items-center gap-1.5 rounded-full bg-surface-sunken px-2 py-0.5 text-caption text-text-secondary">
                  <Avatar name={m.name} size="sm" />
                  {m.name}
                </span>
              ))}
            </div>
          </Panel>
        ) : null}
      </div>
    </div>
  );
}

function SubtasksTab({ doc, onChange, onOpen }: { doc: TaskDetail; onChange: () => void; onOpen: (id: string) => void }) {
  const [title, setTitle] = useState("");
  const { toast } = useToast();
  const add = useMutation({
    mutationFn: () => addSubtask(doc.id, title),
    onSuccess: () => {
      setTitle("");
      onChange();
      toast({ title: "Sub-task added", tone: "success" });
    },
  });
  return (
    <Panel title="Sub-tasks">
      <div className="mb-4 flex gap-2">
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && title.trim() && add.mutate()}
          placeholder="Add a sub-task and press Enter…"
          className="flex-1 rounded-sm border border-border bg-surface-primary px-3 py-2 text-body-sm text-text-primary"
        />
        <Button size="sm" loading={add.isPending} disabled={title.trim() === ""} onClick={() => add.mutate()}>
          Add
        </Button>
      </div>
      {doc.subtasks.length === 0 ? (
        <p className="text-body-sm text-text-subtle">No sub-tasks yet.</p>
      ) : (
        <ul className="divide-y divide-border">
          {doc.subtasks.map((s) => (
            <li key={s.id}>
              <button
                type="button"
                onClick={() => onOpen(s.id)}
                className="flex w-full items-center gap-3 py-2.5 text-left hover:bg-surface-hover"
              >
                <span className="font-mono text-caption text-text-subtle">{s.code}</span>
                <span className="min-w-0 flex-1 truncate text-body-sm text-text-primary">{s.title}</span>
                <StatusPill kind="inline" status={STATUS_META[s.status].family} label={STATUS_META[s.status].label} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}

function RelatedTab({ doc }: { doc: TaskDetail }) {
  const provenance = doc.source !== "manual" && doc.source !== "capa" ? doc.source : null;
  const noun = doc.task_kind === "issue" ? "issue" : "task";
  const groups = new Map<LinkTarget, typeof doc.links>();
  for (const l of doc.links) groups.set(l.to_type, [...(groups.get(l.to_type) ?? []), l]);
  return (
    <Panel title="Related records">
      {/* Provenance — where this task or issue came from. */}
      <div className="mb-4 flex items-center justify-between gap-3 rounded-md border border-border bg-surface-sunken/40 px-3.5 py-3">
        <div className="min-w-0">
          <p className="type-overline text-text-subtle">Source</p>
          <p className="mt-0.5 text-body-md text-text-primary">
            {provenance
              ? `Raised from a ${sourceLabel(provenance).toLowerCase()}`
              : doc.source === "capa"
                ? "Promoted from a corrective action"
                : "Raised manually"}
          </p>
        </div>
        <Badge variant="neutral">{sourceLabel(doc.source)}</Badge>
      </div>

      {doc.links.length === 0 ? (
        <p className="text-body-sm text-text-subtle">
          No linked records yet. As the compliance modules connect, the controls, evidence and
          assets this {noun} relates to will appear here for end-to-end audit traceability.
        </p>
      ) : (
        <div className="space-y-4">
          {[...groups.entries()].map(([type, links]) => (
            <div key={type}>
              <p className="type-overline mb-1.5 text-text-subtle">{LINK_TARGET_LABEL[type]}</p>
              <ul className="space-y-1.5">
                {links.map((l) => (
                  <li key={l.id} className="flex items-center gap-2.5 rounded-sm border border-border px-3 py-2">
                    <span className="min-w-0 flex-1 truncate text-body-sm text-text-primary">{l.to_label}</span>
                    <Badge variant="neutral">{humanRelation(l.relation)}</Badge>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}

// -- CAPA actions (issues only) ----------------------------------------------

/** The main forward move for each status, highlighted among the buttons. */
const capaPrimary: Record<CapaStatus, CapaStatus | null> = {
  planned: "in_progress",
  in_progress: "completed",
  blocked: "in_progress",
  completed: "verified",
  verified: null,
  cancelled: "planned",
};

function capaActionLabel(from: CapaStatus, to: CapaStatus): string {
  if (to === "in_progress") {
    if (from === "blocked") return "Resume";
    if (from === "completed" || from === "verified") return "Reopen";
    return "Start";
  }
  if (to === "blocked") return "Block";
  if (to === "completed") return "Mark complete";
  if (to === "verified") return "Verify";
  if (to === "cancelled") return "Cancel";
  return "Reinstate"; // → planned
}

function CapaTab({ doc, onChange }: { doc: TaskDetail; onChange: () => void }) {
  const [adding, setAdding] = useState(false);
  return (
    <Panel
      title="Corrective & preventive actions"
      action={
        <Button variant="secondary" size="sm" onClick={() => setAdding(true)}>
          Add action
        </Button>
      }
    >
      {doc.capa_actions.length === 0 ? (
        <p className="text-body-sm text-text-subtle">
          No actions yet. Add the corrective and preventive steps that resolve this issue and stop it recurring.
        </p>
      ) : (
        <ul className="space-y-3">
          {doc.capa_actions.map((a) => (
            <CapaCard key={a.id} doc={doc} action={a} onChange={onChange} />
          ))}
        </ul>
      )}
      {adding ? (
        <CapaDialog doc={doc} onOpenChange={setAdding} onDone={() => { setAdding(false); onChange(); }} />
      ) : null}
    </Panel>
  );
}

function CapaCard({ doc, action, onChange }: { doc: TaskDetail; action: CapaAction; onChange: () => void }) {
  const { toast } = useToast();
  const [editing, setEditing] = useState(false);
  const status = CAPA_STATUS_META[action.status];
  const move = useMutation({
    mutationFn: (to: CapaStatus) => transitionCapaAction(doc.id, action.id, to),
    onSuccess: onChange,
    onError: (e) => toast({ title: e instanceof Error ? e.message : "Couldn’t update the action.", tone: "danger" }),
  });
  const promote = useMutation({
    mutationFn: () => promoteCapaToTask(doc.id, action.id),
    onSuccess: () => { onChange(); toast({ title: "Promoted to a task", tone: "success" }); },
  });
  const primary = capaPrimary[action.status];
  return (
    <li className="rounded-md border border-border p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="neutral">{CAPA_TYPE_LABEL[action.action_type]}</Badge>
            {action.auto_generated ? <span className="text-caption text-text-subtle">Auto-generated</span> : null}
          </div>
          <p className="mt-1.5 text-body-md font-medium text-text-primary">{action.title}</p>
          {action.description ? (
            <p className="mt-1 whitespace-pre-line text-body-sm text-text-secondary">{action.description}</p>
          ) : null}
        </div>
        <StatusPill status={status.family} label={status.label} />
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-x-6 gap-y-1 text-body-sm text-text-secondary">
        <span className="inline-flex items-center gap-2">
          <span className="text-text-subtle">Owner</span>
          {action.owner ? (
            <span className="inline-flex items-center gap-1.5">
              <Avatar name={action.owner.name} size="sm" />
              {action.owner.name}
            </span>
          ) : (
            <span className="text-text-subtle">Unassigned</span>
          )}
        </span>
        <span>
          <span className="text-text-subtle">Due</span> {fmtDate(action.due_at)}
        </span>
        {action.verified_by ? (
          <span>
            <span className="text-text-subtle">Verified by</span> {action.verified_by.name}
          </span>
        ) : null}
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        {CAPA_TRANSITIONS[action.status].map((to) => (
          <Button
            key={to}
            size="sm"
            variant={to === primary ? "primary" : "secondary"}
            loading={move.isPending}
            className={to === "cancelled" ? "text-status-danger-text" : undefined}
            onClick={() => move.mutate(to)}
          >
            {capaActionLabel(action.status, to)}
          </Button>
        ))}
        <Button variant="ghost" size="sm" onClick={() => setEditing(true)}>
          Edit
        </Button>
        {action.promoted_task_code ? (
          <Link
            to={`/tasks?search=${encodeURIComponent(action.promoted_task_code)}`}
            className="text-body-sm text-text-link hover:underline"
          >
            Promoted to {action.promoted_task_code}
          </Link>
        ) : (
          <Button variant="ghost" size="sm" loading={promote.isPending} onClick={() => promote.mutate()}>
            Promote to task
          </Button>
        )}
      </div>

      {editing ? (
        <CapaDialog doc={doc} action={action} onOpenChange={setEditing} onDone={() => { setEditing(false); onChange(); }} />
      ) : null}
    </li>
  );
}

function CapaDialog({
  doc,
  action,
  onOpenChange,
  onDone,
}: {
  doc: TaskDetail;
  action?: CapaAction;
  onOpenChange: (o: boolean) => void;
  onDone: () => void;
}) {
  const { toast } = useToast();
  const membersQuery = useQuery({ queryKey: ["task-members"], queryFn: listMembers });
  const people = (membersQuery.data ?? []).map((m) => ({ id: m.membership_id, name: m.name, email: m.email }));
  const [type, setType] = useState<CapaType>(action?.action_type ?? "corrective");
  const [title, setTitle] = useState(action?.title ?? "");
  const [description, setDescription] = useState(action?.description ?? "");
  const [ownerId, setOwnerId] = useState<string | null>(action?.owner?.membership_id ?? doc.owner?.membership_id ?? null);
  const [dueAt, setDueAt] = useState(action?.due_at ? action.due_at.slice(0, 10) : "");

  const save = useMutation({
    mutationFn: () => {
      const due = dueAt ? new Date(dueAt).toISOString() : null;
      const input = { action_type: type, title, description, owner_membership_id: ownerId, due_at: due };
      return action ? updateCapaAction(doc.id, action.id, input) : addCapaAction(doc.id, input);
    },
    onSuccess: () => {
      onDone();
      toast({ title: action ? "Action updated" : "Action added", tone: "success" });
    },
    onError: () => toast({ title: "Couldn’t save the action.", tone: "danger" }),
  });

  return (
    <Dialog open onOpenChange={onOpenChange}>
      <DialogContent size="md">
        <DialogHeader>
          <DialogTitle>{action ? "Edit action" : "Add action"}</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <TextField
            label="Title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Rotate the exposed access key and audit its usage"
          />
          <TextField
            label="Description"
            optional
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="What will be done, and how it stops the issue recurring."
          />
          <div className="grid grid-cols-2 gap-x-4 gap-y-3">
            <SelectField label="Type">
              <Select value={type} onValueChange={(v) => setType(v as CapaType)}>
                <SelectTrigger aria-label="Type" />
                <SelectContent>
                  {CAPA_TYPES.map((t) => (
                    <SelectItem key={t} value={t}>
                      {CAPA_TYPE_LABEL[t]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </SelectField>
            <div>
              <span className="mb-1.5 block font-sans text-label-sm text-text-secondary">
                Due date <span className="font-normal text-text-faint">(optional)</span>
              </span>
              <input
                type="date"
                value={dueAt}
                onChange={(e) => setDueAt(e.target.value)}
                className="h-9 w-full rounded-sm border border-border bg-surface-primary px-3 text-body-sm text-text-primary"
              />
            </div>
          </div>
          <SelectField label="Owner" optional>
            <PersonSelect
              people={people}
              value={ownerId}
              onChange={setOwnerId}
              placeholder="Assign an owner"
              clearLabel="Unassigned"
              aria-label="Owner"
            />
          </SelectField>
        </div>
        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button loading={save.isPending} disabled={title.trim() === ""} onClick={() => save.mutate()}>
            {action ? "Save changes" : "Add action"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function CommentsTab({ doc, onChange }: { doc: TaskDetail; onChange: () => void }) {
  const [body, setBody] = useState("");
  const add = useMutation({
    mutationFn: () => addComment(doc.id, body),
    onSuccess: () => {
      setBody("");
      onChange();
    },
  });
  return (
    <Panel title="Comments">
      <div className="mb-4">
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Add a comment…"
          rows={2}
          className="w-full rounded-sm border border-border bg-surface-primary px-3 py-2 text-body-sm text-text-primary"
        />
        <div className="mt-2 flex justify-end">
          <Button size="sm" loading={add.isPending} disabled={body.trim() === ""} onClick={() => add.mutate()}>
            Comment
          </Button>
        </div>
      </div>
      {doc.comments.length === 0 ? (
        <p className="text-body-sm text-text-subtle">No comments yet.</p>
      ) : (
        <ul className="space-y-3">
          {doc.comments.map((c) => (
            <li key={c.id} className="flex gap-3">
              <Avatar name={c.author} size="sm" />
              <div className="min-w-0 flex-1">
                <div className="flex items-baseline gap-2">
                  <span className="text-body-sm font-semibold text-text-primary">{c.author}</span>
                  <span className="text-caption text-text-subtle">{relativeTime(c.created_at)}</span>
                </div>
                <p className="mt-0.5 whitespace-pre-line text-body-sm text-text-secondary">{c.body}</p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}

/** A plain, human sentence for one history entry — no field names or arrows. */
function describeActivity(t: TaskDetail["transitions"][number], noun: string): string {
  switch (t.field_changed) {
    case "created":
      return `created this ${noun}`;
    case "status":
      return `moved it to ${STATUS_META[t.new_value as TaskStatus]?.label ?? t.new_value}`;
    case "priority":
      return `set the priority to ${t.new_value}`;
    case "owner":
      return t.new_value && t.new_value !== "—" ? `made ${t.new_value} the owner` : "removed the owner";
    case "assignees":
      return "changed who's assigned";
    case "approval":
      return t.new_value === "approved" ? "approved it" : "rejected it";
    default:
      return t.new_value ? `changed the ${t.field_changed} to ${t.new_value}` : `updated the ${t.field_changed}`;
  }
}

function friendlyTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    day: "2-digit",
    month: "short",
    hour: "numeric",
    minute: "2-digit",
  });
}

function HistoryTab({ doc }: { doc: TaskDetail }) {
  const noun = doc.task_kind === "issue" ? "issue" : "task";
  return (
    <Panel title="Activity">
      <ol className="relative space-y-4 border-l border-border pl-5">
        {doc.transitions.map((t) => (
          <li key={t.id} className="relative">
            <span className="absolute -left-[1.6rem] top-1.5 size-2 rounded-full bg-action-accent" />
            <p className="text-body-sm text-text-secondary">
              <span className="font-semibold text-text-primary">{t.actor}</span> {describeActivity(t, noun)}
              <span className="text-text-subtle"> · {friendlyTime(t.occurred_at)}</span>
            </p>
            {t.note ? <p className="mt-1 rounded-sm bg-surface-sunken px-2.5 py-1.5 text-body-sm text-text-secondary">{t.note}</p> : null}
          </li>
        ))}
      </ol>
    </Panel>
  );
}

// -- dialogs -----------------------------------------------------------------

function TransitionDialog({
  doc,
  to,
  onOpenChange,
  onDone,
}: {
  doc: TaskDetail;
  to: TaskStatus;
  onOpenChange: (o: boolean) => void;
  onDone: () => void;
}) {
  const [note, setNote] = useState("");
  const { toast } = useToast();
  const noteRequired = to === "closed" || to === "cancelled";
  const run = useMutation({
    mutationFn: () => transitionTask(doc.id, to, note.trim() || undefined),
    onSuccess: onDone,
    onError: (e) => toast({ title: e instanceof Error ? e.message : "Transition failed", tone: "danger" }),
  });
  return (
    <Dialog open onOpenChange={onOpenChange}>
      <DialogContent size="md">
        <DialogHeader>
          <DialogTitle>
            {transitionLabel(doc.status, to)} {doc.code}
          </DialogTitle>
          <p className="text-body-md text-text-secondary">
            {to === "closed"
              ? "Record how this was resolved. The note goes on the permanent history."
              : to === "cancelled"
                ? "Cancelling keeps the record with a reason. Nothing is deleted."
                : "Add an optional note describing the change."}
          </p>
        </DialogHeader>
        <TextField
          label={to === "cancelled" ? "Reason" : "Note"}
          optional={!noteRequired}
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder={to === "closed" ? "Bucket policy corrected; drift alert added." : ""}
        />
        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            loading={run.isPending}
            disabled={noteRequired && note.trim() === ""}
            variant={to === "cancelled" ? "secondary" : "primary"}
            onClick={() => run.mutate()}
          >
            {transitionLabel(doc.status, to)}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function AssigneeDialog({
  doc,
  open,
  onOpenChange,
  onDone,
}: {
  doc: TaskDetail;
  open: boolean;
  onOpenChange: (o: boolean) => void;
  onDone: () => void;
}) {
  const membersQuery = useQuery({ queryKey: ["task-members"], queryFn: listMembers, enabled: open });
  const people = (membersQuery.data ?? []).map((m) => ({ id: m.membership_id, name: m.name, email: m.email }));
  const [selected, setSelected] = useState<string[]>(doc.assignees.map((m) => m.membership_id));
  const { toast } = useToast();
  const save = useMutation({
    mutationFn: () => setAssignees(doc.id, selected),
    onSuccess: () => {
      onOpenChange(false);
      onDone();
      toast({ title: "Assignees updated", tone: "success" });
    },
  });
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="md">
        <DialogHeader>
          <DialogTitle>Assignees</DialogTitle>
        </DialogHeader>
        <PeopleSelect people={people} values={selected} onChange={setSelected} placeholder="Search and add people" />
        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button loading={save.isPending} onClick={() => save.mutate()}>
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// -- primitives --------------------------------------------------------------

function Panel({ title, action, children }: { title: string; action?: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-border bg-surface-primary p-5">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-display text-title-sm text-text-primary">{title}</h2>
        {action}
      </div>
      {children}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-caption text-text-subtle">{label}</p>
      <div className="mt-1">{children}</div>
    </div>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt className="text-text-subtle">{label}</dt>
      <dd className="text-right text-text-primary">{value}</dd>
    </div>
  );
}

function Plain({ children }: { children: React.ReactNode }) {
  return <span className="text-body-md text-text-primary">{children}</span>;
}
