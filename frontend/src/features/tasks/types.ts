/**
 * Task & Issue Management — typed contracts for the UI/UX build (Phase A).
 *
 * The screens are built against an in-memory mock (mock.ts, read through api.ts)
 * so the whole module is clickable and reviewable before the backend exists.
 * These shapes are the contract the real API will fill at Phase C — so swapping
 * mock → real stays a one-file change in api.ts, exactly as the documents module
 * did it.
 *
 * Decisions encoded here (see the published build plan):
 *   D1  one entity, `task_kind` discriminates task vs issue
 *   D2  a single `status`; `allowed_transitions` is served, never hardcoded in UI
 *   D3  `sla_due_at` is stored; `sla_state` is computed for display, never stored
 *   D4  history is columnar (field/old/new), not a JSON blob
 *   D7  severity comes from the impact×urgency matrix, override needs a reason
 *   D9  many assignees + one accountable owner
 */

// -- enumerations ------------------------------------------------------------

export const TASK_KINDS = ["task", "issue"] as const;
export type TaskKind = (typeof TASK_KINDS)[number];

/** `blocked` stops the SLA clock; `cancelled` is terminal and needs a reason
 *  (rule 6 — compliance objects are never hard-deleted). */
export const TASK_STATUSES = [
  "open",
  "in_progress",
  "blocked",
  "under_review",
  "closed",
  "cancelled",
] as const;
export type TaskStatus = (typeof TASK_STATUSES)[number];

export const PRIORITIES = ["critical", "high", "medium", "low"] as const;
export type Priority = (typeof PRIORITIES)[number];

/** Matrix inputs — issue kind only. */
export const IMPACTS = ["high", "medium", "low"] as const;
export type Impact = (typeof IMPACTS)[number];
export const URGENCIES = ["high", "medium", "low"] as const;
export type Urgency = (typeof URGENCIES)[number];

/** Resolved severity — the matrix output, or an override. */
export const SEVERITIES = ["critical", "high", "medium", "low", "informational"] as const;
export type Severity = (typeof SEVERITIES)[number];

export const CATEGORIES = [
  "security",
  "privacy",
  "operations",
  "data",
  "regulatory",
  "vendor",
  "other",
] as const;
export type Category = (typeof CATEGORIES)[number];

export type ApprovalStatus = "not_required" | "pending" | "approved" | "rejected";

/** Computed on read from `sla_due_at` against the clock (D3). `none` = no SLA
 *  applies; `paused` = the task is blocked. */
export type SlaState = "none" | "on_track" | "due_soon" | "breached" | "paused";

/** The objects a task can link to through the polymorphic `links` table (D5). */
export const LINK_TARGETS = [
  "control",
  "framework",
  "evidence",
  "document",
  "asset",
  "risk",
  "vendor",
  "vulnerability",
] as const;
export type LinkTarget = (typeof LINK_TARGETS)[number];

/** Which link targets are backed by a shipped module today. The rest render as
 *  "Soon" in the picker and light up the moment their module lands. */
export const LINK_TARGETS_LIVE: readonly LinkTarget[] = [
  "control",
  "framework",
  "evidence",
  "document",
  "asset",
];

export const LINK_TARGET_LABEL: Record<LinkTarget, string> = {
  control: "Control",
  framework: "Framework",
  evidence: "Evidence",
  document: "Document",
  asset: "Asset",
  risk: "Risk",
  vendor: "Vendor",
  vulnerability: "Vulnerability",
};

export const LINK_RELATIONS = ["relates_to", "remediates", "caused_by", "depends_on", "duplicates"] as const;
export type LinkRelation = (typeof LINK_RELATIONS)[number];

// -- people ------------------------------------------------------------------

/** Always a tenant membership, never a global user (rule 3). */
export type Member = {
  membership_id: string;
  name: string;
  email?: string;
};

// -- the task ----------------------------------------------------------------

/** The register row: everything a list or board cell needs, and nothing it
 *  doesn't. Detail extends this. */
export type Task = {
  id: string;
  code: string; // TSK-0001
  task_kind: TaskKind;
  title: string;
  status: TaskStatus;
  priority: Priority;
  /** Resolved severity for issues; null for plain tasks that use priority alone. */
  severity: Severity | null;
  category: Category;

  owner: Member | null;
  assignees: Member[];

  sla_level: string | null;
  /** The stored deadline. `sla_state` is derived from it and the clock. */
  sla_due_at: string | null;
  sla_state: SlaState;

  detected_at: string | null;
  due_at: string | null;
  created_at: string;
  updated_at: string;

  /** Present on a recurring task; a plain summary string for the row badge. */
  recurrence_summary: string | null;
  parent_task_id: string | null;

  /** Provenance — set when a task was raised from another object (rule 9). */
  source: LinkTarget | "manual" | "capa";

  // Counts for register/detail badges, so a row needs no extra fetch.
  subtask_count: number;
  comment_count: number;
  link_count: number;
  attachment_count: number;
};

/** One immutable history row — columnar (D4), so "who changed the assignee"
 *  is a filter, not a JSON parse. */
export type TaskTransition = {
  id: string;
  actor: string;
  field_changed: string; // "status", "priority", "assignee", "created", …
  old_value: string | null;
  new_value: string | null;
  note: string | null;
  occurred_at: string;
};

export type TaskComment = {
  id: string;
  author: string;
  body: string;
  created_at: string;
};

export type TaskLink = {
  id: string;
  to_type: LinkTarget;
  to_id: string;
  to_label: string; // e.g. "CC6.1 · Logical access controls"
  relation: string; // "relates_to", "remediates", "caused_by"
  note: string | null;
};

export type TaskAttachment = {
  id: string;
  filename: string;
  size_bytes: number;
  uploaded_by: string;
  uploaded_at: string;
  /** Set when the file was attached as part of a transition, not standalone. */
  transition_id: string | null;
};

export type TaskApproval = {
  required: boolean;
  status: ApprovalStatus;
  approver: Member | null;
  decided_at: string | null;
};

// -- CAPA (issues only) ------------------------------------------------------

/** Corrective and Preventive Action — the remediation actions under an issue. */
export const CAPA_TYPES = ["corrective", "preventive", "containment", "verification"] as const;
export type CapaType = (typeof CAPA_TYPES)[number];

export const CAPA_STATUSES = ["planned", "in_progress", "blocked", "completed", "verified", "cancelled"] as const;
export type CapaStatus = (typeof CAPA_STATUSES)[number];

/** The legal moves out of each CAPA status; served, never hardcoded in the UI. */
export const CAPA_TRANSITIONS: Record<CapaStatus, CapaStatus[]> = {
  planned: ["in_progress", "cancelled"],
  in_progress: ["blocked", "completed", "cancelled"],
  blocked: ["in_progress", "cancelled"],
  completed: ["verified", "in_progress"], // verify, or reopen
  verified: ["in_progress"], // reopen
  cancelled: ["planned"], // reinstate
};

export type CapaAction = {
  id: string;
  action_type: CapaType;
  title: string;
  description: string;
  owner: Member | null;
  due_at: string | null;
  status: CapaStatus;
  completed_at: string | null;
  verified_by: Member | null;
  verified_at: string | null;
  /** True for the action auto-created when an issue is raised from an event. */
  auto_generated: boolean;
  /** Set once this action has been promoted into its own task. */
  promoted_task_code: string | null;
  created_at: string;
};

/** The extra detail one task carries beyond the register row. */
export type TaskDetail = Task & {
  description: string;

  // Issue severity machinery (D7).
  impact: Impact | null;
  urgency: Urgency | null;
  severity_override: Severity | null;
  severity_override_reason: string | null;

  reporter: Member | null;

  started_at: string | null;
  resolved_at: string | null;
  closed_at: string | null;
  closure_note: string | null;
  cancelled_reason: string | null;

  approval: TaskApproval;

  recurrence_rule: string | null;
  recurrence_parent_id: string | null;
  next_occurrence_at: string | null;
  template_id: string | null;

  subtasks: Task[];
  comments: TaskComment[];
  transitions: TaskTransition[];
  links: TaskLink[];
  attachments: TaskAttachment[];
  watchers: Member[];
  /** Remediation actions — issues only; empty on a task. */
  capa_actions: CapaAction[];

  /** Served by the API (D2) — the buttons the current user may press now. */
  allowed_transitions: TaskStatus[];
};

// -- configuration -----------------------------------------------------------

export type SlaDefinition = {
  level: string;
  respond_hours: number;
  resolve_hours: number;
};

export type SeverityMatrixCell = {
  impact: Impact;
  urgency: Urgency;
  severity: Severity;
  respond_hours: number;
  resolve_hours: number;
  default_owner: Member | null;
  /** True when this cell is inherited from the built-in default, not tenant-set. */
  is_default: boolean;
};

export type TaskTemplate = {
  id: string;
  name: string;
  task_kind: TaskKind;
  priority: Priority;
  category: Category;
  sla_level: string | null;
  description: string;
  subtasks: string[];
  recurrence_rule: string | null;
};

// -- automations -------------------------------------------------------------

/** Who the auto-created task/issue is assigned to when the rule fires. */
export const AUTOMATION_OWNER_RULES = ["source_owner", "unassigned"] as const;
export type AutomationOwnerRule = (typeof AUTOMATION_OWNER_RULES)[number];

/**
 * A curated, built-in rule that opens a task or issue when something happens in
 * another module. The catalogue is fixed (this is the "toggles first" model — a
 * free-form rule builder comes later); each row is switched on/off and tuned.
 */
export type Automation = {
  id: string;
  name: string;
  /** Plain sentence describing when it fires, shown read-only. */
  trigger: string;
  /** The module the trigger watches — an unavailable one shows as "Soon". */
  source: LinkTarget;
  /** Human phrase for the source_owner option, e.g. "the control's owner". */
  owner_label: string;
  creates: TaskKind;
  enabled: boolean;
  owner_rule: AutomationOwnerRule;
  priority: Priority;
  /** Days from firing to the due date on the created item. */
  due_in_days: number;
  /** False until the watched module ships; such a rule can't be enabled yet. */
  available: boolean;
};

// -- filtering & views -------------------------------------------------------

export type TaskFilters = {
  search: string;
  kind: TaskKind | "all";
  statuses: TaskStatus[];
  priorities: Priority[];
  categories: Category[];
  assignee: string | null; // membership_id, or "me", or "unassigned"
  sla_state: SlaState | "all";
  source_type: LinkTarget | null;
  source_id: string | null;
};

export type SavedView = {
  id: string;
  name: string;
  filters: Partial<TaskFilters>;
  is_shared: boolean;
  position: number;
};

// -- dashboard ---------------------------------------------------------------

export type MttrPoint = {
  severity: Severity;
  days: number;
  /** Sample size ships with the mean — a 3-day MTTR from one sample is not
   *  trustworthy and the operator deserves to see that. */
  count: number;
};

export type TaskSummary = {
  open_total: number;
  open_by_priority: Record<Priority, number>;
  breaching_now: number;
  due_soon: number;
  /** Open tasks by age band, in days. */
  ageing: { band: string; count: number }[];
  /** Closed in the trailing window. */
  throughput: number;
  by_assignee: { member: Member; open: number }[];
  mttr: MttrPoint[];
};

// -- list envelope -----------------------------------------------------------

export type TaskPage = {
  items: Task[];
  total: number;
};
