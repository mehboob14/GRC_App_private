import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Button,
  Checkbox,
  Dialog,
  DialogBody,
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
import { describeError, errorToast } from "@/lib/api/describe-error";
import {
  createTask,
  listMembers,
  listSeverityMatrix,
  listSlaDefinitions,
  updateTask,
  type SeverityInput,
} from "../api";
import {
  CATEGORIES,
  IMPACTS,
  PRIORITIES,
  REPEAT_FREQUENCIES,
  SEVERITIES,
  TASK_KINDS,
  URGENCIES,
  type Category,
  type Impact,
  type Priority,
  type RepeatFrequency,
  type Severity,
  type TaskDetail,
  type TaskKind,
  type TaskRepeat,
  type Urgency,
} from "../types";
import { PRIORITY_META, SEVERITY_LABEL } from "../tokens";

const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
const NONE = "__none__";
type Ends = "never" | "on" | "after";

const FREQUENCY_LABEL: Record<RepeatFrequency, string> = {
  daily: "Daily",
  weekly: "Weekly",
  monthly: "Monthly",
  quarterly: "Quarterly",
  yearly: "Yearly",
};
/** What one step of the repeat is called in the "Every" label. */
const FREQUENCY_UNIT: Record<RepeatFrequency, string> = {
  daily: "days",
  weekly: "weeks",
  monthly: "months",
  quarterly: "quarters",
  yearly: "years",
};

const INPUT_CLASS =
  "h-9 w-full rounded-sm border border-border bg-surface-primary px-3 text-body-sm text-text-primary " +
  "focus:border-action-accent focus:shadow-input-focus focus:outline-none";

const todayISO = () => new Date().toISOString().slice(0, 10);

/** A whole number in range, or null: what the number fields mean by valid. */
function wholeNumber(value: string): number | null {
  const n = Number(value);
  return Number.isInteger(n) && n >= 1 && n <= 999 ? n : null;
}

const sameRepeat = (a: TaskRepeat | null, b: TaskRepeat | null) =>
  a === b ||
  (a !== null &&
    b !== null &&
    a.frequency === b.frequency &&
    a.interval === b.interval &&
    a.until === b.until &&
    a.count === b.count);

/** What the severity controls held when the form opened, to tell whether they were touched. */
type SeverityStart = {
  severity: Severity | typeof NONE;
  impact: Impact | typeof NONE;
  urgency: Urgency | typeof NONE;
  reason: string;
};
const NO_START: SeverityStart = { severity: NONE, impact: NONE, urgency: NONE, reason: "" };

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
  const [severity, setSeverity] = useState<Severity | typeof NONE>(NONE);
  const [impact, setImpact] = useState<Impact | typeof NONE>(NONE);
  const [urgency, setUrgency] = useState<Urgency | typeof NONE>(NONE);
  const [reason, setReason] = useState("");
  const [reasonSeen, setReasonSeen] = useState(false);
  const [repeat, setRepeat] = useState<RepeatFrequency | typeof NONE>(NONE);
  const [every, setEvery] = useState("1");
  const [ends, setEnds] = useState<Ends>("never");
  const [endsOn, setEndsOn] = useState("");
  const [endsOnSeen, setEndsOnSeen] = useState(false);
  const [endsAfter, setEndsAfter] = useState("4");
  const [needsApproval, setNeedsApproval] = useState(false);
  const [start, setStart] = useState<SeverityStart>(NO_START);

  const isIssue = kind === "issue";
  // Impact and urgency are an issue's inputs; a task that already carries them (set through
  // the API) keeps them and is held to the matrix like an issue is.
  const impactNow = isIssue ? impact : (task?.impact ?? NONE);
  const urgencyNow = isIssue ? urgency : (task?.urgency ?? NONE);
  const usesMatrix = impactNow !== NONE && urgencyNow !== NONE;

  const membersQuery = useQuery({ queryKey: ["task-members"], queryFn: listMembers, enabled: open });
  const slaQuery = useQuery({ queryKey: ["task-sla-defs"], queryFn: listSlaDefinitions, enabled: open });
  const matrixQuery = useQuery({
    queryKey: ["task-severity-matrix"],
    queryFn: listSeverityMatrix,
    enabled: open && (isIssue || usesMatrix),
  });
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
      // A severity the matrix gave reads as "from the matrix" (Not set); one a person
      // chose, with or without an override, reads as that choice.
      const fromMatrix = Boolean(task.impact && task.urgency && !task.severity_override);
      const opened: SeverityStart = {
        severity: fromMatrix ? NONE : (task.severity ?? NONE),
        impact: task.impact ?? NONE,
        urgency: task.urgency ?? NONE,
        reason: task.severity_override_reason ?? "",
      };
      setStart(opened);
      setSeverity(opened.severity);
      setImpact(opened.impact);
      setUrgency(opened.urgency);
      setReason(opened.reason);
      setReasonSeen(false);
      setRepeat(task.repeat?.frequency ?? NONE);
      setEvery(String(task.repeat?.interval ?? 1));
      setEnds(task.repeat?.until ? "on" : task.repeat?.count ? "after" : "never");
      setEndsOn(task.repeat?.until ?? "");
      setEndsOnSeen(false);
      setEndsAfter(String(task.repeat?.count ?? 4));
      setNeedsApproval(task.approval.required);
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
      setStart(NO_START);
      setSeverity(NONE);
      setImpact(NONE);
      setUrgency(NONE);
      setReason("");
      setReasonSeen(false);
      setRepeat(NONE);
      setEvery("1");
      setEnds("never");
      setEndsOn("");
      setEndsOnSeen(false);
      setEndsAfter("4");
      setNeedsApproval(false);
    }
  }, [open, mode, task]);

  // What the workspace's matrix says for the impact and urgency picked, so a severity
  // chosen against it can say why.
  const resolved: Severity | null = usesMatrix
    ? (matrixQuery.data?.find((c) => c.impact === impactNow && c.urgency === urgencyNow)?.severity ?? null)
    : null;
  const needsReason = resolved !== null && severity !== NONE && severity !== resolved;
  const reasonMissing = needsReason && reason.trim() === "";

  // Only the first task of a series carries the repeat, and a sub-task has none.
  const partOfSeries = mode === "edit" && task?.recurrence_parent_id != null;
  const isSubtask = mode === "edit" && task?.parent_task_id != null;
  const anchor = dueAt || todayISO();
  const everyProblem =
    repeat !== NONE && wholeNumber(every) === null ? "Enter a whole number from 1 to 999." : undefined;
  const endsOnProblem =
    repeat !== NONE && ends === "on" && (endsOn === "" || endsOn <= anchor)
      ? dueAt
        ? "Pick a date after the due date."
        : "Pick a date after today."
      : undefined;
  // A date still left blank is not an error until the person has been to the field.
  const showEndsOnProblem = endsOnSeen || endsOn !== "";
  const endsAfterProblem =
    repeat !== NONE && ends === "after" && wholeNumber(endsAfter) === null
      ? "Enter a whole number from 1 to 999."
      : undefined;
  const repeatProblem = Boolean(everyProblem || endsOnProblem || endsAfterProblem);

  const repeatValue: TaskRepeat | null =
    repeat === NONE
      ? null
      : {
          frequency: repeat,
          interval: wholeNumber(every) ?? 1,
          until: ends === "on" ? endsOn : null,
          count: ends === "after" ? (wholeNumber(endsAfter) ?? null) : null,
        };

  const severityValue: SeverityInput = {
    impact: impactNow === NONE ? null : impactNow,
    urgency: urgencyNow === NONE ? null : urgencyNow,
    severity: severity === NONE ? null : severity,
    reason: needsReason ? reason.trim() : null,
  };

  const save = useMutation({
    mutationFn: () => {
      const sla = slaLevel === NONE ? null : slaLevel;
      const due = dueAt ? new Date(dueAt).toISOString() : null;
      if (mode === "edit" && task) {
        const severityChanged =
          severity !== start.severity ||
          impact !== start.impact ||
          urgency !== start.urgency ||
          (needsReason && reason.trim() !== start.reason.trim());
        return updateTask(task.id, {
          title,
          description,
          priority,
          category,
          sla_level: sla,
          owner_membership_id: ownerId,
          due_at: due,
          severity: severityChanged ? severityValue : undefined,
          repeat: !partOfSeries && !isSubtask && !sameRepeat(task.repeat, repeatValue) ? repeatValue : undefined,
          requires_approval: needsApproval !== task.approval.required ? needsApproval : undefined,
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
        severity: severityValue,
        repeat: repeatValue,
        requires_approval: needsApproval,
      });
    },
    onSuccess: (result) => {
      toast({ title: mode === "edit" ? "Updated" : `${(result as { code: string }).code} created`, tone: "success" });
      onOpenChange(false);
      void queryClient.invalidateQueries({ queryKey: ["tasks"] });
      void queryClient.invalidateQueries({ queryKey: ["task-summary"] });
      if (mode === "edit" && task) void queryClient.invalidateQueries({ queryKey: ["task", task.id] });
    },
    onError: (error) => toast({ title: errorToast(error, "task"), tone: "danger" }),
  });

  const ownerMissing = isIssue && !ownerId;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="lg" scrollBody className="max-h-[90vh]">
        <DialogHeader>
          <DialogTitle>{mode === "edit" ? `Edit ${task?.code}` : "New task"}</DialogTitle>
        </DialogHeader>

        <DialogBody>
          <div className="space-y-3 pb-1">
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

              {isIssue ? (
                <>
                  <SelectField label="Impact" optional>
                    <Select value={impact} onValueChange={(v) => setImpact(v as Impact | typeof NONE)}>
                      <SelectTrigger aria-label="Impact" />
                      <SelectContent>
                        <SelectItem value={NONE}>Not set</SelectItem>
                        {IMPACTS.map((i) => (
                          <SelectItem key={i} value={i}>
                            {cap(i)}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </SelectField>
                  <SelectField label="Urgency" optional>
                    <Select value={urgency} onValueChange={(v) => setUrgency(v as Urgency | typeof NONE)}>
                      <SelectTrigger aria-label="Urgency" />
                      <SelectContent>
                        <SelectItem value={NONE}>Not set</SelectItem>
                        {URGENCIES.map((u) => (
                          <SelectItem key={u} value={u}>
                            {cap(u)}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </SelectField>
                </>
              ) : null}

              <div>
                <SelectField label="Severity" optional>
                  <Select value={severity} onValueChange={(v) => setSeverity(v as Severity | typeof NONE)}>
                    <SelectTrigger aria-label="Severity" />
                    <SelectContent>
                      <SelectItem value={NONE}>Not set</SelectItem>
                      {SEVERITIES.map((s) => (
                        <SelectItem key={s} value={s}>
                          {SEVERITY_LABEL[s]}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </SelectField>
                {resolved ? (
                  <p className="mt-1.5 text-body-sm text-text-subtle">
                    The matrix gives {SEVERITY_LABEL[resolved]}.
                  </p>
                ) : null}
                {matrixQuery.isError ? (
                  <p className="mt-1.5 text-body-sm text-status-danger-text">
                    {describeError(matrixQuery.error, "severity matrix").message}
                  </p>
                ) : null}
              </div>
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
                {slaQuery.isError ? (
                  <p className="text-body-sm text-status-danger-text">
                    {describeError(slaQuery.error, "SLA level list").message}
                  </p>
                ) : null}
              </SelectField>

              {needsReason ? (
                <div className="col-span-2">
                  <TextField
                    label="Why this severity"
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    onBlur={() => setReasonSeen(true)}
                    placeholder="Compensating control in place until the next release."
                    error={reasonMissing && reasonSeen ? "Say why it differs from the matrix." : undefined}
                  />
                </div>
              ) : null}

              <div>
                <label htmlFor="task-due" className="mb-1.5 block font-sans text-label-sm text-text-secondary">
                  Due date <span className="font-normal text-text-faint">(optional)</span>
                </label>
                <input
                  id="task-due"
                  type="date"
                  value={dueAt}
                  onChange={(e) => setDueAt(e.target.value)}
                  className={INPUT_CLASS}
                />
              </div>

              {/* Only the first task of a series carries the repeat, and a sub-task has none. */}
              {isSubtask ? null : partOfSeries ? (
                <p className="col-span-2 rounded-sm bg-surface-sunken px-3 py-2 text-body-sm text-text-secondary">
                  Repeats from {task?.recurrence_parent_code}. Change the repeat on that task.
                </p>
              ) : (
                <>
                  <SelectField label="Repeat">
                    <Select value={repeat} onValueChange={(v) => setRepeat(v as RepeatFrequency | typeof NONE)}>
                      <SelectTrigger aria-label="Repeat" />
                      <SelectContent>
                        <SelectItem value={NONE}>None</SelectItem>
                        {REPEAT_FREQUENCIES.map((f) => (
                          <SelectItem key={f} value={f}>
                            {FREQUENCY_LABEL[f]}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </SelectField>
                  {repeat !== NONE ? (
                    <>
                      <TextField
                        label={`Every (${FREQUENCY_UNIT[repeat]})`}
                        type="number"
                        min={1}
                        max={999}
                        value={every}
                        onChange={(e) => setEvery(e.target.value)}
                        error={everyProblem}
                      />
                      <SelectField label="Ends">
                        <Select value={ends} onValueChange={(v) => setEnds(v as Ends)}>
                          <SelectTrigger aria-label="Ends" />
                          <SelectContent>
                            <SelectItem value="never">Never</SelectItem>
                            <SelectItem value="on">On a date</SelectItem>
                            <SelectItem value="after">After a number of tasks</SelectItem>
                          </SelectContent>
                        </Select>
                      </SelectField>
                      {ends === "on" ? (
                        <div>
                          <label htmlFor="task-ends-on" className="mb-1.5 block font-sans text-label-sm text-text-secondary">
                            End date
                          </label>
                          <input
                            id="task-ends-on"
                            type="date"
                            value={endsOn}
                            onChange={(e) => setEndsOn(e.target.value)}
                            onBlur={() => setEndsOnSeen(true)}
                            aria-invalid={endsOnProblem && showEndsOnProblem ? true : undefined}
                            className={INPUT_CLASS}
                          />
                          {endsOnProblem && showEndsOnProblem ? (
                            <p className="mt-1.5 text-body-sm text-status-danger-text">{endsOnProblem}</p>
                          ) : null}
                        </div>
                      ) : null}
                      {ends === "after" ? (
                        <TextField
                          label="Tasks in all"
                          type="number"
                          min={1}
                          max={999}
                          value={endsAfter}
                          onChange={(e) => setEndsAfter(e.target.value)}
                          hint="Counting this one."
                          error={endsAfterProblem}
                        />
                      ) : null}
                      <p className="col-span-2 text-body-sm text-text-subtle">
                        {dueAt ? "Repeats from the due date." : "Repeats from today."} A new task is raised on each date.
                      </p>
                    </>
                  ) : null}
                </>
              )}
            </div>

            {/* Owner: required on an issue (it is owned, not assigned). */}
            <SelectField label="Owner" optional={!isIssue}>
              <PersonSelect
                people={people}
                value={ownerId}
                onChange={setOwnerId}
                placeholder="Assign an owner"
                clearLabel={isIssue ? undefined : "Unassigned"}
                aria-label="Owner"
              />
              {membersQuery.isError ? (
                <p className="text-body-sm text-status-danger-text">
                  {describeError(membersQuery.error, "list of people").message}
                </p>
              ) : null}
            </SelectField>

            {/* Assignees: tasks only. */}
            {mode === "create" && !isIssue ? (
              <SelectField label="Assignees" optional>
                <PeopleSelect people={people} values={assignees} onChange={setAssignees} placeholder="Add assignees" />
              </SelectField>
            ) : null}

            <label className="flex cursor-pointer items-start gap-2.5 rounded-sm border border-border px-3 py-2.5">
              <Checkbox
                checked={needsApproval}
                onCheckedChange={setNeedsApproval}
                aria-label="Requires approval"
                className="mt-0.5"
              />
              <span>
                <span className="block text-body-md font-medium text-text-primary">Requires approval</span>
                <span className="block text-caption text-text-subtle">
                  An approver signs off once it is sent for review, and only then can it be closed.
                </span>
              </span>
            </label>
          </div>
        </DialogBody>

        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            loading={save.isPending}
            disabled={title.trim() === "" || ownerMissing || reasonMissing || repeatProblem}
            onClick={() => save.mutate()}
          >
            {mode === "edit" ? "Save changes" : "Create"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
