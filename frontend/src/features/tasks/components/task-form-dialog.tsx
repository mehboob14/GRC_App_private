import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Button,
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  PeopleSelect,
  PersonSelect,
  Select,
  SelectContent,
  SelectField,
  SelectItem,
  SelectTrigger,
  TextField,
  useToast,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { createTask, listMembers, listSlaDefinitions, updateTask } from "../api";
import {
  CATEGORIES,
  PRIORITIES,
  TASK_KINDS,
  type Category,
  type Priority,
  type TaskDetail,
  type TaskKind,
} from "../types";
import { PRIORITY_META } from "../tokens";

const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
const NONE = "__none__";

type Props =
  | { mode: "create"; task?: undefined; open: boolean; onOpenChange: (v: boolean) => void }
  | { mode: "edit"; task: TaskDetail; open: boolean; onOpenChange: (v: boolean) => void };

export function TaskFormDialog({ mode, task, open, onOpenChange }: Props) {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const [kind, setKind] = useState<TaskKind>("task");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<Priority>("medium");
  const [category, setCategory] = useState<Category>("operations");
  const [slaLevel, setSlaLevel] = useState<string>(NONE);
  const [ownerId, setOwnerId] = useState<string | null>(null);
  const [assignees, setAssignees] = useState<string[]>([]);
  const [dueAt, setDueAt] = useState("");

  const membersQuery = useQuery({ queryKey: ["task-members"], queryFn: listMembers, enabled: open });
  const slaQuery = useQuery({ queryKey: ["task-sla-defs"], queryFn: listSlaDefinitions, enabled: open });
  const people = (membersQuery.data ?? []).map((m) => ({ id: m.membership_id, name: m.name, email: m.email }));

  useEffect(() => {
    if (!open) return;
    if (mode === "edit" && task) {
      setKind(task.task_kind);
      setTitle(task.title);
      setDescription(task.description);
      setPriority(task.priority);
      setCategory(task.category);
      setSlaLevel(task.sla_level ?? NONE);
      setOwnerId(task.owner?.membership_id ?? null);
      setAssignees(task.assignees.map((m) => m.membership_id));
      setDueAt(task.due_at ? task.due_at.slice(0, 10) : "");
    } else {
      setKind("task");
      setTitle("");
      setDescription("");
      setPriority("medium");
      setCategory("operations");
      setSlaLevel(NONE);
      setOwnerId(null);
      setAssignees([]);
      setDueAt("");
    }
  }, [open, mode, task]);

  const save = useMutation({
    mutationFn: () => {
      const sla = slaLevel === NONE ? null : slaLevel;
      const due = dueAt ? new Date(dueAt).toISOString() : null;
      if (mode === "edit" && task) {
        return updateTask(task.id, {
          title,
          description,
          priority,
          category,
          sla_level: sla,
          owner_membership_id: ownerId,
          due_at: due,
        });
      }
      return createTask({
        task_kind: kind,
        title,
        description,
        priority,
        category,
        sla_level: sla,
        owner_membership_id: ownerId,
        // An issue is owned, not assigned; only a task carries assignees.
        assignee_ids: kind === "task" ? assignees : [],
        due_at: due,
      });
    },
    onSuccess: (result) => {
      toast({ title: mode === "edit" ? "Updated" : `${(result as { code: string }).code} created`, tone: "success" });
      onOpenChange(false);
      void queryClient.invalidateQueries({ queryKey: ["tasks"] });
      void queryClient.invalidateQueries({ queryKey: ["task-summary"] });
      if (mode === "edit" && task) void queryClient.invalidateQueries({ queryKey: ["task", task.id] });
    },
    onError: () => toast({ title: "Couldn’t save.", tone: "danger" }),
  });

  const isIssue = kind === "issue";
  const ownerMissing = isIssue && !ownerId;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="lg" className="max-h-[90vh]">
        <DialogHeader>
          <DialogTitle>{mode === "edit" ? `Edit ${task?.code}` : "New task"}</DialogTitle>
        </DialogHeader>

        <div className="space-y-3">
          {mode === "create" ? (
            <div className="grid grid-cols-2 gap-2">
              {TASK_KINDS.map((k) => (
                <button
                  key={k}
                  type="button"
                  onClick={() => {
                    setKind(k);
                    if (k === "issue") setAssignees([]);
                  }}
                  className={cn(
                    "rounded-sm border px-3 py-2.5 text-left",
                    kind === k ? "border-action-accent bg-action-accent-tint" : "border-border hover:border-border-strong",
                  )}
                >
                  <span className="block text-body-md font-medium text-text-primary">{cap(k)}</span>
                  <span className="mt-0.5 block text-caption text-text-subtle">
                    {k === "issue" ? "A finding to remediate and close out" : "A piece of work to track to done"}
                  </span>
                </button>
              ))}
            </div>
          ) : null}

          <TextField label="Title" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Enforce MFA on the remaining admin accounts" />
          <TextField
            label="Description"
            optional
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="What needs to happen, and why."
          />

          <div className="grid grid-cols-2 gap-x-4 gap-y-3">
            <SelectField label="Priority">
              <Select value={priority} onValueChange={(v) => setPriority(v as Priority)}>
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
            <SelectField label="Category">
              <Select value={category} onValueChange={(v) => setCategory(v as Category)}>
                <SelectTrigger aria-label="Category" />
                <SelectContent>
                  {CATEGORIES.map((c) => (
                    <SelectItem key={c} value={c}>
                      {cap(c)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </SelectField>

            <SelectField label="SLA level" optional>
              <Select value={slaLevel} onValueChange={setSlaLevel}>
                <SelectTrigger aria-label="SLA level" />
                <SelectContent>
                  <SelectItem value={NONE}>None</SelectItem>
                  {(slaQuery.data ?? []).map((s) => (
                    <SelectItem key={s.level} value={s.level}>
                      {s.level}
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

          {/* Owner — required on an issue (it is owned, not assigned). */}
          <SelectField label="Owner" optional={!isIssue}>
            <PersonSelect
              people={people}
              value={ownerId}
              onChange={setOwnerId}
              placeholder={isIssue ? "Assign an owner" : "Assign an owner"}
              clearLabel={isIssue ? undefined : "Unassigned"}
              aria-label="Owner"
            />
          </SelectField>

          {/* Assignees — tasks only. */}
          {mode === "create" && !isIssue ? (
            <SelectField label="Assignees" optional>
              <PeopleSelect people={people} values={assignees} onChange={setAssignees} placeholder="Add assignees" />
            </SelectField>
          ) : null}
        </div>

        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button loading={save.isPending} disabled={title.trim() === "" || ownerMissing} onClick={() => save.mutate()}>
            {mode === "edit" ? "Save changes" : "Create"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
