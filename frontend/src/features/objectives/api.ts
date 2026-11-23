import { apiFetch } from "@/lib/api/client";

/**
 * Assessment objectives (guided onboarding AO-1 to AO-5). Outcomes are derived on the server
 * from documents, tagged evidence and checks; nothing here changes readiness. Types mirror
 * `backend/src/verity/modules/objectives/schemas.py`.
 */

export type Outcome = "satisfied" | "not_satisfied" | "not_applicable" | "not_tested";

export type NextStep = { action: string; label: string; link: string; artifact_key: string | null };

export type ObjectiveArtifact = {
  key: string;
  code: string;
  name: string;
  category: string;
  state: "satisfied" | "not_satisfied";
  reason: string | null;
  sources: string[];
};

export type Objective = {
  code: string;
  key: string;
  statement: string;
  assurance: "design" | "operating";
  methods: string[];
  interview_with: string[];
  outcome: Outcome;
  reason: string | null;
  artifacts: ObjectiveArtifact[];
  next_step: NextStep | null;
  not_applicable_reason: string | null;
};

export type ControlObjectives = {
  control_id: string;
  code: string;
  name: string;
  frameworks: string[];
  objectives: Objective[];
  design_ready: boolean;
  operating_ready: boolean;
  ready: boolean;
  ready_today: boolean;
  review_status: string;
};

export type FrameworkObjectives = {
  code: string;
  name: string;
  audit_type: string | null;
  controls: number;
  design_ready: number;
  operating_ready: number;
  objectives_total: number;
  objectives_satisfied: number;
  first_audit_ready: number;
  first_audit_label: string;
  first_audit_notes: string[];
};

export type ObjectivesOverview = {
  frameworks: FrameworkObjectives[];
  controls_with_objectives: number;
  controls_total: number;
  next: { control_id: string; control_code: string; control_name: string; objective: Objective }[];
  review_status: string;
};

export type Comparison = {
  rows: {
    control_id: string;
    code: string;
    name: string;
    ready_today: boolean;
    ready_rule_a: boolean;
    ready_rule_b: boolean;
    blocking: string[];
  }[];
  compared: number;
  differ_rule_a: number;
  differ_rule_b: number;
};

export const objectivesApi = {
  overview: () => apiFetch<ObjectivesOverview>("/objectives"),
  comparison: () => apiFetch<Comparison>("/objectives/comparison"),
  forControl: (id: string) => apiFetch<ControlObjectives | null>(`/objectives/controls/${id}`),
  notApplicable: (code: string, reason: string) =>
    apiFetch<void>(`/objectives/${code}/not-applicable`, { method: "POST", body: JSON.stringify({ reason }) }),
  appliesAgain: (code: string) => apiFetch<void>(`/objectives/${code}/applies-again`, { method: "POST" }),
  tag: (artifact: string, evidenceId: string, on = true) =>
    apiFetch<void>(`/objectives/artifacts/${artifact}/evidence`, {
      method: "PUT",
      body: JSON.stringify({ evidence_id: evidenceId, on }),
    }),
};

export const OUTCOME: Record<Outcome, { family: "success" | "warning" | "neutral" | "pending"; label: string }> = {
  satisfied: { family: "success", label: "Met" },
  not_satisfied: { family: "warning", label: "Not met" },
  not_applicable: { family: "neutral", label: "Not applicable" },
  not_tested: { family: "pending", label: "Nothing yet" },
};

export const REASON: Record<string, string> = {
  deviation: "A check found a problem",
  insufficient_information: "A check could not be read",
  stale: "The record is out of date",
  awaiting_review: "Filed, waiting for review",
  missing: "Nothing filed yet",
};
