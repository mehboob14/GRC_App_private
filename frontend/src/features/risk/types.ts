import type { Appetite, ScoringFormula } from "./scoring";
/** Mirrors backend `modules/risk/schemas.py`. */

export type RiskStatus = "open" | "in_treatment" | "mitigated" | "accepted" | "closed";
export type Treatment = "mitigate" | "accept" | "avoid" | "transfer";
export type BandKey = "low" | "medium" | "high" | "critical";

export const REGISTER_TYPES = [
  "enterprise",
  "rcsa",
  "iso_27001",
  "soc_2",
  "pci_dss",
  "sox",
  "gdpr",
  "nist_csf",
  "sama_csf",
  "internal",
  "project",
  "third_party",
  "other",
] as const;
export type RegisterType = (typeof REGISTER_TYPES)[number];

export type ScaleLevel = { level: number; label: string; description: string };
export type Band = { key: BandKey; label: string; min_score: number };

export type Category = {
  id: string;
  name: string;
  position: number;
  archived: boolean;
  risk_count: number;
  children: Category[];
};

export type Register = {
  id: string;
  name: string;
  register_type: RegisterType;
  description: string | null;
  owner_membership_id: string | null;
  owner_name: string | null;
  is_default: boolean;
  status: "active" | "archived";
  likelihood_levels: number;
  impact_levels: number;
  likelihood_scale: ScaleLevel[];
  impact_scale: ScaleLevel[];
  severity_bands: Band[];
  review_cadence_days: number;
  risk_count: number;
  categories: Category[];
  created_at: string;
  scoring_formula: ScoringFormula;
  appetite: Appetite;
  max_score: number;
};

export type RegisterInput = {
  name: string;
  register_type: RegisterType;
  description?: string | null;
  owner_membership_id?: string | null;
  likelihood_levels?: number;
  impact_levels?: number;
  likelihood_scale?: { label: string; description: string }[];
  impact_scale?: { label: string; description: string }[];
  severity_bands?: Band[];
  review_cadence_days?: number;
  is_default?: boolean;
  status?: "active" | "archived";
  scoring_formula?: ScoringFormula;
  appetite?: Appetite;
};

export type CategoryNode = { id?: string; name: string; children: { id?: string; name: string }[] };

export type Person = { membership_id: string; name: string };

export type Attention =
  | "no_controls"
  | "review_overdue"
  | "treatment_overdue"
  | "unscored"
  | "unowned"
  | "acceptance_pending"
  | "acceptance_expiring";

export type Risk = {
  id: string;
  register_id: string;
  code: string;
  title: string;
  description: string;
  category_id: string;
  category_name: string;
  sub_category_id: string | null;
  sub_category_name: string | null;
  status: RiskStatus;
  treatment: Treatment | null;
  inherent_likelihood: number | null;
  inherent_impact: number | null;
  inherent_score: number | null;
  inherent_band: BandKey | null;
  residual_likelihood: number | null;
  residual_impact: number | null;
  residual_score: number | null;
  residual_band: BandKey | null;
  owner: Person | null;
  department_group_id: string | null;
  department_name: string | null;
  treatment_due_on: string | null;
  next_review_on: string | null;
  last_reviewed_at: string | null;
  origin: "manual" | "library" | "import" | "vendor_finding" | "assessment";
  control_count: number;
  attention: Attention[];
  created_at: string;
  updated_at: string;
  appetite_status: "within" | "tolerated" | "breach" | null;
  custom_fields: Record<string, string | number | boolean>;
};

export type RiskPage = { items: Risk[]; total: number };

export type ControlRef = {
  id: string;
  code: string;
  name: string;
  status: string;
  category: string;
  disabled: boolean;
};

export type LinkType = "asset" | "vulnerability" | "evidence" | "task" | "vendor" | "document";

export type LinkedRecord = {
  link_id: string;
  target_type: LinkType;
  target_id: string;
  relation: string;
  code: string;
  title: string;
  status: string;
  detail: string | null;
};

export type Action = {
  link_id: string;
  task_id: string;
  code: string;
  title: string;
  status: string;
  priority: string;
  owner_name: string | null;
  due_at: string | null;
};

export type AcceptanceStatus = "pending" | "active" | "rejected" | "withdrawn" | "expired" | "revoked";

export type Acceptance = {
  id: string;
  status: AcceptanceStatus;
  rationale: string;
  expires_on: string;
  requested_by: Person | null;
  approver: Person | null;
  residual_score_at_request: number | null;
  decided_at: string | null;
  decision_note: string | null;
  revoked_at: string | null;
  revoke_reason: string | null;
  created_at: string;
};

export type RiskEvent = {
  id: string;
  kind: string;
  from_value: string | null;
  to_value: string | null;
  note: string | null;
  inherent_score: number | null;
  residual_score: number | null;
  actor_name: string | null;
  created_at: string;
};

export type RiskDetail = Risk & {
  root_cause: string | null;
  consequences: string | null;
  recommendations: string | null;
  treatment_plan: string | null;
  closure_justification: string | null;
  closed_at: string | null;
  template_code: string | null;
  origin_ref: string | null;
  created_by_name: string | null;
  allowed_statuses: RiskStatus[];
  controls: ControlRef[];
  links: LinkedRecord[];
  actions: Action[];
  acceptances: Acceptance[];
  history: RiskEvent[];
};

export type RiskInput = {
  register_id: string;
  title: string;
  description: string;
  category_id: string;
  sub_category_id: string | null;
  status: RiskStatus;
  treatment: Treatment | null;
  inherent_likelihood: number | null;
  inherent_impact: number | null;
  residual_likelihood: number | null;
  residual_impact: number | null;
  root_cause: string | null;
  consequences: string | null;
  recommendations: string | null;
  treatment_plan: string | null;
  owner_membership_id: string | null;
  department_group_id: string | null;
  treatment_due_on: string | null;
  next_review_on: string | null;
  asset_ids: string[] | null;
  custom_fields?: Record<string, string | number | boolean> | null;
};

export type RiskFilters = {
  search: string;
  statuses: string[];
  bands: string[];
  category_ids: string[];
  treatments: string[];
  owner: string | null;
  department_ids: string[];
  attention: string[];
  cell: string | null;
  /** "field key:value" pairs for the workspace's own choice fields. */
  custom: string[];
};

export type RiskSort = "code" | "title" | "inherent" | "residual" | "status" | "next_review" | "updated";

export type Summary = {
  register_id: string;
  total: number;
  closed: number;
  likelihood_levels: number;
  impact_levels: number;
  heatmap_inherent: number[][];
  heatmap_residual: number[][];
  by_band: Record<string, number>;
  by_appetite?: Record<string, number>;
  by_status: Record<string, number>;
  by_treatment: Record<string, number>;
  by_category: { name: string; count: number }[];
  attention: Record<string, number>;
  top_risks: Risk[];
};

export type Options = {
  members: { membership_id: string; name: string; email: string }[];
  business_units: { id: string; name: string }[];
};

export type Approver = { membership_id: string; name: string; eligible: boolean; reason: string | null };

export type LibraryTemplate = {
  id: string;
  code: string;
  title: string;
  description: string;
  category: string;
  sub_category: string | null;
  default_likelihood: number;
  default_impact: number;
  root_cause: string | null;
  consequences: string | null;
  recommendations: string | null;
  treatment: Treatment | null;
  control_keys: string[];
  frameworks: string[];
  adopted: boolean;
};

export type ImportRow = {
  row_number: number;
  title: string;
  description: string;
  category_id: string | null;
  category_name: string | null;
  sub_category_id: string | null;
  sub_category_name: string | null;
  status: RiskStatus;
  owner_membership_id: string | null;
  owner_name: string | null;
  department_group_id: string | null;
  department_name: string | null;
  inherent_likelihood: number | null;
  inherent_impact: number | null;
  residual_likelihood: number | null;
  residual_impact: number | null;
  root_cause: string | null;
  consequences: string | null;
  recommendations: string | null;
  treatment: Treatment | null;
  treatment_plan: string | null;
  treatment_due_on: string | null;
  next_review_on: string | null;
  custom_fields?: Record<string, string | number | boolean>;
  errors: string[];
  warnings: string[];
};

export type ImportPreview = { rows: ImportRow[]; valid: number; invalid: number };
export type ImportResult = { created: number; failed: { row_number: number; error: string }[] };

export type AssistDraft = {
  source: "ai" | "library" | "none";
  description: string | null;
  root_cause: string | null;
  consequences: string | null;
  recommendations: string | null;
  treatment_plan: string | null;
  treatment: Treatment | null;
  category_id: string | null;
  sub_category_id: string | null;
  inherent_likelihood: number | null;
  inherent_impact: number | null;
  residual_likelihood: number | null;
  residual_impact: number | null;
  similar: { code: string; title: string }[];
};
