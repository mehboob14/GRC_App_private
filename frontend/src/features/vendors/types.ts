/**
 * Third-party risk types (Week 5).
 *
 * Hand-written mirrors of `backend/src/verity/modules/vendors/schemas.py`.
 * Field names are the wire names — snake_case, no mapping layer. `| null` is a
 * nullable response field; `?` is an optional request field.
 */

// -- vocabularies -------------------------------------------------------------
// Iterable arrays where the UI needs to map over them; the union is derived so
// the two can never disagree.

export const VENDOR_TYPES = ["vendor", "supplier", "contractor", "partner"] as const;
export type VendorType = (typeof VENDOR_TYPES)[number];

export const LIFECYCLE_STATUSES = [
  "requested",
  "under_review",
  "approved",
  "active",
  "flagged",
  "on_hold",
  "offboarding",
  "terminated",
  "archived",
] as const;
export type LifecycleStatus = (typeof LIFECYCLE_STATUSES)[number];

export const TIERS = ["critical", "high", "medium", "low"] as const;
export type Tier = (typeof TIERS)[number];

export const DATA_CLASSIFICATIONS = ["public", "internal", "confidential", "restricted"] as const;
export type DataClassification = (typeof DATA_CLASSIFICATIONS)[number];

export const CONTACT_TYPES = ["security", "privacy", "commercial", "portal"] as const;
export type ContactType = (typeof CONTACT_TYPES)[number];

/** The twelve stages, in lifecycle order. `approval` is the only gate. */
export const STAGES = [
  "intake",
  "tiering",
  "diligence",
  "questionnaire",
  "scoring",
  "findings",
  "contracting",
  "approval",
  "onboarding",
  "monitoring",
  "reassessment",
  "offboarding",
] as const;
export type Stage = (typeof STAGES)[number];

export type StageStatus = "not_started" | "in_progress" | "complete" | "skipped";
export type StageTransition = "advance" | "send_back" | "skip";

/** The five tiering factors, in the order the form asks them. */
export const TIERING_FACTORS = [
  "data_sensitivity",
  "business_criticality",
  "system_access",
  "regulatory_scope",
  "fourth_party_reliance",
] as const;
export type TieringFactorKey = (typeof TIERING_FACTORS)[number];

export type AssessmentStatus = "pending" | "in_progress" | "submitted" | "expired" | "scored";
export type AssessmentKind = "initial" | "reassessment";
export type ReviewFormat = "questionnaire" | "soc_report_review" | "external_report";
export type AssessmentDomain = "security" | "privacy" | "legal" | "esg";
export type Answer = "yes" | "partial" | "no" | "na";
export type AnswerType = "yes_no_na" | "select" | "multi_select" | "text" | "numeric";
export type ScopeLevel = "lite" | "core" | "detail";
export type Grade = "A" | "B" | "C" | "D" | "F";

export type FindingSeverity = "critical" | "high" | "medium" | "low";
export type FindingStatus = "open" | "in_remediation" | "accepted" | "closed";
export type FindingTreatment = "remediate" | "mitigate" | "transfer" | "accept";
export type FindingSource =
  | "assessment"
  | "sla_breach"
  | "signal"
  | "document_review"
  | "offboarding";

/** Four-valued, deliberately: a deferral is not a soft reject and must stay distinct. */
export type ApprovalDecision = "approve" | "approve_with_conditions" | "defer" | "reject";
export type ConditionStatus = "open" | "met" | "overdue" | "waived";

export const DOC_TYPES = [
  "soc_report",
  "iso_cert",
  "bridge_letter",
  "dpa",
  "pentest",
  "insurance",
  "financials",
  "bcdr",
  "policy",
] as const;
export type DocType = (typeof DOC_TYPES)[number];
export type CollectionStatus = "requested" | "received" | "reviewed";

export type ReportKind = "soc1" | "soc2" | "soc3";
export type ReportType = "type_i" | "type_ii";
export type SocOpinion = "unqualified" | "qualified" | "adverse" | "disclaimer";

export const CONTRACT_TYPES = ["master", "dpa", "sla", "security_addendum", "nda"] as const;
export type ContractType = (typeof CONTRACT_TYPES)[number];
export type ContractStatus = "draft" | "active" | "expired" | "terminated";

export type SubprocessorProvenance = "vendor_declared" | "auto_detected" | "intelligence";

export type Urgency = "low" | "normal" | "high";
export type ScreeningStatus = "pending" | "passed" | "flagged";
/** `auto_approved` is not `approved` — a machine decision stays distinguishable. */
export type IntakeDecision = "pending" | "approved" | "auto_approved" | "rejected";

export const ROSTER_ROLES = [
  "tprm_lead",
  "analyst",
  "security",
  "privacy",
  "legal",
  "procurement",
  "exec_approver",
  "it",
] as const;
export type RosterRole = (typeof ROSTER_ROLES)[number];

// -- register -----------------------------------------------------------------

export type Ownership = {
  business_owner_membership_id: string | null;
  business_owner_name: string | null;
  security_owner_membership_id: string | null;
  security_owner_name: string | null;
  relationship_owner_membership_id: string | null;
  relationship_owner_name: string | null;
};

export type Vendor = {
  id: string;
  name: string;
  vendor_type: string;
  industry: string | null;
  website: string | null;
  business_unit: string | null;
  services_provided: string;
  stores_pii: boolean;
  data_location: string | null;
  data_types_in_scope: string[];
  systems_in_scope: string[];
  data_classification: string | null;
  lifecycle_status: string;
  tier: string | null;
  current_residual_score: number | null;
  current_grade: string | null;
  annual_contract_value: number | null;
  ownership: Ownership;
  next_reassessment_on: string | null;
  tags: string[];
  source: string;
  created_at: string;
  updated_at: string;
  engagement_count: number;
  contact_count: number;
  /** What this vendor is waiting on, decided server-side. Null means nothing is. */
  attention_code: string | null;
};

export type Engagement = {
  id: string;
  vendor_id: string;
  name: string;
  service_description: string;
  business_unit: string | null;
  internal_owner_membership_id: string | null;
  internal_owner_name: string | null;
  tier: string | null;
  status: string;
  start_date: string | null;
  end_date: string | null;
  created_at: string;
  updated_at: string;
};

export type Contact = {
  id: string;
  vendor_id: string;
  name: string;
  email: string | null;
  phone: string | null;
  contact_type: string;
};

export type DuplicateMatch = { id: string; name: string; reason: string };

/** A questionnaire as a list row — no responses, no findings. Opening one
 *  fetches the full `Assessment`. */
export type AssessmentSummary = {
  id: string;
  engagement_id: string;
  cycle: number;
  kind: string;
  review_format: string;
  status: string;
  due_date: string | null;
  residual_score: number | null;
  grade: string | null;
  question_count: number;
  answered_count: number;
  submitted_at: string | null;
  created_at: string;
  questionnaire_id: string | null;
  questionnaire_name: string | null;
};

export type VendorDetail = Vendor & {
  engagements: Engagement[];
  contacts: Contact[];
  duplicates: DuplicateMatch[];
  stages: StageRow[];
  tierings: Tiering[];
  approvals: Approval[];
  documents: VendorDocument[];
  contracts: Contract[];
  soc_reviews: SocReview[];
  subprocessors: Subprocessor[];
  /** Newest cycle first. */
  assessments: AssessmentSummary[];
  /** Newest first. An open one has no `completed_at`. */
  offboardings: Offboarding[];
  /** Every stage move, newest first. Append-only on the server. */
  transitions: Transition[];
  /** Adverse events recorded against the vendor, newest first. */
  signals: Signal[];
  /** Committed service levels, across this vendor's contracts. */
  slas: Sla[];
};

export const SIGNAL_TYPES = [
  "breach",
  "adverse_media",
  "rating_change",
  "financial",
  "sla_breach",
  "cert_expiry",
] as const;

export const SIGNAL_SOURCE_CLASSES = [
  "internal",
  "media",
  "breach_intel",
  "rating_platform",
  "financial_provider",
] as const;

export type Signal = {
  id: string;
  vendor_id: string;
  signal_type: string;
  source_class: string;
  severity: string;
  title: string;
  detail: string;
  status: string;
  acknowledged_by_name: string | null;
  acknowledged_at: string | null;
  observed_at: string;
  created_at: string;
};

export type SignalInput = {
  signal_type: string;
  title: string;
  severity?: string;
  detail?: string;
  source_class?: string;
  observed_on?: string | null;
  /** Raise a finding with it, for a signal somebody has to act on. */
  raise_finding?: boolean;
};

export const FINDING_SEVERITIES = ["critical", "high", "medium", "low"] as const;

/** The risk domains a questionnaire scores, and so the parts a review splits into. */
export const RISK_DOMAINS = [
  { key: "information_security", label: "Information security programme" },
  { key: "access_control", label: "Access control" },
  { key: "data_protection_privacy", label: "Data protection and privacy" },
  { key: "business_continuity", label: "Business continuity and resilience" },
  { key: "incident_response", label: "Incident response" },
  { key: "secure_development", label: "Secure development" },
  { key: "infrastructure_cloud", label: "Infrastructure and cloud" },
  { key: "personnel_security", label: "Personnel security" },
  { key: "compliance_legal", label: "Compliance and legal" },
  { key: "fourth_party_management", label: "Fourth-party management" },
] as const;

export type Reviewer = {
  id: string;
  assessment_id: string;
  domain: string | null;
  domain_label: string;
  reviewer_membership_id: string;
  reviewer_name: string | null;
  status: string;
  note: string | null;
  decided_at: string | null;
};

export type Comment = {
  id: string;
  assessment_id: string;
  question_id: string | null;
  author_name: string;
  author_type: string;
  /** `vendor_shared` reaches the portal; anything else never leaves the team. */
  visibility: string;
  body: string;
  created_at: string;
};

export type AlertRule = {
  id: string;
  name: string;
  signal_types: string[];
  tier_scope: string[];
  min_severity: string;
  action: string;
  channel: string;
  is_enabled: boolean;
};

export type AlertRuleInput = Omit<AlertRule, "id">;

export const ALERT_ACTIONS = ["notify", "create_task", "trigger_reassessment"] as const;

export type DiscoveredApp = {
  id: string;
  app_name: string;
  authorizing_users: number;
  oauth_scopes: string[];
  first_seen_at: string | null;
  disposition: string;
  vendor_id: string | null;
  source: string;
  created_at: string;
};

export const DISCOVERED_DISPOSITIONS = [
  "pending",
  "added_as_vendor",
  "linked_to_vendor",
  "ignored",
] as const;

export const SLA_STATUSES = ["on_track", "at_risk", "breached"] as const;

export type Sla = {
  id: string;
  contract_id: string;
  contract_title: string | null;
  name: string;
  target: string;
  measurement: string | null;
  measured_on: string | null;
  cure_period_days: number | null;
  status: string;
};

export type SlaInput = {
  contract_id: string;
  name: string;
  target: string;
  measurement?: string | null;
  measured_on?: string | null;
  cure_period_days?: number | null;
  status?: string;
};

export type FindingInput = {
  title: string;
  detail?: string;
  severity?: string;
  engagement_id?: string | null;
  is_blocking?: boolean;
  owner_membership_id?: string | null;
};

/** The workspace's tiering policy: what the tier is worth in work. */
export type Policy = {
  tier_thresholds: Record<string, number>;
  cadence_days_by_tier: Record<string, number>;
  finding_sla_days_by_severity: Record<string, number>;
  stage_skip_matrix_by_tier: Record<string, string[]>;
  required_reviewer_roles_by_tier: Record<string, string[]>;
  /** False while the workspace is still on the shipped defaults. */
  is_customised: boolean;
  skippable_stages: string[];
  roster_roles: string[];
};

export type PolicyInput = Omit<Policy, "is_customised" | "skippable_stages" | "roster_roles">;

/** One move of the review: an advance, a send-back or a skip, with its reason. */
export type Transition = {
  id: string;
  engagement_id: string;
  cycle: number;
  action: string;
  from_stage: string | null;
  to_stage: string | null;
  reason: string | null;
  /** Null when the platform moved it rather than a person. */
  actor: string | null;
  occurred_at: string;
};

/** One exit (ER 127): four steps, each evidenced, before the vendor is archived. */
export type Offboarding = {
  id: string;
  /** Null means the whole relationship rather than one engagement. */
  engagement_id: string | null;
  reason: string;
  access_revoked_at: string | null;
  data_return_attested_at: string | null;
  contract_provisions_reviewed: boolean;
  final_payments_settled: boolean;
  notes: string | null;
  completed_at: string | null;
  created_at: string;
};

export type VendorPage = { items: Vendor[]; total: number };

/** One thing the portfolio is waiting on, and how many vendors are on it. */
export type AttentionCount = { code: string; label: string; count: number };

/**
 * The portfolio in one object, from `GET /vendors/summary`. Whole-tenant and
 * unfiltered on purpose: the overview tells a reader where to go, so a number
 * that moved when they changed a facet would answer a different question.
 */
export type VendorSummary = {
  total: number;
  mine: number;
  by_tier: Record<string, number>;
  by_status: Record<string, number>;
  attention: AttentionCount[];
  /** Vendors a reassessment cadence applies to at all. */
  coverage_in_scope: number;
  /** Of those, the ones inside their window. */
  coverage_current: number;
  findings_by_severity: Record<string, number>;
  findings_open: number;
  findings_overdue: number;
  intake_pending: number;
  /** Every live vendor with no business owner, not only those it is the top concern for. */
  unowned: number;
  critical_overdue: number;
  /** Live vendors with a scored assessment, worst residual score first, top five. */
  highest_residual: ResidualVendor[];
};

export type ResidualVendor = {
  id: string;
  name: string;
  tier: string | null;
  residual_score: number;
  grade: string | null;
};

export type StageFacet = { stage: string; label: string; is_gate: boolean; is_required: boolean };

export type TieringFactorSpec = {
  key: string;
  label: string;
  weight: number;
  scale_max: number;
};

export type VendorFacets = {
  vendor_types: string[];
  statuses: string[];
  tiers: string[];
  classifications: string[];
  contact_types: string[];
  business_units: string[];
  stages: StageFacet[];
  skip_matrix_by_tier: Record<string, string[]>;
  tiering_factors: TieringFactorSpec[];
  risk_domains: { key: string; label: string }[];
  /** Tier to the roles a review waits on. Roles, not people — the roster
   *  resolves a role to whoever holds it. */
  reviewer_roles_by_tier: Record<string, string[]>;
  tier_thresholds: Record<string, number>;
  policy_is_customised: boolean;
};

// -- lifecycle and tiering ----------------------------------------------------

/**
 * `satisfied` is THREE-valued. `null` means the module that answers this check
 * does not exist yet — render it as pending, never as a tick and never as a
 * failure. Mirrors `ExitCheck` in the backend's `lifecycle.py`.
 */
export type ExitCheck = {
  code: string;
  label: string;
  satisfied: boolean | null;
  detail: string | null;
  clears_with: string | null;
  clears_id: string | null;
};

export type StageRow = {
  id: string;
  engagement_id: string;
  cycle: number;
  stage: string;
  label: string;
  status: string;
  is_gate: boolean;
  is_required: boolean;
  entered_at: string | null;
  exited_at: string | null;
  skipped_reason: string | null;
  skipped_by_policy: string | null;
  checks: ExitCheck[];
  blockers: ExitCheck[];
  pending: ExitCheck[];
  allowed_transitions: string[];
};

export type TieringFactor = {
  key: string;
  label: string;
  answer: number;
  clamped: number;
  weight: number;
  points: number;
  max_points: number;
};

export type Tiering = {
  id: string;
  engagement_id: string;
  cycle: number;
  factors: TieringFactor[];
  score: number;
  computed_tier: string;
  override_tier: string | null;
  override_justification: string | null;
  effective_tier: string;
  thresholds: Record<string, number>;
  points_to_higher_tier: number | null;
  points_to_lower_tier: number | null;
  assessed_by_name: string | null;
  assessed_at: string | null;
  /** Set on a run answered from a tiering questionnaire; `factors` is then empty. */
  questionnaire_id: string | null;
  questionnaire_name: string | null;
  questions: TieringQuestionLine[];
  answers: Record<string, TieringAnswer>;
  /** The tier an option's minimum lifted this run to, when the score alone would not. */
  floor_tier: string | null;
};

export type TieringQuestionLine = {
  id: string;
  prompt: string;
  section: string;
  answer_labels: string[];
  comment: string | null;
  points: number;
  max_points: number;
  floor_tier: string | null;
  counted: boolean;
};

export type AnswerValue = string | number | string[] | null;
export type TieringAnswer = { value: AnswerValue; comment?: string | null };

// -- questionnaires a tenant builds --------------------------------------------

/**
 * Two questionnaires with two audiences. `tiering` is answered by our own team
 * about how we use a vendor and sets the tier. `due_diligence` goes to the
 * vendor through the portal and sets the residual score and findings.
 */
export type QuestionnairePurpose = "tiering" | "due_diligence";

export const QUESTION_TYPES = [
  "single_choice",
  "multi_choice",
  "text",
  "paragraph",
  "number",
  "date",
  "file",
] as const;
export type QuestionType = (typeof QUESTION_TYPES)[number];
export type EvidenceRule = "none" | "optional" | "required";

export type QuestionOption = {
  key: string;
  label: string;
  score: number;
  flag: boolean;
  not_applicable: boolean;
  comment_required: boolean;
  min_tier: string | null;
};

export type QuestionCondition = { question_id: string; option_keys: string[] };

export type BuilderQuestion = {
  id: string;
  position: number;
  section: string;
  prompt: string;
  help_text: string | null;
  answer_type: QuestionType;
  options: QuestionOption[];
  required: boolean;
  evidence: EvidenceRule;
  evidence_on: string[];
  weight: number;
  domain: string | null;
  domain_label: string | null;
  critical: boolean;
  blocking: boolean;
  condition: Partial<QuestionCondition>;
  framework_refs: string[];
  library_code: string | null;
};

export type QuestionnaireSummary = {
  id: string;
  purpose: QuestionnairePurpose;
  name: string;
  description: string | null;
  status: "active" | "archived";
  is_default: boolean;
  default_tiers: string[];
  question_count: number;
  section_count: number;
  library_code: string | null;
  updated_at: string;
  updated_by_name: string | null;
};

export type Questionnaire = QuestionnaireSummary & {
  tier_thresholds: Record<string, number>;
  questions: BuilderQuestion[];
};

export type LibraryQuestion = {
  id: string;
  code: string;
  section: string;
  prompt: string;
  help_text: string | null;
  answer_type: QuestionType;
  options: QuestionOption[];
  required: boolean;
  evidence: EvidenceRule;
  weight: number;
  domain: string | null;
  domain_label: string | null;
  critical: boolean;
  blocking: boolean;
  scope_level: string;
  framework_refs: string[];
  condition_code: string | null;
};

export type LibraryTemplate = {
  code: string;
  name: string;
  description: string | null;
  purpose: QuestionnairePurpose;
  version: string;
  presets: { key: string; label: string; question_count: number }[];
  questions: LibraryQuestion[];
};

export type QuestionInput = {
  prompt: string;
  answer_type: QuestionType;
  section: string;
  help_text: string | null;
  options: Partial<QuestionOption>[];
  required: boolean;
  evidence: EvidenceRule;
  evidence_on: string[];
  weight: number;
  domain: string | null;
  critical: boolean;
  blocking: boolean;
  condition: QuestionCondition | null;
};

// -- questionnaire, assessment, findings --------------------------------------

/**
 * `portal_url` is the ONLY copy of the token that will ever exist — the row
 * stores a hash. Show it once; re-issuing mints a new token and revokes this one.
 */
export type IssuedQuestionnaire = {
  assessment_id: string;
  contact_email: string;
  question_count: number;
  due_date: string | null;
  portal_url: string;
};

export type DomainScore = { posture: number; residual: number; answered: number };
export type ScoreStep = { label: string; value: number; detail: string | null };

/** A review sent from a tenant questionnaire names it; one sent from the bank names the bank. */
export type AssessmentScope = {
  tier: string | null;
  question_count: number;
  snapshotted_at: string;
  questionnaire_id?: string;
  questionnaire_name?: string;
  bank_code?: string;
  bank_version?: string;
  scope_levels?: string[];
};

export type AssessmentResponse = {
  id: string;
  question_id: string;
  question_code: string;
  body: string;
  domain: string;
  domain_label: string;
  scope_level: string;
  answer_type: string;
  weight: number;
  critical_control: boolean;
  non_negotiable: boolean;
  evidence_required: boolean;
  framework_refs: string[];
  answer: string | null;
  implementation_notes: string | null;
  na_justification: string | null;
  evidence_id: string | null;
  answered_at: string | null;
  section: string;
  help_text: string | null;
  options: { key: string; label: string; score: number; flag: boolean; not_applicable: boolean }[];
  value: AnswerValue;
  answer_labels: string[];
  /** The answer picked an option marked as a gap. */
  flagged: boolean;
  required: boolean;
  evidence: EvidenceRule;
  /** False when its condition was not met: the question was never asked. */
  visible: boolean;
  owes_evidence: boolean;
};

export type Assessment = {
  id: string;
  vendor_id: string;
  engagement_id: string;
  cycle: number;
  kind: string;
  review_format: string;
  assessment_domain: string;
  status: string;
  due_date: string | null;
  residual_score: number | null;
  grade: string | null;
  domain_scores: Record<string, DomainScore>;
  score_steps: ScoreStep[];
  scope: AssessmentScope;
  question_count: number;
  answered_count: number;
  unanswered_count: number;
  missing_evidence_count: number;
  submitted_at: string | null;
  responses: AssessmentResponse[];
  findings: Finding[];
  portal_link_live: boolean;
  portal_link_expires_at: string | null;
  created_at: string;
  updated_at: string;
  /** Who is reading which domain, and how far each has got. */
  reviewers: Reviewer[];
  comments: Comment[];
};

export type Finding = {
  id: string;
  vendor_id: string;
  /** Only the cross-vendor queue fills this in — a finding shown under its own
   *  vendor does not need it, so the backend does not pay for the join. */
  vendor_name: string | null;
  assessment_id: string | null;
  question_id: string | null;
  title: string;
  detail: string;
  finding_source: string;
  severity: string;
  status: string;
  treatment: string;
  is_blocking: boolean;
  sla_due: string | null;
  owner_membership_id: string | null;
  owner_name: string | null;
  task_id: string | null;
  accepted_until: string | null;
  accepted_rationale: string | null;
  closed_at: string | null;
  /** Always null until the risk module exists — do not build UI on it. */
  promoted_risk_id: string | null;
  created_at: string;
};

export type FindingPage = { items: Finding[]; total: number };

// -- the decision -------------------------------------------------------------

export type Condition = {
  id: string;
  approval_id: string;
  description: string;
  owner_membership_id: string | null;
  owner_name: string | null;
  due_date: string | null;
  status: string;
  task_id: string | null;
  waived_reason: string | null;
};

export type Approval = {
  id: string;
  engagement_id: string;
  cycle: number;
  stage_id: string | null;
  decision: string;
  rationale: string;
  decided_by_membership_id: string | null;
  decided_by_name: string | null;
  excluded_membership_ids: string[];
  decided_at: string;
  conditions: Condition[];
};

/**
 * `disqualified_reason` is shown before submit — segregation of duties is meant
 * to be visible, not enforced by a rejection after the rationale is written.
 */
export type Approver = {
  membership_id: string;
  name: string;
  is_designated_approver: boolean;
  disqualified_reason: string | null;
};

// -- paperwork ----------------------------------------------------------------

export type VendorDocument = {
  id: string;
  vendor_id: string;
  doc_type: string;
  title: string;
  issue_date: string | null;
  valid_until: string | null;
  expires_in_days: number | null;
  is_expired: boolean;
  collection_status: string;
  review_notes: string | null;
  reviewed_by_name: string | null;
  reviewed_at: string | null;
  evidence_id: string | null;
};

export type SocReview = {
  id: string;
  vendor_id: string;
  document_id: string | null;
  report_kind: string;
  report_type: string;
  audit_period_start: string | null;
  audit_period_end: string | null;
  tsc_included: string[];
  opinion: string;
  bridge_letter_received: boolean;
  findings_material: boolean;
  cuec_reviewed: boolean;
  cuec_notes: string | null;
  subservice_orgs: string | null;
  cpa_firm: string | null;
  reviewed_at: string | null;
  period_is_stale: boolean;
  needs_bridge_letter: boolean;
};

export type Contract = {
  id: string;
  vendor_id: string;
  engagement_id: string | null;
  contract_type: string;
  title: string;
  start_date: string | null;
  end_date: string | null;
  renewal_date: string | null;
  renews_in_days: number | null;
  auto_renew: boolean;
  notice_period_days: number | null;
  breach_notification_hours: number | null;
  right_to_audit: boolean;
  subprocessor_terms: boolean;
  exit_data_return_clause: boolean;
  value: number | null;
  status: string;
  clauses_present: number;
  notice_deadline: string | null;
};

export type Subprocessor = {
  id: string;
  vendor_id: string;
  name: string;
  service: string;
  data_location: string | null;
  provenance: string;
  linked_vendor_id: string | null;
  notification_obligation: string | null;
  status: string;
  also_used_by_vendors: number;
};

// -- intake and roster --------------------------------------------------------

export type IntakeRequest = {
  id: string;
  vendor_name: string;
  department: string | null;
  proposed_service: string;
  data_types_shared: string[];
  urgency: string;
  screening_status: string;
  decision: string;
  decision_reason: string | null;
  requested_by_name: string | null;
  decided_by_name: string | null;
  decided_at: string | null;
  created_vendor_id: string | null;
  duplicates: DuplicateMatch[];
  created_at: string;
};

export type IntakePage = { items: IntakeRequest[]; total: number };

export type Roster = { roles: Record<string, string[]> };

// -- the portal (unauthenticated; defined inline in portal_router.py) ----------

/** An option as the vendor sees it: never its score, never whether it counts as a gap. */
export type PortalOption = {
  key: string;
  label: string;
  not_applicable: boolean;
  comment_required: boolean;
};

export type PortalQuestion = {
  id: string;
  code: string;
  body: string;
  domain: string;
  domain_label: string;
  section: string;
  help_text: string | null;
  answer_type: QuestionType;
  options: PortalOption[];
  required: boolean;
  evidence: EvidenceRule;
  evidence_on: string[];
  evidence_required: boolean;
  condition_question_id: string | null;
  condition_option_keys: string[];
  answer: string | null;
  value: AnswerValue;
  answered: boolean;
  implementation_notes: string | null;
  na_justification: string | null;
  has_evidence: boolean;
};

export type Portal = {
  assessment_id: string;
  organisation: string;
  vendor_name: string;
  status: string;
  due_date: string | null;
  question_count: number;
  answered_count: number;
  submitted_at: string | null;
  questions: PortalQuestion[];
};

// -- request bodies -----------------------------------------------------------
// Every request model forbids extra fields server-side: one stray key 422s the
// whole request. Keep these exact.

export type VendorInput = {
  name: string;
  vendor_type?: string;
  industry?: string | null;
  website?: string | null;
  business_unit?: string | null;
  services_provided?: string;
  stores_pii?: boolean;
  data_location?: string | null;
  data_types_in_scope?: string[];
  systems_in_scope?: string[];
  data_classification?: string | null;
  tags?: string[];
  business_owner_membership_id?: string | null;
  security_owner_membership_id?: string | null;
  relationship_owner_membership_id?: string | null;
};

export type EngagementInput = {
  name: string;
  service_description?: string;
  business_unit?: string | null;
  internal_owner_membership_id?: string | null;
  start_date?: string | null;
  end_date?: string | null;
};

export type VendorCreateInput = VendorInput & { engagement?: EngagementInput };

export type ContactInput = {
  name: string;
  email?: string | null;
  phone?: string | null;
  contact_type?: string;
};

/**
 * Answers to a tiering questionnaire, keyed by question id. The score, the tier
 * and the whole stage list are computed server-side in the same transaction.
 */
export type TieringInput = {
  questionnaire_id: string;
  answers: Record<string, TieringAnswer>;
  override_tier?: string | null;
  override_justification?: string | null;
};

export type ConditionInput = {
  description: string;
  owner_membership_id?: string | null;
  due_date?: string | null;
};

export type DecisionInput = {
  decision: string;
  rationale: string;
  conditions?: ConditionInput[];
};

export type DocumentInput = {
  title: string;
  doc_type?: string;
  issue_date?: string | null;
  valid_until?: string | null;
  collection_status?: string;
  evidence_id?: string | null;
};

export type SocReviewInput = {
  report_kind?: string;
  report_type?: string;
  document_id?: string | null;
  audit_period_start?: string | null;
  audit_period_end?: string | null;
  tsc_included?: string[];
  opinion?: string;
  bridge_letter_received?: boolean;
  findings_material?: boolean;
  cuec_reviewed?: boolean;
  cuec_notes?: string | null;
  subservice_orgs?: string | null;
  cpa_firm?: string | null;
};

export type ContractInput = {
  title: string;
  contract_type?: string;
  engagement_id?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  renewal_date?: string | null;
  auto_renew?: boolean;
  notice_period_days?: number | null;
  breach_notification_hours?: number | null;
  right_to_audit?: boolean;
  subprocessor_terms?: boolean;
  exit_data_return_clause?: boolean;
  value?: number | null;
  status?: string;
};

export type SubprocessorInput = {
  name: string;
  service?: string;
  data_location?: string | null;
  provenance?: string;
  linked_vendor_id?: string | null;
  notification_obligation?: string | null;
};

export type IntakeInput = {
  vendor_name: string;
  department?: string | null;
  proposed_service?: string;
  data_types_shared?: string[];
  urgency?: string;
};

export type OffboardingCompletionInput = {
  access_revoked?: boolean;
  data_returned?: boolean;
  contract_provisions_reviewed?: boolean;
  final_payments_settled?: boolean;
  certificate_evidence_id?: string | null;
  notes?: string | null;
  complete?: boolean;
};

// -- register filters ---------------------------------------------------------

export type VendorSort =
  | "name"
  | "tier"
  | "grade"
  | "owner"
  | "reassessment"
  | "value"
  | "status";

export type VendorFilters = {
  search: string;
  vendor_type: string | null;
  statuses: string[];
  tiers: string[];
  classifications: string[];
  business_units: string[];
  /** "me", "unassigned", or a membership id. Filters the BUSINESS owner only. */
  owner: string | null;
  /** Only meaningful when true — there is no "does not store PII" filter. */
  stores_pii: boolean;
  /** Attention codes, from `ATTENTION_CODES` server-side. This is what the
   *  overview's tiles link into, so the count and the filtered list agree. */
  attention: string[];
};
