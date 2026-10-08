/**
 * Typed API contracts for Week 1 — mirrored from:
 * openspec/changes/add-identity-and-access, add-provider-plane, add-audit-trail.
 * When the backend ships OpenAPI, replace with openapi-typescript output.
 */

export type BuiltInRoleName =
  | "Admin"
  | "Chief Executive Officer"
  | "Security Officer"
  | "Privacy Officer"
  | "Engineering Lead"
  | "Business Operations/Finance Lead";

export const PERMISSION_KEYS = [
  "tenant:read",
  "members:read",
  "members:invite",
  "members:disable",
  "members:manage",
  "groups:read",
  "groups:manage",
  "roles:read",
  "roles:manage",
  "audit:read",
  "security:manage",
  "tenant:manage",
  "frameworks:read",
  "controls:manage",
  "evidence:read",
  "evidence:manage",
  "evidence:review",
  "documents:read",
  "documents:manage",
  "documents:approve",
  "documents:publish",
  "tasks:read",
  "tasks:manage",
  "tasks:assign",
  "tasks:approve",
  "assets:read",
  "assets:manage",
  "assets:import",
  "assets:decommission",
  "vulnerabilities:read",
  "vulnerabilities:manage",
  "vulnerabilities:import",
  "vulnerabilities:accept",
  "vendors:read",
  "vendors:manage",
  "vendors:assess",
  "vendors:approve",
] as const;

export type PermissionKey = (typeof PERMISSION_KEYS)[number];

export function isPermissionKey(key: string): key is PermissionKey {
  return (PERMISSION_KEYS as readonly string[]).includes(key);
}

export type MembershipStatus = "invited" | "active" | "disabled";

export type User = {
  id: string;
  email: string;
  full_name: string;
  status: "active" | "disabled";
  mfa_enabled: boolean;
};

export type WorkspaceSummary = {
  membership_id: string;
  tenant_id: string;
  tenant_name: string;
  tenant_slug: string;
  role_name: BuiltInRoleName | string;
  status: MembershipStatus;
};

export type SessionPrincipal = {
  user: User;
  membership_id: string;
  tenant_id: string;
  tenant_name: string;
  permissions: PermissionKey[];
  role_names: string[];
};

export type LoginPasswordRequest = {
  email: string;
  password: string;
};

export type LoginSuccess = {
  status: "authenticated";
  access_token: string;
  principal: SessionPrincipal;
  workspaces: WorkspaceSummary[];
  /** Present only on the enrollment-confirm response — the plaintext recovery
      codes leave the server exactly once, here. */
  recovery_codes?: string[];
};

export type LoginMfaChallenge = {
  status: "mfa_required";
  challenge_token: string;
  membership_id: string;
};

export type LoginMfaEnroll = {
  status: "mfa_enrollment_required";
  challenge_token: string;
  membership_id: string;
};

export type LoginWorkspaceChoice = {
  status: "select_workspace";
  selection_token: string;
  workspaces: WorkspaceSummary[];
};

/**
 * The address hasn't been verified yet — signup always lands here, and login
 * does too when the user signed up but never clicked the emailed link. A real
 * verification email points at /verify-email?token=…; no session is issued
 * until that token is redeemed.
 */
export type LoginEmailVerification = {
  status: "email_verification_required";
  email: string;
};

export type LoginResponse =
  | LoginSuccess
  | LoginMfaChallenge
  | LoginMfaEnroll
  | LoginWorkspaceChoice
  | LoginEmailVerification;

export type SignupRequest = {
  company_name: string;
  full_name: string;
  email: string;
  password: string;
  /** Must be true — the backend rejects signup without an accepted terms box. */
  accept_terms: boolean;
};

/**
 * Signup is verify-first: it creates the tenant + Admin membership, mails a
 * verification link, and returns `email_verification_required`. MFA enrollment
 * happens after the emailed token is redeemed at /verify-email.
 */
export type SignupResponse =
  | LoginEmailVerification
  | LoginMfaEnroll
  | LoginSuccess;

export type MfaVerifyRequest = {
  challenge_token: string;
  /** Exactly one of these: the 6-digit authenticator code, or a single-use
      recovery code. Enrollment confirmation always uses `code`. */
  code?: string;
  recovery_code?: string;
};

export type MfaEnrollStartResponse = {
  challenge_token: string;
  secret: string;
  otpauth_url: string;
};

export type Member = {
  membership_id: string;
  user_id: string;
  full_name: string;
  email: string;
  status: MembershipStatus;
  role_names: string[];
  group_names: string[];
  mfa_enabled: boolean;
  /** Last successful sign-in (ISO), or null if they never have. */
  last_login_at: string | null;
};

export type InviteMemberRequest = {
  email: string;
  full_name: string;
  role_id: string;
  /**
   * Optional group. The backend adds the membership to it in the same
   * transaction as the invite, so the person is in the group on arrival.
   */
  group_id?: string;
  /**
   * Optional access window for guest auditors/consultants (ISO dates,
   * YYYY-MM-DD). The backend models the window on the role assignment;
   * an omitted bound means open-ended on that side.
   */
  valid_from?: string;
  valid_until?: string;
};

/**
 * Week 1: email delivery is a notifications-module concern, so the one-time
 * invite token and accept URL are returned once, here, for the inviter to
 * hand over (week1-review-decisions.md #15). Removed when notifications land.
 */
export type InviteMemberResponse = {
  member: Member;
  /** Single-use invite token (typ='invite', 7-day TTL). Shown once. */
  invite_token: string;
  /** Absolute URL to /accept-invite?token=… for the invitee. */
  accept_url: string;
  /** False when SMTP is unconfigured or the send failed. Never claim an invite
   *  was emailed unless this is true. */
  email_sent: boolean;
};

/**
 * POST /api/v1/auth/invitations/accept (public). New users supply
 * full_name + password; existing users send the token alone. Accepting
 * activates the membership and consumes the token; the user then signs in
 * normally.
 */
export type AcceptInvitationRequest = {
  token: string;
  full_name?: string;
  password?: string;
};

export type AcceptInvitationResponse = {
  status: "accepted";
  tenant_name: string;
};

export type Group = {
  id: string;
  name: string;
  description: string | null;
  member_count: number;
  member_ids: string[];
};

export type Role = {
  id: string;
  name: string;
  description: string | null;
  built_in: boolean;
  permission_keys: PermissionKey[];
  assignment_count: number;
};

export type AuditAction =
  | "create"
  | "update"
  | "delete"
  | "transition"
  | "approve";

export type AuditEvent = {
  id: string;
  tenant_id: string;
  actor_type: "membership" | "platform_admin" | "system";
  actor_id: string | null;
  /**
   * Best-effort humanised label from the backend (e.g. "Membership ·
   * 019ff785"). Treated as possibly-absent: the UI composes a fallback from
   * actor_type + short actor_id when it is missing or empty.
   */
  actor_label?: string | null;
  action: AuditAction;
  object_type: string;
  object_id: string;
  /** Best-effort humanised label; see actor_label. Possibly-absent. */
  object_label?: string | null;
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
  occurred_at: string;
};

export type TenantStatus =
  | "provisioning"
  | "active"
  | "suspended"
  | "terminated";

/** GET /api/v1/tenant — the caller's current workspace. */
export type TenantSummary = {
  id: string;
  name: string;
  slug: string;
  status: TenantStatus;
};

export type SecuritySettings = {
  require_admin_mfa: boolean;
  /** Enforced on every path that sets a password. */
  password_min_length: number;
  password_require_upper: boolean;
  password_require_lower: boolean;
  password_require_digit: boolean;
  password_require_symbol: boolean;
  password_history_depth: number;
  /** Stored and shown, not enforced yet — the UI badges these as such. */
  password_max_age_days: number;
  lockout_threshold: number;
  lockout_duration_minutes: number;
  idle_timeout_minutes: number;
};

/** Patch only what changed; the server accepts any subset. */
export type SecuritySettingsPatch = Partial<SecuritySettings>;

export type CompanyProfile = {
  tenant_id: string;
  legal_name: string | null;
  display_name: string | null;
  registration_number: string | null;
  industry: string | null;
  company_size: string | null;
  description: string | null;
  website: string | null;
  domain: string | null;
  headquarters: string | null;
  regulatory_scope: string | null;
  privacy_policy_url: string | null;
  terms_url: string | null;
};

export type CompanyProfilePatch = Partial<Omit<CompanyProfile, "tenant_id">>;

export type SmtpConfig = {
  host: string | null;
  port: number;
  username: string | null;
  from_name: string | null;
  from_address: string | null;
  use_tls: boolean;
  enabled: boolean;
  /** Whether a password is stored — the password itself is never returned. */
  has_password: boolean;
};

export type SmtpConfigUpdate = {
  host?: string | null;
  port?: number | null;
  username?: string | null;
  /** Write-only. Omit (or empty) to keep the stored one. */
  password?: string | null;
  from_name?: string | null;
  from_address?: string | null;
  use_tls?: boolean | null;
  enabled?: boolean | null;
};

export type SmtpTestResult = { ok: boolean; detail: string };

export type ApiErrorBody = {
  error: {
    code: string;
    message: string;
    correlation_id: string;
  };
};

export type CursorPage<T> = {
  items: T[];
  next_cursor: string | null;
};

// ---------------------------------------------------------------------------
// Compliance — shipped global content (frameworks, criteria, control templates)
// ---------------------------------------------------------------------------

export type FrameworkVersion = {
  id: string;
  version: string;
  published_at: string;
  is_current: boolean;
  requirement_count: number;
};

export type Framework = {
  id: string;
  code: string;
  name: string;
  description: string | null;
  built_in: boolean;
  versions: FrameworkVersion[];
};

export type Requirement = {
  id: string;
  requirement_key: string;
  code: string;
  name: string;
  description: string | null;
  category: string;
  trust_services_category: string;
  is_always_in_scope: boolean;
  /** How many shipped control templates satisfy this criterion. */
  template_count: number;
};

export type ControlTemplate = {
  id: string;
  code: string;
  canonical_key: string;
  name: string;
  description: string;
  implementation_guidance: string | null;
  /** The Type: which domain of the estate the control lives in. */
  category: string;
  /** The Sub-type: the area inside the Type, authored per control in the pack. */
  sub_category: string | null;
  /** Preventive / Detective / Corrective, shown as Design. NULL on framework
   *  content — the classification is authored on a tenant's own internal/custom
   *  controls. */
  control_type: string | null;
  /** Manual / Automated / Hybrid, shown as Automation. */
  control_sub_type: string | null;
  importance: string;
  built_in: boolean;
};

export type ControlTemplateDetail = ControlTemplate & {
  requirements: Requirement[];
};

export type ControlTemplatePage = {
  items: ControlTemplate[];
  total: number;
};

export type ControlTemplateQuery = {
  framework_id?: string;
  category?: string;
  control_type?: string;
  importance?: string;
  search?: string;
  limit?: number;
  offset?: number;
};

// --- Tenant control library -------------------------------------------------

export type ControlStatus =
  | "not_started"
  | "in_progress"
  | "implemented"
  | "not_applicable";

export type Control = {
  id: string;
  code: string;
  name: string;
  description: string;
  implementation_guidance: string | null;
  /** The Type: which domain of the estate the control lives in. */
  category: string;
  /** The Sub-type: the area inside the Type. Copied from the template, free text
   *  on a custom control; empty when nobody set one. */
  sub_category: string | null;
  /** Preventive / Detective / Corrective / Deterrent / Compensating / Directive,
   *  shown as Design. NULL on framework content — authored on a tenant's own
   *  controls. */
  control_type: string | null;
  /** Manual / Automated / Hybrid, shown as Automation. */
  control_sub_type: string | null;
  status: ControlStatus;
  origin: "template" | "custom";
  owner_membership_id: string | null;
  owner_name: string | null;
  disabled_at: string | null;
  disabled_reason: string | null;
  template_id: string | null;
  /** Criteria this control satisfies, e.g. ["SOC2:CC6.2"]. */
  requirement_keys: string[];
};

export type ControlVocabulary = {
  /** The Types. */
  categories: string[];
  /** The Sub-types the shipped library uses, per Type: suggestions, not a closed
   *  list. A Type none of the shipped controls refines is absent. */
  sub_categories: Record<string, string[]>;
  /** The Design values. */
  control_types: string[];
  /** The Automation values. */
  control_sub_types: string[];
  statuses: ControlStatus[];
};

export type ControlQuery = {
  status?: string;
  category?: string;
  sub_category?: string;
  control_type?: string;
  control_sub_type?: string;
  owner_membership_id?: string;
  include_disabled?: boolean;
  search?: string;
};

export type ControlCreateRequest = {
  /** Optional: omit and the platform assigns a GRC-NN code. */
  code?: string;
  name: string;
  description: string;
  category: string;
  /** Preventive / Detective / Corrective. NULL on framework content — the
   *  classification is authored on a tenant's own internal/custom controls. */
  control_type: string | null;
  sub_category?: string | null;
  control_sub_type?: string | null;
  implementation_guidance?: string | null;
  owner_membership_id?: string | null;
  requirement_ids?: string[];
  evidence_ids?: string[] | null;
};

export type ControlUpdateRequest = {
  name?: string;
  description?: string;
  implementation_guidance?: string | null;
  category?: string;
  sub_category?: string | null;
  control_type?: string;
  control_sub_type?: string | null;
  status?: ControlStatus;
  owner_membership_id?: string | null;
  clear_owner?: boolean;
  requirement_ids?: string[];
  evidence_ids?: string[] | null;
};

export type AdoptLibraryResult = {
  created: number;
  already_present: number;
  mappings_created: number;
};

// --- Engagement, scope and coverage -----------------------------------------

export type AuditType = "type_1" | "type_2";

export type Engagement = {
  id: string;
  name: string;
  framework_version_id: string;
  audit_type: AuditType;
  status: "draft" | "active" | "closed";
  window_start: string | null;
  window_end: string | null;
  categories_in_scope: string[];
};

export type EngagementPut = {
  name: string;
  framework_version_id: string;
  audit_type: AuditType;
  categories_in_scope: string[];
  window_start?: string | null;
  window_end?: string | null;
  status?: string | null;
};

export type ScopeCriterion = {
  id: string;
  requirement_key: string;
  code: string;
  name: string;
  trust_services_category: string;
  is_always_in_scope: boolean;
};

export type CriterionCoverage = {
  requirement_id: string;
  requirement_key: string;
  code: string;
  name: string;
  trust_services_category: string;
  in_scope: boolean;
  control_count: number;
};

export type ControlGap = {
  control_id: string;
  code: string;
  name: string;
  reason: string;
};

export type Coverage = {
  criteria_total: number;
  criteria_covered: number;
  criteria_uncovered: CriterionCoverage[];
  controls_total: number;
  controls_without_evidence: number;
  /** The controls behind that count. Itemised so the gap is something a person
      can open and act on, rather than a number they cannot get to. */
  controls_no_evidence: ControlGap[];
  /** Always true since the evidence module shipped. Kept so the older contract
      does not break; new code should not branch on it. */
  evidence_tracking_available: boolean;
  controls_unmapped: ControlGap[];
};

export type StatusCount = { status: string; count: number };
export type CategoryCoverage = {
  category: string;
  in_scope: number;
  covered: number;
  ready: number;
};
export type TimelinePoint = { on: string; controls: number; evidence: number };
export type ActivityItem = {
  occurred_at: string;
  action: string;
  actor_name: string | null;
  control_code: string | null;
  control_name: string | null;
};

export type OwnerCount = {
  membership_id: string | null;
  name: string;
  role: string | null;
  count: number;
};
export type DisabledControl = {
  control_id: string;
  code: string;
  name: string;
  reason: string | null;
};
export type RecentEvidence = {
  title: string;
  control_code: string | null;
  collected_on: string;
  freshness: EvidenceFreshness;
};

export type ReportKpis = {
  controls_total: number;
  controls_disabled: number;
  controls_evidenced: number;
  controls_owned: number;
  controls_ready: number;
  criteria_mapped: number;
  by_status: Record<string, number>;
  /** Controls whose automated tests fail. They are not counted as ready. */
  controls_failing_automation: number;
};
export type ReportRow = {
  code: string;
  name: string;
  category: string;
  sub_category: string | null;
  control_type: string | null;
  status: string;
  status_label: string;
  owner_name: string | null;
  frameworks: string[];
  criteria: string[];
  evidence_count: number;
  disabled_reason: string | null;
};
export type ControlReport = {
  generated_at: string;
  framework_label: string;
  kpis: ReportKpis;
  rows: ReportRow[];
};

export type ComplianceDashboard = {
  has_engagement: boolean;
  framework_name: string | null;
  audit_type: string | null;
  categories_in_scope: string[];
  criteria_total: number;
  criteria_covered: number;
  criteria_uncovered: number;
  controls_total: number;
  controls_evidenced: number;
  controls_no_evidence: number;
  controls_owned: number;
  controls_disabled: number;
  controls_internal: number;
  controls_unmapped: number;
  /** Implemented and currently evidenced — the point-in-time readiness count.
      Readiness over time needs a snapshot table, which is a later phase. */
  controls_ready: number;
  controls_in_progress: number;
  by_status: StatusCount[];
  by_category: CategoryCoverage[];
  by_owner: OwnerCount[];
  disabled: DisabledControl[];
  evidence_total: number;
  evidence_fresh: number;
  evidence_aging: number;
  evidence_stale: number;
  evidence_recent: RecentEvidence[];
  /** The date range picker's floor: the tenant cannot see before this. */
  tenant_created_on: string;
  timeline_from: string;
  timeline_to: string;
  timeline: TimelinePoint[];
  /** False until a connection has produced results. The UI greys that panel
      rather than showing a zero that would read as "everything failing". */
  checks_available: boolean;
  /** Controls, rolled up from their tests (AU-6). A control whose tests could
      not be read is "error", never "failing" (rule 7). */
  automation_passing: number;
  automation_failing: number;
  automation_error: number;
  recent_activity: ActivityItem[];
};

// --- Evidence library --------------------------------------------------------

export type EvidenceFreshness = "current" | "aging" | "stale" | "no_expiry";
export type ReviewStatus = "pending" | "approved" | "rejected";
export type EvidenceKind = "file" | "link";

export type Evidence = {
  id: string;
  title: string;
  description: string | null;
  evidence_type: string;
  kind: EvidenceKind;
  source_label: string | null;
  owner_membership_id: string | null;
  owner_name: string | null;
  collected_at: string;
  renewal_date: string | null;
  /** Derived server-side from renewal_date; never stored. */
  freshness: EvidenceFreshness;
  filename: string | null;
  content_type: string | null;
  size_bytes: number | null;
  sha256: string | null;
  link_url: string | null;
  /** Connector that produced this item (rule 9). Null for hand-uploaded
   *  evidence, which is everything until connectors land in Phase 2. */
  source: string | null;
  /** Review / approval — pending until someone with evidence:review signs off. */
  review_status: ReviewStatus;
  /** Whether a verdict is called for at all. Evidence proves a control; until
   *  one is linked there is nothing to review it against, so a bare upload is
   *  not pending anybody. Derived server-side from the control mappings. */
  review_required: boolean;
  reviewed_by_membership_id: string | null;
  reviewed_by_name: string | null;
  reviewed_at: string | null;
  review_note: string | null;
  control_ids: string[];
  control_codes: string[];
  control_links: { code: string; criteria: string[] }[];
};

/** The modules a piece of evidence can be linked to. Mirrors LINKABLE_TYPES in
 *  the backend's evidence service — adding one means adding it there first. */
export type LinkTargetType = "task" | "document" | "asset" | "vulnerability";

/** A record this evidence is linked to, in one shape for every module. `code`
 *  is that module's human handle (task code, doc code, CVE, hostname) and is
 *  empty where it has none; `detail` is its second fact. */
export type LinkedRecord = {
  link_id: string;
  target_type: LinkTargetType;
  target_id: string;
  code: string;
  title: string;
  status: string;
  detail: string | null;
};

export type EvidenceType = {
  value: string;
  label: string;
  default_validity_days: number;
};

export type EvidenceVocabulary = {
  types: EvidenceType[];
  freshness_states: EvidenceFreshness[];
};

export type EvidenceQuery = {
  evidence_type?: string;
  control_id?: string;
  freshness?: string;
};

export type EvidenceLinkCreate = {
  title: string;
  link_url: string;
  evidence_type: string;
  collected_at: string;
  description?: string | null;
  source_label?: string | null;
  owner_membership_id?: string | null;
  renewal_date?: string | null;
  control_ids?: string[];
};

export type EvidenceUpdate = {
  title?: string;
  description?: string | null;
  evidence_type?: string;
  source_label?: string | null;
  owner_membership_id?: string | null;
  clear_owner?: boolean;
  collected_at?: string;
  renewal_date?: string | null;
  control_ids?: string[];
};

/** A suggested control mapping for a piece of evidence — a draft a person approves. */
export type MappingSuggestion = {
  control_id: string;
  code: string;
  name: string;
  criteria: string[];
  coverage: "full" | "partial";
  confidence: number;
  rationale: string;
  /** 0..100: how well the evidence would prove this control. Null from the offline matcher. */
  maturity: number | null;
  verdict: "proves" | "partly" | "does_not" | null;
  gaps: string;
  /** "CC6.1: Logical access security" for each criterion the control answers. */
  requirements: string[];
};

/** A draft judgement of how well one item proves one control and its requirements. */
export type MaturityResult = {
  available: boolean;
  control_id: string;
  code: string;
  name: string;
  maturity: number | null;
  verdict: "proves" | "partly" | "does_not" | null;
  summary: string;
  strengths: string[];
  gaps: string[];
  requirements: { code: string; verdict: string; note: string }[];
};

export type MappingSuggestions = {
  /** "ai" when a model produced these, "heuristic" for the offline matcher. */
  source: "ai" | "heuristic";
  suggestions: MappingSuggestion[];
};

/** A task this evidence is linked to — the remediation or work it supports. */
