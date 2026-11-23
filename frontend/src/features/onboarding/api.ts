import { apiFetch } from "@/lib/api/client";

/**
 * Get Started. Every state is computed on the server from the workspace's records
 * (`GET /onboarding/status`); the only thing a person stores here is a skip with a
 * reason. Types mirror `backend/src/verity/modules/onboarding/schemas.py`.
 */

export type StepState = "not_started" | "in_progress" | "done" | "skipped" | "not_permitted";

export type StepPhase = "describe" | "organise" | "assess" | "build" | "operate" | "check" | "audit";

export type FrameworkFigures = {
  code: string;
  name: string;
  scope_model: "categories" | "applicability";
  scope_set: boolean;
  audit_type: string | null;
  window_start: string | null;
  window_end: string | null;
  audit_on: string | null;
  certification_body: string | null;
  as_of_date: string | null;
  target_date: string | null;
  live_date: string | null;
  assessor: "chosen" | "undecided" | "unknown";
  requirements_total: number;
  requirements_supported: number;
  requirements_met: number;
  controls_total: number;
  controls_owned: number;
  controls_evidenced: number;
  checks_passing: number;
  checks_failing: number;
  decisions_total: number;
  decisions_reviewed: number;
};

export type StepSkip = {
  by_membership_id: string | null;
  by_name: string | null;
  at: string;
  reason: string;
};

export type OnboardingStep = {
  key: string;
  step: string;
  phase: StepPhase;
  title: string;
  /** Set when the step belongs to one framework; null for a shared step. */
  framework_code: string | null;
  /** The frameworks a shared step counts for, shown as chips. */
  frameworks: string[];
  state: StepState;
  done_count: number | null;
  total_count: number | null;
  detail: string | null;
  link: string;
  can_act: boolean;
  skip: StepSkip | null;
};

export type PlanMilestone = {
  kind: string;
  label: string;
  planned_on: string | null;
  actual_on: string | null;
  from_engagement: boolean;
};

export type OnboardingStatus = {
  /** Null when the caller's role cannot read frameworks. */
  frameworks: FrameworkFigures[] | null;
  steps: OnboardingStep[];
  next_key: string | null;
  phases: StepPhase[];
  /** Per framework code, the audit plan for the timeline. */
  milestones: Record<string, PlanMilestone[]>;
};

export const ONBOARDING_STATUS_KEY = "onboarding-status";

export const onboardingApi = {
  status: () => apiFetch<OnboardingStatus>("/onboarding/status"),
  skip: (key: string, reason: string) =>
    apiFetch<void>(`/onboarding/steps/${encodeURIComponent(key)}/skip`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
  reopen: (key: string) =>
    apiFetch<void>(`/onboarding/steps/${encodeURIComponent(key)}/reopen`, { method: "POST" }),
  proposals: () => apiFetch<Proposals>("/onboarding/proposals"),
  decide: (body: { keys: string[]; accept: boolean; reason?: string; bulk?: boolean }) =>
    apiFetch<{ decided: number }>("/onboarding/proposals/decide", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  baseline: () => apiFetch<BaselineView>("/onboarding/baseline"),
  answer: (controlId: string, answer: BaselineAnswer, note?: string) =>
    apiFetch<void>(`/onboarding/baseline/controls/${controlId}`, {
      method: "PUT",
      body: JSON.stringify({ answer, note: note ?? null }),
    }),
  completeBaseline: () => apiFetch<BaselineView>("/onboarding/baseline/complete", { method: "POST" }),
  plan: () => apiFetch<PlanView>("/onboarding/plan"),
  approvePlan: () => apiFetch<{ raised: number }>("/onboarding/plan/approve", { method: "POST" }),
  connections: () => apiFetch<ConnectionSuggestion[]>("/onboarding/connections"),
  assist: (kind: AssistKind, subject?: string) =>
    apiFetch<AssistDraft>("/onboarding/assist", {
      method: "POST",
      body: JSON.stringify({ kind, subject: subject ?? null }),
    }),
  setup: () => apiFetch<SetupView>("/onboarding/setup"),
  saveSetup: (body: { start_point?: "fresh" | "existing"; setup_step?: string; complete?: boolean }) =>
    apiFetch<SetupView>("/onboarding/setup", { method: "PUT", body: JSON.stringify(body) }),
};

export type Proposal = {
  key: string;
  rule_key: string;
  kind: "control_status" | "iso_applicability" | "soc2_category";
  subject: string;
  subject_name: string;
  change: string;
  because: string;
  reason: string;
  bulk_ok: boolean;
  framework: string | null;
  state: "open" | "accepted" | "rejected" | "review_needed";
  decided_by_name: string | null;
  decided_at: string | null;
};

export type Proposals = { proposals: Proposal[]; open: number; review_needed: number };

export type BaselineAnswer = "in_place" | "partly" | "not_in_place" | "not_sure";

export type BaselineView = {
  id: string | null;
  status: "none" | "open" | "complete";
  families: {
    family: string;
    answered: number;
    controls: { id: string; code: string; name: string; answer: BaselineAnswer | null; note: string | null }[];
  }[];
  answered: number;
  total: number;
  counts: Record<BaselineAnswer, number>;
  completed_at: string | null;
};

export type PlanView = {
  items: {
    key: string;
    kind: "put_in_place" | "evidence";
    title: string;
    control_code: string;
    owner_membership_id: string | null;
    due_on: string | null;
    raised: boolean;
  }[];
  raised: number;
  due_on: string | null;
  due_label: string | null;
};

export type SetupView = {
  start_point: "fresh" | "existing" | null;
  setup_step: string | null;
  completed_at: string | null;
  steps: string[];
};


export type ConnectionSuggestion = {
  key: string;
  name: string;
  because: string;
  status: "available" | "planned" | "not_planned";
  connected: boolean;
};

export type AssistKind =
  | "scope_statement"
  | "description_section"
  | "control_explanation"
  | "proposal_reason"
  | "document_tailoring";

export type AssistDraft = {
  kind: AssistKind;
  source: "ai" | "template";
  text: string;
  notice: string | null;
  model: string | null;
  prompt_version: string;
  at: string;
};
