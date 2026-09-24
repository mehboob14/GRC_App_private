/** Vulnerability management types — the definition/instance model (Week 6). */

export type Severity = "critical" | "high" | "medium" | "low" | "info";

export type InstanceState =
  | "new"
  | "active"
  | "in_progress"
  | "pending_retest"
  | "fixed"
  | "resurfaced"
  | "accepted"
  | "false_positive";

export type VulnInstance = {
  id: string;
  cve_id: string | null;
  title: string;
  severity: Severity;
  cvss_score: number | null;
  cvss_vector: string | null;
  cwe_id: string | null;
  state: InstanceState;
  risk_score: number | null;
  risk_reason: string | null;
  priority_band: string;
  kev_flag: boolean;
  epss_score: number | null;
  epss_percentile: number | null;
  public_exploit_count: number | null;
  patch_available: boolean | null;
  asset_id: string;
  asset_name: string;
  asset_host: string | null;
  locator: string;
  owner_membership_id: string | null;
  owner_name: string | null;
  sla_due_at: string | null;
  overdue: boolean;
  escalation_level: number;
  first_detected_at: string | null;
  last_seen_at: string | null;
  detected_by: string[];
};

export type VulnTransition = {
  from_state: string | null;
  to_state: string;
  actor_name: string;
  note: string | null;
  occurred_at: string;
};

export type AffectedAsset = {
  instance_id: string;
  asset_id: string;
  asset_name: string;
  asset_host: string | null;
  state: InstanceState;
  risk_score: number | null;
  priority_band: string;
};

export type AssignmentTarget = {
  target_type: "user" | "role" | "group";
  target_id: string;
  name: string;
};

/** One additive term of the base risk score, with where its value came from. */
export type RiskFactor = {
  key: string;
  label: string;
  detail: string;
  points: number;
  max_points: number;
};

/** How the risk score was reached. Not a flat sum: three threat terms make a
 *  base out of 100, the asset multiplies it, then the 100 cap and the KEV floor
 *  can bind. Mirrors RiskBreakdown in the backend's scoring.py. */
export type RiskBreakdown = {
  score: number;
  band: string;
  reason: string;
  factors: RiskFactor[];
  base_score: number;
  asset_multiplier: number;
  asset_detail: string;
  adjusted_score: number;
  capped: boolean;
  kev_floor_applied: boolean;
};

/** The linked asset's rating inputs. C/I/A travel for context; only `tier` and
 *  the two exposure flags weigh the score. */
export type AssetCriticality = {
  tier: string | null;
  internet_facing: boolean;
  customer_facing: boolean;
  confidentiality: number | null;
  integrity: number | null;
  availability: number | null;
};

/** A request to accept the risk on a finding, and the decision on it.
 *  requested -> approved | rejected; approved -> expired | revoked. */
export type ExceptionStatus =
  | "requested"
  | "approved"
  | "rejected"
  | "expired"
  | "revoked";

export type VulnException = {
  id: string;
  status: ExceptionStatus;
  duration_days: number;
  rationale: string;
  potential_risks: string;
  compensating_controls: string | null;
  requested_by_membership_id: string | null;
  requested_by_name: string | null;
  requested_at: string;
  decided_by_membership_id: string | null;
  decided_by_name: string | null;
  decided_at: string | null;
  decision_note: string | null;
  expires_at: string | null;
};

/** A primary source behind one of the facts on a finding, so a reader can check
 *  the KEV badge, the EPSS score or the patch claim rather than trust it. */
export type VulnReference = {
  /** Which fact it backs: cve | kev | epss | exploit | patch */
  backs: string;
  label: string;
  url: string;
  detail: string;
};

export type VulnInstanceDetail = VulnInstance & {
  /** The tenant's own fields (features/custom-fields), validated server side. */
  custom_fields: Record<string, string | number | boolean>;
  kev_vendor: string | null;
  kev_product: string | null;
  kev_required_action: string | null;
  kev_due_at: string | null;
  references: VulnReference[];
  exception: VulnException | null;
  kev_added_at: string | null;
  risk_breakdown: RiskBreakdown | null;
  asset_criticality: AssetCriticality | null;
  definition_id: string;
  description: string | null;
  recommendation: string | null;
  kev_ransomware: boolean;
  exploit_refs: Array<{ full_name?: string; url?: string; stars?: number }>;
  enriched_at: string | null;
  fixed_versions: string | null;
  advisory_url: string | null;
  patch_source: string | null;
  component: string | null;
  port: number | null;
  affected_url: string | null;
  evidence: string | null;
  reproduction_steps: string | null;
  resolution_notes: string | null;
  fixed_verified: boolean;
  resurfaced_count: number;
  accepted_reason: string | null;
  accepted_expires_at: string | null;
  compensating_controls: string | null;
  escalated_at: string | null;
  false_positive_reason: string | null;
  report_id: string | null;
  transitions: VulnTransition[];
  affected_assets: AffectedAsset[];
  assignment_targets: AssignmentTarget[];
};

export type CveLookup = {
  matched: boolean;
  match_source: string;
  cve_id: string | null;
  cvss_score: number | null;
  cvss_vector: string | null;
  severity: Severity | null;
  cwe_id: string | null;
  description: string | null;
  nvd_url: string | null;
};

export type RemediationFixType = "patch" | "config" | "script" | "mitigation";

export type RemediationStatus =
  | "preview"
  | "recommended"
  | "approved"
  | "applied"
  | "verified"
  | "failed"
  | "cancelled";

export type RemediationPlan = {
  id: string | null;
  instance_id: string;
  fix_type: RemediationFixType;
  title: string;
  summary: string;
  fix_artifact: string;
  rationale: string;
  rollback_plan: string | null;
  source: string;
  status: RemediationStatus;
  triggers: string[];
  risk_score_before: number | null;
  risk_score_after: number | null;
  change_window_start: string | null;
  change_window_end: string | null;
  approved_by_name: string | null;
  approved_at: string | null;
  applied_at: string | null;
  execution_log: string | null;
  verification_evidence: string | null;
  verified_by_name: string | null;
  verified_at: string | null;
  failure_reason: string | null;
  cancelled_reason: string | null;
  cancelled_at: string | null;
};

export type VulnKpis = {
  open_total: number;
  open_by_severity: Record<string, number>;
  open_by_priority: Record<string, number>;
  sla_posture: Record<string, number>;
  overdue: number;
  kev_open: number;
  accepted: number;
};

export type VulnThroughput = {
  closed_30d: number;
  opened_30d: number;
  mttr_days_by_severity: Record<string, number | null>;
  median_mttr_days: number | null;
};

export type VulnReport = {
  id: string;
  name: string;
  report_type: string;
  scan_tool: string | null;
  status: string;
  parse_error: string | null;
  file_name: string | null;
  has_file: boolean;
  total_count: number;
  critical_count: number;
  high_count: number;
  uploaded_by_name: string | null;
  created_at: string;
};

export type SlaPolicy = { severity: Severity; days: number | null };

export type ImportResult = {
  report_id: string;
  created: number;
  resurfaced: number;
  updated: number;
  unmatched: number;
  definitions: number;
  status: string;
  parse_error: string | null;
};

export type AddFindingInput = {
  asset_id: string;
  title: string;
  severity: Severity;
  cve_id?: string | null;
  description?: string | null;
  cvss_score?: number | null;
  cvss_vector?: string | null;
  cwe_id?: string | null;
  recommendation?: string | null;
  component?: string | null;
  port?: number | null;
  affected_url?: string | null;
  evidence?: string | null;
  reproduction_steps?: string | null;
};

export type VulnListFilters = {
  state?: string;
  severity?: string;
  asset_id?: string;
  kev_only?: boolean;
  overdue_only?: boolean;
  search?: string;
};
