/**
 * The response shapes the dashboard reads, declared here rather than imported
 * from the other features. Each module owns its types and refactors them; a
 * dashboard that borrowed them would break every time one of them moved. Only
 * the fields the dashboard uses are listed, and each block names the endpoint
 * and the backend schema it mirrors.
 */

// -- compliance ---------------------------------------------------------------

/** GET /engagement/dashboard (compliance DashboardOut). */
export type Posture = {
  has_engagement: boolean;
  framework_name: string | null;
  audit_type: string | null;
  controls_total: number;
  controls_no_evidence: number;
  controls_ready: number;
  controls_in_progress: number;
  evidence_total: number;
  evidence_fresh: number;
  evidence_aging: number;
  evidence_stale: number;
  checks_available: boolean;
  automation_failing: number;
  by_category: CategoryCoverage[];
};

export type CategoryCoverage = {
  category: string;
  in_scope: number;
  covered: number;
  ready: number;
};

/** GET /engagement (EngagementOut), or null before one is set up. */
export type EngagementWindow = {
  window_end: string | null;
};

/** GET /controls/report (ControlReportOut), rows only. A disabled control
 *  reports the status "disabled". */
export type ControlReport = {
  rows: { status: string; frameworks: string[] }[];
};

/** One framework the workspace has adopted, counted over its live controls. */
export type FrameworkSummary = {
  name: string;
  controls: number;
  implemented: number;
  inProgress: number;
};

// -- risk ---------------------------------------------------------------------

/** GET /risks/registers (RegisterOut). */
export type RiskRegister = {
  id: string;
  name: string;
  is_default: boolean;
  status: string;
  severity_bands: RiskBand[];
};

export type RiskBand = { key: string; label: string; min_score: number };

/** GET /risks/summary (SummaryOut). Heatmaps are indexed [likelihood - 1][impact - 1]. */
export type RiskSummary = {
  total: number;
  heatmap_inherent: number[][];
  heatmap_residual: number[][];
  by_band: Record<string, number>;
  attention: Record<string, number>;
  top_risks: RiskTop[];
};

export type RiskTop = {
  id: string;
  code: string;
  title: string;
  category_name: string;
  inherent_score: number | null;
  inherent_band: string | null;
  residual_score: number | null;
  residual_band: string | null;
};

/** The default register and its summary, fetched as one picture. */
export type RiskPicture = {
  register: RiskRegister;
  summary: RiskSummary;
  /** Active registers in the workspace, so the card can name the one it shows. */
  registers: number;
};

// -- module summaries ---------------------------------------------------------

/** GET /vendors/summary (SummaryOut). */
export type VendorSummary = {
  total: number;
  attention: { code: string; label: string; count: number }[];
  findings_open: number;
  findings_by_severity: Record<string, number>;
  critical_overdue: number;
  intake_pending: number;
};

/** GET /vulnerabilities/kpis (KpiOut). */
export type VulnKpis = {
  open_total: number;
  open_by_severity: Record<string, number>;
  overdue: number;
  kev_open: number;
};

/** GET /assets/summary (AssetSummaryOut). */
export type AssetSummary = {
  total: number;
  by_tier: Record<string, number>;
  needs_cia: number;
  stale: number;
};

/** GET /tasks/summary (TaskSummaryOut). */
export type TaskSummary = {
  open_total: number;
  open_by_priority: Record<string, number>;
  breaching_now: number;
  due_soon: number;
};

/** GET /documents (DocumentOut), the fields the policies card counts. */
export type DocumentRow = {
  lifecycle: string;
  attestation_pct: number | null;
};

/** GET /documents/kpis (DocumentKpisOut). */
export type DocumentKpis = {
  renewal_past_due: number;
  needs_approval: number;
};

/** What the policies card shows, counted from the register and its KPIs. */
export type PolicySummary = {
  total: number;
  published: number;
  renewalOverdue: number;
  needsApproval: number;
  /** Mean acknowledgement rate over the documents that have readers assigned. */
  acknowledged: number | null;
};

// -- the caller's own work ----------------------------------------------------

/** GET /tasks?assignee=me (TaskPageOut). */
export type TaskPage = { items: TaskRow[]; total: number };

export type TaskRow = {
  id: string;
  code: string;
  title: string;
  priority: string;
  sla_due_at: string | null;
  sla_state: string;
  detected_at: string | null;
  due_at: string | null;
  created_at: string;
};

/** GET /documents/approvals/pending (PendingApprovalOut). */
export type PendingApproval = {
  document_id: string;
  document_code: string;
  document_title: string;
  tier: number;
};

/** GET /documents/campaigns/pending (PendingCampaignOut). */
export type PendingCampaign = {
  id: string;
  document_code: string;
  document_title: string;
  title: string;
  due_at: string | null;
  created_by_name: string;
};

/** GET /controls?owner_membership_id= (ControlOut). */
export type OwnedControl = {
  id: string;
  code: string;
  name: string;
  status: string;
};

/** GET /evidence (EvidenceOut), the fields that decide whether it still counts. */
export type EvidenceRow = {
  freshness: string;
  review_status: string;
  control_ids: string[];
};

/** An owned control with no evidence that still counts toward readiness. */
export type EvidenceGap = OwnedControl & { reason: string };
