import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
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
  DropdownMenuTrigger,
  ErrorState,
  Icon,
  Select,
  SelectContent,
  SelectField,
  SelectItem,
  SelectTrigger,
  Skeleton,
  Switch,
  TextField,
  useToast,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { useAuth } from "@/lib/auth/auth-context";
import { hasPermission } from "@/lib/auth/session";
import {
  deleteSlaDefinition,
  listAutomations,
  listSeverityMatrix,
  listSlaDefinitions,
  listTemplates,
  saveSlaDefinition,
  updateAutomation,
  updateMatrixCell,
  type AutomationPatch,
} from "../api";
import {
  AUTOMATION_OWNER_RULES,
  IMPACTS,
  LINK_TARGET_LABEL,
  PRIORITIES,
  SEVERITIES,
  TASK_KINDS,
  URGENCIES,
  type Automation,
  type AutomationOwnerRule,
  type Priority,
  type Severity,
  type SeverityMatrixCell,
  type SlaDefinition,
  type TaskKind,
} from "../types";
import { PRIORITY_META, SEVERITY_LABEL } from "../tokens";

const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

export function TasksSettingsPage() {
  const { principal } = useAuth();
  const canEdit = hasPermission(principal, "tasks:manage");
  return (
    <div className="space-y-4">
      {!canEdit ? (
        <p className="text-body-sm text-text-subtle">You can view these settings. Editing needs the Manage tasks permission.</p>
      ) : null}
      <AutomationsCard canEdit={canEdit} />
      <SeverityMatrixCard canEdit={canEdit} />
      <div className="grid gap-4 lg:grid-cols-2">
        <SlaCard canEdit={canEdit} />
        <TemplatesCard />
      </div>
    </div>
  );
}

// -- automations -------------------------------------------------------------

const cardCls = "rounded-lg border border-border bg-surface-primary p-5";

/** A card body that could not load. Retry is only offered when retrying helps. */
function LoadFailed({ error, subject, onRetry }: { error: unknown; subject: string; onRetry: () => void }) {
  const e = describeError(error, subject);
  return (
    <ErrorState
      title={e.title}
      description={e.message}
      referenceId={e.referenceId}
      onRetry={e.retryable ? onRetry : undefined}
      className="mt-3"
    />
  );
}

function AutomationsCard({ canEdit }: { canEdit: boolean }) {
  const query = useQuery({ queryKey: ["task-automations"], queryFn: listAutomations });
  return (
    <div className={cardCls}>
      <h2 className="font-display text-title-md text-text-primary">Automations</h2>
      <p className="mt-1 text-body-sm text-text-subtle">
        Open a task or issue automatically when something happens in another module.
      </p>
      {query.isError ? (
        <LoadFailed error={query.error} subject="automation list" onRetry={() => void query.refetch()} />
      ) : query.isLoading ? (
        <Skeleton className="mt-3 h-40 rounded-md" />
      ) : (
        <ul className="mt-3">
          {(query.data ?? []).map((a) => (
            <AutomationRow key={a.id} automation={a} canEdit={canEdit} />
          ))}
        </ul>
      )}
    </div>
  );
}

function AutomationRow({ automation: a, canEdit }: { automation: Automation; canEdit: boolean }) {
  const [open, setOpen] = useState(false);
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const save = useMutation({
    mutationFn: (patch: AutomationPatch) => updateAutomation(a.id, patch),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["task-automations"] }),
    onError: (error) => toast({ title: errorToast(error, "automation"), tone: "danger" }),
  });
  const locked = !canEdit || !a.available;
  const ownerText = a.owner_rule === "source_owner" ? cap(a.owner_label) : "Unassigned";
  const summary = `Opens a ${a.creates} · ${ownerText} · ${PRIORITY_META[a.priority].label} · due in ${a.due_in_days}d`;

  return (
    <li className="border-t border-border first:border-t-0">
      <div className="flex items-center gap-3 py-2.5">
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          className="flex min-w-0 flex-1 items-center gap-2 text-left"
          aria-expanded={open}
        >
          <Icon name="arrowr" className={cn("size-4 shrink-0 text-text-subtle transition-transform", open && "rotate-90")} />
          <span className="min-w-0">
            <span className="flex items-center gap-2">
              <span className="truncate text-body-sm font-medium text-text-primary">{a.name}</span>
              {!a.available ? (
                <Badge variant="neutral">Soon</Badge>
              ) : a.enabled ? (
                <Badge variant="statusPass">Active</Badge>
              ) : (
                <Badge variant="neutral">Off</Badge>
              )}
            </span>
            <span className="block truncate text-caption text-text-subtle">{summary}</span>
          </span>
        </button>
        <Switch
          checked={a.enabled}
          disabled={locked}
          aria-label={`Enable ${a.name}`}
          onCheckedChange={(v) => save.mutate({ enabled: v })}
        />
      </div>

      {open ? (
        <div className="pb-3 pl-6">
          <p className="mb-3 max-w-[70ch] text-caption text-text-subtle">
            {a.trigger}
            {!a.available ? ` Available once the ${LINK_TARGET_LABEL[a.source].toLowerCase()} module ships.` : ""}
          </p>
          <div className="grid gap-x-4 gap-y-3 sm:grid-cols-2 lg:grid-cols-4">
            <SelectField label="Opens">
              <Select value={a.creates} disabled={locked} onValueChange={(v) => save.mutate({ creates: v as TaskKind })}>
                <SelectTrigger aria-label="Opens" />
                <SelectContent>
                  {TASK_KINDS.map((k) => (
                    <SelectItem key={k} value={k}>
                      {cap(k)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </SelectField>
            <SelectField label="Assign to">
              <Select value={a.owner_rule} disabled={locked} onValueChange={(v) => save.mutate({ owner_rule: v as AutomationOwnerRule })}>
                <SelectTrigger aria-label="Assign to" />
                <SelectContent>
                  {AUTOMATION_OWNER_RULES.map((r) => (
                    <SelectItem key={r} value={r}>
                      {r === "source_owner" ? cap(a.owner_label) : "Unassigned"}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </SelectField>
            <SelectField label="Priority">
              <Select value={a.priority} disabled={locked} onValueChange={(v) => save.mutate({ priority: v as Priority })}>
                <SelectTrigger aria-label="Priority" />
                <SelectContent>
                  {PRIORITIES.map((p) => (
                    <SelectItem key={p} value={p}>
                      {PRIORITY_META[p].label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </SelectField>
            <SelectField label="Due in">
              <Select value={String(a.due_in_days)} disabled={locked} onValueChange={(v) => save.mutate({ due_in_days: Number(v) })}>
                <SelectTrigger aria-label="Due in" />
                <SelectContent>
                  {[1, 2, 3, 5, 7, 14, 30].map((d) => (
                    <SelectItem key={d} value={String(d)}>
                      {d} {d === 1 ? "day" : "days"}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </SelectField>
          </div>
        </div>
      ) : null}
    </li>
  );
}

// -- severity matrix ---------------------------------------------------------

function SeverityMatrixCard({ canEdit }: { canEdit: boolean }) {
  const query = useQuery({ queryKey: ["task-severity-matrix"], queryFn: listSeverityMatrix });
  const [editing, setEditing] = useState<SeverityMatrixCell | null>(null);

  return (
    <div className="rounded-lg border border-border bg-surface-primary p-5">
      <h2 className="mb-4 font-display text-title-md text-text-primary">Severity matrix</h2>

      {query.isError ? (
        <LoadFailed error={query.error} subject="severity matrix" onRetry={() => void query.refetch()} />
      ) : query.isLoading ? (
        <Skeleton className="h-56 rounded-md" />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[520px] border-separate border-spacing-1 text-center">
            <thead>
              <tr>
                <th className="w-24" />
                {URGENCIES.map((u) => (
                  <th key={u} className="pb-1 text-caption uppercase tracking-wide text-text-subtle">
                    Urgency · {cap(u)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {IMPACTS.map((impact) => (
                <tr key={impact}>
                  <th className="pr-2 text-right text-caption uppercase tracking-wide text-text-subtle">
                    Impact · {cap(impact)}
                  </th>
                  {URGENCIES.map((urgency) => {
                    const cell = query.data!.find((c) => c.impact === impact && c.urgency === urgency)!;
                    return (
                      <td key={urgency}>
                        <button
                          type="button"
                          disabled={!canEdit}
                          onClick={() => setEditing(cell)}
                          className={cn(
                            "w-full rounded-md border p-2.5 text-left transition-colors",
                            canEdit ? "hover:border-border-strong" : "cursor-default",
                            cell.is_default ? "border-border bg-surface-sunken/40" : "border-border bg-surface-primary",
                          )}
                        >
                          <span className="block font-display text-body-md font-semibold text-text-primary">
                            {SEVERITY_LABEL[cell.severity]}
                          </span>
                          <span className="block text-caption text-text-subtle">
                            respond {cell.respond_hours}h · resolve {cell.resolve_hours}h{cell.is_default ? " · default" : ""}
                          </span>
                        </button>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {editing ? <MatrixCellDialog cell={editing} onOpenChange={(o) => !o && setEditing(null)} /> : null}
    </div>
  );
}

function MatrixCellDialog({ cell, onOpenChange }: { cell: SeverityMatrixCell; onOpenChange: (o: boolean) => void }) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [severity, setSeverity] = useState<Severity>(cell.severity);
  const [respond, setRespond] = useState(String(cell.respond_hours));
  const [resolve, setResolve] = useState(String(cell.resolve_hours));

  const save = useMutation({
    mutationFn: () =>
      updateMatrixCell(cell.impact, cell.urgency, {
        severity,
        respond_hours: Number(respond) || 0,
        resolve_hours: Number(resolve) || 0,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["task-severity-matrix"] });
      onOpenChange(false);
      toast({ title: "Matrix updated", tone: "success" });
    },
    onError: (error) => toast({ title: errorToast(error, "severity matrix"), tone: "danger" }),
  });

  return (
    <Dialog open onOpenChange={onOpenChange}>
      <DialogContent size="md">
        <DialogHeader>
          <DialogTitle>
            Impact {cap(cell.impact)} · Urgency {cap(cell.urgency)}
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <SelectField label="Severity">
            <Select value={severity} onValueChange={(v) => setSeverity(v as Severity)}>
              <SelectTrigger aria-label="Severity" />
              <SelectContent>
                {SEVERITIES.map((s) => (
                  <SelectItem key={s} value={s}>
                    {SEVERITY_LABEL[s]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </SelectField>
          <div className="grid grid-cols-2 gap-3">
            <NumberField label="Respond within (hours)" value={respond} onChange={setRespond} />
            <NumberField label="Resolve within (hours)" value={resolve} onChange={setResolve} />
          </div>
        </div>
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

// -- SLA definitions ---------------------------------------------------------

function SlaCard({ canEdit }: { canEdit: boolean }) {
  const query = useQuery({ queryKey: ["task-sla-defs"], queryFn: listSlaDefinitions });
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [editing, setEditing] = useState<SlaDefinition | "new" | null>(null);

  const remove = useMutation({
    mutationFn: (level: string) => deleteSlaDefinition(level),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["task-sla-defs"] });
      toast({ title: "SLA level removed", tone: "success" });
    },
    onError: (error) => toast({ title: errorToast(error, "SLA level"), tone: "danger" }),
  });

  return (
    <div className="rounded-lg border border-border bg-surface-primary p-5">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-display text-title-md text-text-primary">SLA levels</h2>
        {canEdit ? (
          <Button variant="secondary" size="sm" onClick={() => setEditing("new")}>
            Add level
          </Button>
        ) : null}
      </div>
      {query.isError ? (
        <p className="text-body-sm text-status-danger-text">
          {describeError(query.error, "SLA level list").message}
        </p>
      ) : query.isLoading ? (
        <Skeleton className="h-32 rounded-md" />
      ) : (
        <ul className="divide-y divide-border">
          {(query.data ?? []).map((s) => (
            <li key={s.level} className="flex items-center justify-between gap-3 py-2.5 first:pt-0 last:pb-0">
              <div className="min-w-0">
                <span className="block truncate text-body-sm font-medium text-text-primary">{s.level}</span>
                <span className="tabular text-caption text-text-subtle">
                  respond {s.respond_hours}h · resolve {s.resolve_hours}h
                </span>
              </div>
              {canEdit ? (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <button
                      type="button"
                      aria-label={`Actions for ${s.level}`}
                      className="inline-flex size-7 shrink-0 items-center justify-center rounded-sm text-text-subtle transition-colors hover:bg-surface-hover"
                    >
                      <Icon name="more" className="size-4" />
                    </button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem onSelect={() => setEditing(s)}>Edit</DropdownMenuItem>
                    <DropdownMenuItem variant="danger" onSelect={() => remove.mutate(s.level)}>
                      Remove
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              ) : null}
            </li>
          ))}
        </ul>
      )}
      {editing ? (
        <SlaDialog
          initial={editing === "new" ? null : editing}
          onOpenChange={(o) => !o && setEditing(null)}
        />
      ) : null}
    </div>
  );
}

function SlaDialog({ initial, onOpenChange }: { initial: SlaDefinition | null; onOpenChange: (o: boolean) => void }) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [level, setLevel] = useState(initial?.level ?? "");
  const [respond, setRespond] = useState(String(initial?.respond_hours ?? 24));
  const [resolve, setResolve] = useState(String(initial?.resolve_hours ?? 72));

  const save = useMutation({
    mutationFn: () =>
      saveSlaDefinition(initial?.level ?? null, {
        level: level.trim(),
        respond_hours: Number(respond) || 0,
        resolve_hours: Number(resolve) || 0,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["task-sla-defs"] });
      onOpenChange(false);
      toast({ title: initial ? "SLA level updated" : "SLA level added", tone: "success" });
    },
    onError: (error) => toast({ title: errorToast(error, "SLA level"), tone: "danger" }),
  });

  return (
    <Dialog open onOpenChange={onOpenChange}>
      <DialogContent size="md">
        <DialogHeader>
          <DialogTitle>{initial ? `Edit ${initial.level}` : "Add SLA level"}</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <TextField label="Level" value={level} onChange={(e) => setLevel(e.target.value)} placeholder="P1 Critical" />
          <div className="grid grid-cols-2 gap-3">
            <NumberField label="Respond within (hours)" value={respond} onChange={setRespond} />
            <NumberField label="Resolve within (hours)" value={resolve} onChange={setResolve} />
          </div>
        </div>
        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button loading={save.isPending} disabled={level.trim() === ""} onClick={() => save.mutate()}>
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function NumberField({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <div>
      <span className="mb-1.5 block font-sans text-label-sm text-text-secondary">{label}</span>
      <input
        type="number"
        min={0}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 w-full rounded-sm border border-border bg-surface-primary px-3 text-body-sm tabular text-text-primary"
      />
    </div>
  );
}

// -- templates ---------------------------------------------------------------

function TemplatesCard() {
  const query = useQuery({ queryKey: ["task-templates"], queryFn: listTemplates });
  return (
    <div className="rounded-lg border border-border bg-surface-primary p-5">
      <h2 className="mb-3 font-display text-title-md text-text-primary">Templates</h2>
      {query.isError ? (
        <p className="text-body-sm text-status-danger-text">
          {describeError(query.error, "template list").message}
        </p>
      ) : query.isLoading ? (
        <Skeleton className="h-32 rounded-md" />
      ) : (
        <ul className="space-y-3">
          {(query.data ?? []).map((t) => (
            <li key={t.id} className="rounded-md border border-border p-3">
              <div className="flex items-center gap-2">
                <span className="text-body-md font-medium text-text-primary">{t.name}</span>
                <Badge variant="neutral">{cap(t.task_kind)}</Badge>
                {t.recurrence_rule ? <span className="text-caption text-text-subtle">Recurring</span> : null}
              </div>
              <ul className="mt-2 space-y-1">
                {t.subtasks.map((st, i) => (
                  <li key={i} className="flex items-start gap-2 text-body-sm text-text-secondary">
                    <span className="mt-2 size-1.5 shrink-0 rounded-full bg-text-faint" />
                    {st}
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
