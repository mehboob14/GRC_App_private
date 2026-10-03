/**
 * Data layer for the Task & Issue module — wired to the real backend.
 *
 * Every function calls `apiFetch(...)`; the exported signatures are the contract
 * the components depend on and did not change from the mock (Phase A) version.
 * The backend response shapes mirror types.ts, so the only transform is
 * `mapDetail` (the detail flattens approval on the wire; the UI nests it) and a
 * couple of field renames on the config reads.
 */

import { ApiError, apiFetch } from "@/lib/api/client";
import { evidenceApi } from "@/lib/api/endpoints";
import type { ApiErrorBody } from "@/lib/api/types";
import { getAccessToken } from "@/lib/auth/session";
import type {
  Automation,
  CapaStatus,
  CapaType,
  Impact,
  LinkRelation,
  LinkTarget,
  Member,
  Priority,
  SavedView,
  Severity,
  SeverityMatrixCell,
  SlaDefinition,
  Task,
  TaskApproval,
  TaskComment,
  TaskDetail,
  TaskFilters,
  TaskLink,
  TaskPage,
  TaskRepeat,
  TaskStatus,
  TaskSummary,
  TaskTemplate,
  TaskTransition,
  Urgency,
} from "./types";

// -- detail mapping ----------------------------------------------------------

/** The detail exactly as the API sends it: approval is flat, and links and the
 *  template are not carried yet. Attachments and the repeat fields are. */
type RawDetail = Omit<TaskDetail, "approval" | "links" | "template_id"> & {
  approval_required: boolean;
  approval_status: TaskApproval["status"];
  approver: Member | null;
  approved_at: string | null;
  comments: (Omit<TaskComment, "author"> & { author: string | null })[];
  transitions: (Omit<TaskTransition, "actor"> & { actor: string | null })[];
  links?: TaskLink[] | null;
  template_id?: string | null;
};

function mapDetail(raw: RawDetail): TaskDetail {
  const { approval_required, approval_status, approver, approved_at, ...rest } = raw;
  return {
    ...rest,
    approval: {
      required: approval_required,
      status: approval_status,
      approver,
      decided_at: approved_at,
    },
    links: raw.links ?? [],
    template_id: raw.template_id ?? null,
    comments: raw.comments.map((c) => ({ ...c, author: c.author ?? "Unknown" })),
    transitions: raw.transitions.map((t) => ({ ...t, actor: t.actor ?? "System" })),
  } as TaskDetail;
}

// -- reads -------------------------------------------------------------------

export async function listTasks(
  filters: Partial<TaskFilters>,
  page = 1,
  pageSize = 25,
): Promise<TaskPage> {
  const p = new URLSearchParams();
  if (filters.search) p.set("search", filters.search);
  if (filters.kind && filters.kind !== "all") p.set("kind", filters.kind);
  for (const s of filters.statuses ?? []) p.append("statuses", s);
  for (const pr of filters.priorities ?? []) p.append("priorities", pr);
  for (const c of filters.categories ?? []) p.append("categories", c);
  if (filters.assignee) p.set("assignee", filters.assignee);
  if (filters.source_type) p.set("source_type", filters.source_type);
  p.set("page", String(page));
  p.set("page_size", String(pageSize));
  return apiFetch<TaskPage>(`/tasks?${p.toString()}`);
}

export async function getTask(id: string): Promise<TaskDetail | null> {
  try {
    return mapDetail(await apiFetch<RawDetail>(`/tasks/${id}`));
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) return null;
    throw e;
  }
}

export function getSummary(): Promise<TaskSummary> {
  return apiFetch<TaskSummary>("/tasks/summary");
}

type RawMember = { membership_id: string; full_name: string; email: string };
export async function listMembers(): Promise<Member[]> {
  const rows = await apiFetch<RawMember[]>("/members");
  return rows.map((m) => ({ membership_id: m.membership_id, name: m.full_name, email: m.email }));
}

export function listSlaDefinitions(): Promise<SlaDefinition[]> {
  return apiFetch<SlaDefinition[]>("/tasks/sla-definitions");
}

export function saveSlaDefinition(
  original: string | null,
  next: SlaDefinition,
): Promise<SlaDefinition[]> {
  return apiFetch<SlaDefinition[]>("/tasks/sla-definitions", {
    method: "PUT",
    body: JSON.stringify({
      original_level: original,
      level: next.level,
      respond_hours: next.respond_hours,
      resolve_hours: next.resolve_hours,
    }),
  });
}

export function deleteSlaDefinition(level: string): Promise<SlaDefinition[]> {
  return apiFetch<SlaDefinition[]>(`/tasks/sla-definitions/${encodeURIComponent(level)}`, {
    method: "DELETE",
  });
}

type RawMatrixCell = Omit<SeverityMatrixCell, "default_owner"> & {
  default_owner_membership_id: string | null;
};
function mapMatrix(rows: RawMatrixCell[]): SeverityMatrixCell[] {
  return rows.map((c) => ({
    impact: c.impact,
    urgency: c.urgency,
    severity: c.severity,
    respond_hours: c.respond_hours,
    resolve_hours: c.resolve_hours,
    default_owner: null,
    is_default: c.is_default,
  }));
}

export async function listSeverityMatrix(): Promise<SeverityMatrixCell[]> {
  return mapMatrix(await apiFetch<RawMatrixCell[]>("/tasks/severity-matrix"));
}

export async function updateMatrixCell(
  impact: SeverityMatrixCell["impact"],
  urgency: SeverityMatrixCell["urgency"],
  patch: Pick<SeverityMatrixCell, "severity" | "respond_hours" | "resolve_hours">,
): Promise<SeverityMatrixCell[]> {
  const rows = await apiFetch<RawMatrixCell[]>("/tasks/severity-matrix", {
    method: "PUT",
    body: JSON.stringify({ impact, urgency, ...patch }),
  });
  return mapMatrix(rows);
}

export function listSavedViews(): Promise<SavedView[]> {
  return apiFetch<SavedView[]>("/tasks/saved-views");
}

export function listTemplates(): Promise<TaskTemplate[]> {
  return apiFetch<TaskTemplate[]>("/tasks/templates");
}

// -- writes ------------------------------------------------------------------

/** The severity fields travel together: impact and urgency resolve through the
 *  workspace's matrix, `severity` is the person's choice, and `reason` explains a
 *  choice that differs from the matrix (an override). */
export type SeverityInput = {
  impact: Impact | null;
  urgency: Urgency | null;
  severity: Severity | null;
  reason: string | null;
};

export type CreateTaskInput = {
  task_kind: Task["task_kind"];
  title: string;
  description: string;
  priority: Priority;
  category: Task["category"];
  sla_level: string | null;
  owner_membership_id: string | null;
  assignee_ids: string[];
  due_at: string | null;
  severity: SeverityInput;
  repeat: TaskRepeat | null;
  requires_approval: boolean;
};

export async function createTask(input: CreateTaskInput): Promise<Task> {
  return mapDetail(
    await apiFetch<RawDetail>("/tasks", {
      method: "POST",
      body: JSON.stringify({
        task_kind: input.task_kind,
        title: input.title,
        description: input.description || null,
        priority: input.priority,
        category: input.category,
        sla_level: input.sla_level,
        owner_membership_id: input.owner_membership_id,
        assignee_ids: input.assignee_ids,
        due_at: input.due_at,
        impact: input.severity.impact,
        urgency: input.severity.urgency,
        severity: input.severity.severity,
        severity_reason: input.severity.reason,
        repeat: input.repeat,
        requires_approval: input.requires_approval,
      }),
    }),
  );
}

export type UpdateTaskInput = {
  title?: string;
  description?: string;
  priority?: Priority;
  category?: Task["category"];
  sla_level?: string | null;
  owner_membership_id?: string | null;
  due_at?: string | null;
  /** Replaces impact, urgency, severity and the reason together; leave it out to keep them. */
  severity?: SeverityInput;
  /** A repeat sets or changes it; null clears it. Only the first task of a series carries one. */
  repeat?: TaskRepeat | null;
  requires_approval?: boolean;
};

export async function updateTask(id: string, patch: UpdateTaskInput): Promise<TaskDetail> {
  const body: Record<string, unknown> = {};
  if (patch.title !== undefined) body.title = patch.title;
  if (patch.description !== undefined) body.description = patch.description;
  if (patch.priority !== undefined) body.priority = patch.priority;
  if (patch.category !== undefined) body.category = patch.category;
  if (patch.sla_level !== undefined) body.sla_level = patch.sla_level;
  if (patch.owner_membership_id !== undefined) {
    if (patch.owner_membership_id === null) body.clear_owner = true;
    else body.owner_membership_id = patch.owner_membership_id;
  }
  if (patch.due_at !== undefined) body.due_at = patch.due_at;
  if (patch.severity !== undefined) {
    body.impact = patch.severity.impact;
    body.urgency = patch.severity.urgency;
    body.severity = patch.severity.severity;
    body.severity_reason = patch.severity.reason;
  }
  if (patch.repeat !== undefined) {
    if (patch.repeat === null) body.clear_repeat = true;
    else body.repeat = patch.repeat;
  }
  if (patch.requires_approval !== undefined) body.requires_approval = patch.requires_approval;
  return mapDetail(await apiFetch<RawDetail>(`/tasks/${id}`, { method: "PATCH", body: JSON.stringify(body) }));
}

/** Approvals — a recurring task can require sign-off before it proceeds. */
export async function decideApproval(
  id: string,
  decision: "approved" | "rejected",
  note?: string,
): Promise<TaskDetail> {
  return mapDetail(
    await apiFetch<RawDetail>(`/tasks/${id}/approve`, {
      method: "POST",
      body: JSON.stringify({ decision, note: note ?? null }),
    }),
  );
}

/** Evidence to attach: items already in the library by id, and files to add as new evidence. */
export type AttachInput = { evidenceIds: string[]; files: File[] };

function attachForm(input: AttachInput): FormData {
  const form = new FormData();
  for (const id of input.evidenceIds) form.append("evidence_ids", id);
  for (const file of input.files) form.append("files", file);
  return form;
}

/** A move can carry evidence. With files it is one multipart request, so a file the
 *  server refuses stops the move instead of leaving it half done. */
export async function transitionTask(
  id: string,
  to: TaskStatus,
  note?: string,
  attach?: AttachInput,
): Promise<TaskDetail> {
  if (attach && attach.files.length > 0) {
    const form = attachForm(attach);
    form.append("to_status", to);
    if (note) form.append("note", note);
    return mapDetail(
      await apiFetch<RawDetail>(`/tasks/${id}/transition/files`, { method: "POST", body: form }),
    );
  }
  return mapDetail(
    await apiFetch<RawDetail>(`/tasks/${id}/transition`, {
      method: "POST",
      body: JSON.stringify({ to_status: to, note: note ?? null, evidence_ids: attach?.evidenceIds ?? [] }),
    }),
  );
}

/** Attach evidence to a task on its own, outside any move. Add only. */
export async function attachToTask(id: string, input: AttachInput): Promise<TaskDetail> {
  return mapDetail(
    await apiFetch<RawDetail>(`/tasks/${id}/attachments`, { method: "POST", body: attachForm(input) }),
  );
}

/** The evidence library as a picker needs it: enough to choose an item by. */
export type EvidenceOption = {
  id: string;
  title: string;
  evidence_type: string;
  kind: "file" | "link";
  freshness: "current" | "aging" | "stale" | "no_expiry";
};

export async function listEvidenceOptions(): Promise<EvidenceOption[]> {
  const rows = await evidenceApi.list();
  return rows.map((e) => ({
    id: e.id,
    title: e.title,
    evidence_type: e.evidence_type,
    kind: e.kind,
    freshness: e.freshness,
  }));
}

/** The download route is authenticated, so a bare link would 401: the file goes
 *  through the bearer token into a blob, and a refusal reads as the API's own copy. */
export function fetchAttachmentBlob(taskId: string, evidenceId: string): () => Promise<Blob> {
  return async () => {
    const response = await fetch(`/api/v1/tasks/${taskId}/attachments/${evidenceId}/download`, {
      headers: { Authorization: `Bearer ${getAccessToken() ?? ""}` },
    });
    if (response.ok) return response.blob();
    let body: ApiErrorBody;
    try {
      body = (await response.json()) as ApiErrorBody;
    } catch {
      body = {
        error: {
          code: "http_error",
          message: "Something went wrong. Try again, or contact support if it continues.",
          correlation_id: "unknown",
        },
      };
    }
    throw new ApiError(response.status, body);
  };
}

export async function addComment(id: string, body: string): Promise<TaskDetail> {
  return mapDetail(
    await apiFetch<RawDetail>(`/tasks/${id}/comments`, {
      method: "POST",
      body: JSON.stringify({ body }),
    }),
  );
}

export async function addSubtask(parentId: string, title: string): Promise<TaskDetail> {
  return mapDetail(
    await apiFetch<RawDetail>(`/tasks/${parentId}/subtasks`, {
      method: "POST",
      body: JSON.stringify({ title }),
    }),
  );
}

export async function setAssignees(id: string, memberIds: string[]): Promise<TaskDetail> {
  return mapDetail(
    await apiFetch<RawDetail>(`/tasks/${id}/assign`, {
      method: "POST",
      body: JSON.stringify({ membership_ids: memberIds }),
    }),
  );
}

// -- links (cross-module catalogue is a later phase) -------------------------

export async function listLinkCatalog(): Promise<Record<LinkTarget, { id: string; label: string }[]>> {
  return {
    control: [],
    framework: [],
    evidence: [],
    document: [],
    asset: [],
    risk: [],
    vendor: [],
    vulnerability: [],
  };
}

export function addTaskLink(
  id: string,
  input: { to_type: LinkTarget; to_id: string; to_label: string; relation: LinkRelation },
): Promise<TaskDetail> {
  return Promise.reject(new Error(`Linking a ${input.to_type} to ${id} arrives with the connected modules.`));
}

export function removeTaskLink(id: string, linkId: string): Promise<TaskDetail> {
  return Promise.reject(new Error(`Removing link ${linkId} from ${id} arrives with the connected modules.`));
}

// -- CAPA actions (issues only) ----------------------------------------------

export type CapaInput = {
  action_type: CapaType;
  title: string;
  description: string;
  owner_membership_id: string | null;
  due_at: string | null;
};

export async function addCapaAction(taskId: string, input: CapaInput): Promise<TaskDetail> {
  return mapDetail(
    await apiFetch<RawDetail>(`/tasks/${taskId}/actions`, {
      method: "POST",
      body: JSON.stringify({
        action_type: input.action_type,
        title: input.title,
        description: input.description || null,
        owner_membership_id: input.owner_membership_id,
        due_at: input.due_at,
      }),
    }),
  );
}

export async function updateCapaAction(
  taskId: string,
  actionId: string,
  patch: Partial<CapaInput>,
): Promise<TaskDetail> {
  const body: Record<string, unknown> = {};
  if (patch.action_type !== undefined) body.action_type = patch.action_type;
  if (patch.title !== undefined) body.title = patch.title;
  if (patch.description !== undefined) body.description = patch.description;
  if (patch.owner_membership_id !== undefined) {
    if (patch.owner_membership_id === null) body.clear_owner = true;
    else body.owner_membership_id = patch.owner_membership_id;
  }
  if (patch.due_at !== undefined) body.due_at = patch.due_at;
  return mapDetail(
    await apiFetch<RawDetail>(`/tasks/${taskId}/actions/${actionId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  );
}

export async function transitionCapaAction(
  taskId: string,
  actionId: string,
  to: CapaStatus,
): Promise<TaskDetail> {
  return mapDetail(
    await apiFetch<RawDetail>(`/tasks/${taskId}/actions/${actionId}/transition`, {
      method: "POST",
      body: JSON.stringify({ to_status: to }),
    }),
  );
}

/** Spin a CAPA action out into its own task, linked back to the issue. Idempotent. */
export async function promoteCapaToTask(taskId: string, actionId: string): Promise<TaskDetail> {
  return mapDetail(
    await apiFetch<RawDetail>(`/tasks/${taskId}/actions/${actionId}/promote`, { method: "POST" }),
  );
}

// -- automations -------------------------------------------------------------

export function listAutomations(): Promise<Automation[]> {
  return apiFetch<Automation[]>("/tasks/automations");
}

export type AutomationPatch = Partial<
  Pick<Automation, "enabled" | "owner_rule" | "priority" | "due_in_days" | "creates">
>;

export function updateAutomation(id: string, patch: AutomationPatch): Promise<Automation> {
  return apiFetch<Automation>(`/tasks/automations/${id}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}
