import type { BadgeVariant, IconName, StatusFamily } from "@/components/ui";
import type { Vendor } from "./types";

/**
 * Shared data tokens for the vendors feature. No JSX in this file — a module
 * that exports both a component and a plain value loses fast refresh.
 *
 * A token maps to a design-system variant (`StatusFamily`, `BadgeVariant`),
 * never to a raw Tailwind class. The class strings live once, in the DS.
 */

// -- tier, classification, grade ----------------------------------------------

/**
 * Deliberately identical to the assets module's criticality mapping: "Critical"
 * must be the same colour whether it labels an asset or a vendor. Copied rather
 * than imported — features do not reach into each other.
 */
export const TIER_META: Record<string, { label: string; family: StatusFamily }> = {
  critical: { label: "Critical", family: "danger" },
  high: { label: "High", family: "warning" },
  medium: { label: "Medium", family: "pending" },
  low: { label: "Low", family: "neutral" },
};

/** Shown wherever a tier has not been set — never a default tier. */
export const NOT_TIERED = { label: "Not tiered", family: "neutral" as StatusFamily };

export const CLASSIFICATION_META: Record<string, { label: string; family: StatusFamily }> = {
  public: { label: "Public", family: "neutral" },
  internal: { label: "Internal", family: "neutral" },
  confidential: { label: "Confidential", family: "warning" },
  restricted: { label: "Restricted", family: "danger" },
};

/**
 * The residual grade. A and B are outcomes worth showing green; D and F are the
 * ones that need a decision. C is the middle, and the middle is not a warning.
 */
export const GRADE_META: Record<string, { label: string; family: StatusFamily }> = {
  A: { label: "A", family: "success" },
  B: { label: "B", family: "success" },
  C: { label: "C", family: "progress" },
  D: { label: "D", family: "warning" },
  F: { label: "F", family: "danger" },
};

// -- lifecycle ----------------------------------------------------------------

export const LIFECYCLE_META: Record<string, { label: string; family: StatusFamily }> = {
  requested: { label: "Requested", family: "pending" },
  under_review: { label: "Under review", family: "progress" },
  approved: { label: "Approved", family: "success" },
  active: { label: "Active", family: "success" },
  flagged: { label: "Flagged", family: "danger" },
  on_hold: { label: "On hold", family: "warning" },
  offboarding: { label: "Offboarding", family: "warning" },
  terminated: { label: "Terminated", family: "neutral" },
  archived: { label: "Archived", family: "neutral" },
};

export const VENDOR_TYPE_LABEL: Record<string, string> = {
  vendor: "Vendor",
  supplier: "Supplier",
  contractor: "Contractor",
  partner: "Partner",
};

export const CONTACT_TYPE_LABEL: Record<string, string> = {
  security: "Security",
  privacy: "Privacy",
  commercial: "Commercial",
  portal: "Portal",
};

// -- stages -------------------------------------------------------------------

/**
 * Stage labels and the icon that stands for the work. The backend sends its own
 * `label` on every `StageOut` — prefer that and use this only for a stage code
 * that arrives without one (the facets list, the skip matrix).
 */
export const STAGE_LABEL: Record<string, string> = {
  intake: "Intake",
  tiering: "Tiering",
  diligence: "Diligence",
  questionnaire: "Questionnaire",
  scoring: "Scoring",
  findings: "Findings",
  contracting: "Contracting",
  approval: "Approval",
  onboarding: "Onboarding",
  monitoring: "Monitoring",
  reassessment: "Reassessment",
  offboarding: "Offboarding",
};

export const STAGE_STATUS_META: Record<string, { label: string; family: StatusFamily }> = {
  not_started: { label: "Not started", family: "pending" },
  in_progress: { label: "In progress", family: "progress" },
  complete: { label: "Complete", family: "success" },
  skipped: { label: "Skipped", family: "neutral" },
};

// -- assessment, findings -----------------------------------------------------

export const ASSESSMENT_STATUS_META: Record<string, { label: string; family: StatusFamily }> = {
  pending: { label: "Not started", family: "pending" },
  in_progress: { label: "In progress", family: "progress" },
  submitted: { label: "Submitted", family: "progress" },
  expired: { label: "Expired", family: "danger" },
  scored: { label: "Scored", family: "success" },
};

export const ASSESSMENT_KIND_LABEL: Record<string, string> = {
  initial: "Initial",
  reassessment: "Reassessment",
};

export const ANSWER_META: Record<string, { label: string; variant: BadgeVariant }> = {
  yes: { label: "Yes", variant: "statusPass" },
  partial: { label: "Partial", variant: "countWarn" },
  no: { label: "No", variant: "count" },
  na: { label: "N/A", variant: "neutral" },
};

export const FINDING_STATUS_META: Record<string, { label: string; family: StatusFamily }> = {
  open: { label: "Open", family: "danger" },
  in_remediation: { label: "In remediation", family: "progress" },
  accepted: { label: "Accepted", family: "pending" },
  closed: { label: "Closed", family: "success" },
};

export const FINDING_SOURCE_LABEL: Record<string, string> = {
  assessment: "Assessment",
  sla_breach: "SLA breach",
  signal: "Signal",
  document_review: "Document review",
  offboarding: "Offboarding",
};

export const TREATMENT_LABEL: Record<string, string> = {
  remediate: "Remediate",
  mitigate: "Mitigate",
  transfer: "Transfer",
  accept: "Accept",
};

// -- the decision -------------------------------------------------------------

/**
 * Four decisions, four meanings. A deferral is not a soft rejection: it says the
 * reviewer could not decide, which is a different thing to say to the business.
 */
export const DECISION_META: Record<
  string,
  { label: string; family: StatusFamily; blurb: string }
> = {
  approve: {
    label: "Approved",
    family: "success",
    blurb: "Cleared to onboard with no outstanding conditions.",
  },
  approve_with_conditions: {
    label: "Approved with conditions",
    family: "warning",
    blurb: "Cleared to onboard, but the conditions below must be met.",
  },
  defer: {
    label: "Deferred",
    family: "pending",
    blurb: "Not decided. Something is missing before this can be judged.",
  },
  reject: {
    label: "Rejected",
    family: "danger",
    blurb: "Not cleared to onboard. The engagement stops here.",
  },
};

export const CONDITION_STATUS_META: Record<string, { label: string; family: StatusFamily }> = {
  open: { label: "Open", family: "warning" },
  met: { label: "Met", family: "success" },
  overdue: { label: "Overdue", family: "danger" },
  waived: { label: "Waived", family: "neutral" },
};

// -- paperwork ----------------------------------------------------------------

export const DOC_TYPE_LABEL: Record<string, string> = {
  soc_report: "SOC report",
  iso_cert: "ISO certificate",
  bridge_letter: "Bridge letter",
  dpa: "Data processing agreement",
  pentest: "Penetration test",
  insurance: "Insurance certificate",
  financials: "Financial statements",
  bcdr: "BC/DR plan",
  policy: "Policy",
};

export const COLLECTION_STATUS_META: Record<string, { label: string; family: StatusFamily }> = {
  requested: { label: "Requested", family: "pending" },
  received: { label: "Received", family: "progress" },
  reviewed: { label: "Reviewed", family: "success" },
};

export const REPORT_KIND_LABEL: Record<string, string> = {
  soc1: "SOC 1",
  soc2: "SOC 2",
  soc3: "SOC 3",
};

export const REPORT_TYPE_LABEL: Record<string, string> = {
  type_i: "Type I",
  type_ii: "Type II",
};

/**
 * The auditor's verdict, in the auditor's words. Anything other than
 * unqualified is a finding in itself, which is why only the first is success.
 */
export const OPINION_META: Record<
  string,
  { label: string; family: StatusFamily; blurb: string }
> = {
  unqualified: {
    label: "Unqualified",
    family: "success",
    blurb: "Clean opinion. Controls were suitably designed and operating effectively.",
  },
  qualified: {
    label: "Qualified",
    family: "warning",
    blurb: "Clean except for stated exceptions. Read what was excepted.",
  },
  adverse: {
    label: "Adverse",
    family: "danger",
    blurb: "Controls were not operating effectively. Treat as a failed report.",
  },
  disclaimer: {
    label: "Disclaimer",
    family: "danger",
    blurb: "The auditor could not form an opinion. The report proves nothing.",
  },
};

export const CONTRACT_TYPE_LABEL: Record<string, string> = {
  master: "Master agreement",
  dpa: "Data processing agreement",
  sla: "Service level agreement",
  security_addendum: "Security addendum",
  nda: "Non-disclosure agreement",
};

export const CONTRACT_STATUS_META: Record<string, { label: string; family: StatusFamily }> = {
  draft: { label: "Draft", family: "neutral" },
  active: { label: "Active", family: "success" },
  expired: { label: "Expired", family: "danger" },
  terminated: { label: "Terminated", family: "neutral" },
};

/** The four clauses `clauses_present` counts, in the order the contract form asks. */
export const CONTRACT_CLAUSES = [
  { key: "right_to_audit", label: "Right to audit" },
  { key: "subprocessor_terms", label: "Subprocessor terms" },
  { key: "exit_data_return_clause", label: "Exit data return" },
  { key: "breach_notification_hours", label: "Breach notification window" },
] as const;

export const PROVENANCE_META: Record<string, { label: string; variant: BadgeVariant }> = {
  vendor_declared: { label: "Vendor declared", variant: "neutral" },
  auto_detected: { label: "Auto detected", variant: "role" },
  intelligence: { label: "Intelligence", variant: "role" },
};

// -- intake and roster --------------------------------------------------------

export const URGENCY_META: Record<string, { label: string; family: StatusFamily }> = {
  low: { label: "Low", family: "neutral" },
  normal: { label: "Normal", family: "progress" },
  high: { label: "High", family: "warning" },
};

export const SCREENING_META: Record<string, { label: string; family: StatusFamily }> = {
  pending: { label: "Not screened", family: "pending" },
  passed: { label: "Screened", family: "success" },
  flagged: { label: "Flagged", family: "warning" },
};

/**
 * `auto_approved` reads differently from `approved` on purpose: a machine
 * decision must stay distinguishable from a person's.
 */
export const INTAKE_DECISION_META: Record<string, { label: string; family: StatusFamily }> = {
  pending: { label: "Awaiting decision", family: "pending" },
  approved: { label: "Approved", family: "success" },
  auto_approved: { label: "Auto-approved", family: "success" },
  rejected: { label: "Declined", family: "danger" },
};

export const ROSTER_ROLE_META: Record<string, { label: string; blurb: string }> = {
  tprm_lead: { label: "TPRM lead", blurb: "Owns the programme and the register." },
  analyst: { label: "Analyst", blurb: "Runs assessments and works findings." },
  security: { label: "Security", blurb: "Reviews the security answers and evidence." },
  privacy: { label: "Privacy", blurb: "Reviews data handling and the DPA." },
  legal: { label: "Legal", blurb: "Reviews contract terms." },
  procurement: { label: "Procurement", blurb: "Owns the commercial relationship." },
  exec_approver: { label: "Executive approver", blurb: "Decides the gate for critical vendors." },
  it: { label: "IT", blurb: "Handles provisioning and access removal." },
};

export const DOMAIN_ICON: Record<string, IconName> = {
  information_security: "shield",
  access_control: "users",
  data_protection_privacy: "database",
  business_continuity: "activity",
  incident_response: "alert",
  secure_development: "puzzle",
  infrastructure_cloud: "cloud",
  personnel_security: "users",
  compliance_legal: "audit",
  fourth_party_management: "vendor",
};

/** Why the matcher thinks two records are the same organisation. */
export const DUPLICATE_REASON: Record<string, string> = {
  same_name: "the name matches once punctuation and casing are ignored",
  same_website: "the website resolves to the same domain",
};

export function duplicateReason(code: string): string {
  return DUPLICATE_REASON[code] ?? code.replace(/_/g, " ");
}

// -- formatters ---------------------------------------------------------------

export function fmtDate(value: string | null | undefined): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

/**
 * A countdown in the words a reader acts on. Negative is overdue and says so;
 * "in 0 days" is today.
 */
export function fmtCountdown(days: number | null | undefined): string {
  if (days === null || days === undefined) return "—";
  if (days < 0) return `${Math.abs(days)} ${Math.abs(days) === 1 ? "day" : "days"} ago`;
  if (days === 0) return "today";
  return `in ${days} ${days === 1 ? "day" : "days"}`;
}

export function fmtMoney(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

/** Whole days from today to an ISO date, or null when there is no date. */
export function daysUntil(isoDate: string | null | undefined): number | null {
  if (!isoDate) return null;
  const then = new Date(isoDate);
  if (Number.isNaN(then.getTime())) return null;
  const startOfDay = (d: Date) => Date.UTC(d.getFullYear(), d.getMonth(), d.getDate());
  return Math.round((startOfDay(then) - startOfDay(new Date())) / 86_400_000);
}

// -- the register's next-action column ----------------------------------------

/**
 * How each server-decided attention code renders.
 *
 * The codes and their ordering live in `backend/.../vendors/service.py`, because
 * the overview counts them and the register labels them and two implementations
 * of one rule set drift. This is only the presentation half: a family, where
 * clicking it goes, and — for the three that need live arithmetic — a label
 * built at the call site so no rendered copy is ever sent from Python.
 */
export const ATTENTION_META: Record<
  string,
  { family: StatusFamily; tab: string; label?: (v: Vendor) => string }
> = {
  flagged: { family: "danger", tab: "lifecycle" },
  reassessment_overdue: {
    family: "danger",
    tab: "assessments",
    label: (v) => `Reassessment overdue ${fmtCountdown(daysUntil(v.next_reassessment_on))}`,
  },
  not_tiered: { family: "warning", tab: "lifecycle" },
  awaiting_gate: { family: "warning", tab: "lifecycle" },
  on_hold: { family: "warning", tab: "lifecycle" },
  weak_grade: {
    family: "warning",
    tab: "findings",
    label: (v) => `Grade ${v.current_grade} — work the findings`,
  },
  unowned: { family: "warning", tab: "overview" },
  reassessment_due: {
    family: "progress",
    tab: "assessments",
    label: (v) => `Reassessment due ${fmtCountdown(daysUntil(v.next_reassessment_on))}`,
  },
  offboarding: { family: "progress", tab: "lifecycle" },
};

/** The words the server uses for each code, for surfaces that have only the code. */
export const ATTENTION_LABEL: Record<string, string> = {
  flagged: "Flagged for review",
  reassessment_overdue: "Reassessment overdue",
  not_tiered: "Not tiered",
  awaiting_gate: "Awaiting the approval gate",
  on_hold: "On hold",
  weak_grade: "Weak residual grade",
  unowned: "No business owner",
  reassessment_due: "Reassessment due soon",
  offboarding: "Offboarding in progress",
};

export type NextAction = {
  label: string;
  family: StatusFamily;
  /** Where the reader goes to clear it, relative to the vendor detail page. */
  tab: string;
};

/**
 * What this vendor needs from someone.
 *
 * The rules and their priority order are the server's — see `ATTENTION_CODES`
 * in the vendors service — so the count on the overview and the label in the
 * register can never disagree. This turns the code into the words and the
 * destination. Null means nothing is outstanding, and the register renders its
 * healthy line rather than an empty cell.
 */
export function nextAction(v: Vendor): NextAction | null {
  if (v.attention_code === null) return null;
  const meta = ATTENTION_META[v.attention_code];
  if (!meta) return null;
  return {
    label: meta.label ? meta.label(v) : (ATTENTION_LABEL[v.attention_code] ?? v.attention_code),
    family: meta.family,
    tab: meta.tab,
  };
}

/** The one-line reassurance a register shows in place of an empty cell. */
export const HEALTHY_LINE = "Nothing outstanding";
