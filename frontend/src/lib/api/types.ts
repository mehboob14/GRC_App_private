/**
 * Typed API contracts for Week 1 — mirrored from:
 * openspec/changes/add-identity-and-access, add-provider-plane, add-audit-trail.
 * When the backend ships OpenAPI, replace with openapi-typescript output.
 */

export type BuiltInRoleName =
  | "Admin"
  | "Compliance Manager"
  | "Control Owner"
  | "Employee"
  | "Auditor";

export const PERMISSION_KEYS = [
  "tenant:read",
  "members:read",
  "members:invite",
  "members:disable",
  "groups:read",
  "groups:manage",
  "roles:read",
  "roles:manage",
  "audit:read",
  "security:manage",
  "tenant:manage",
  "frameworks:read",
  "controls:manage",
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
  member_count: number;
  member_ids: string[];
};

export type Role = {
  id: string;
  name: string;
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
};

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
  category: string;
  control_type: string;
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
  category: string;
  control_type: string;
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
  categories: string[];
  control_types: string[];
  control_sub_types: string[];
  statuses: ControlStatus[];
};

export type ControlQuery = {
  status?: string;
  category?: string;
  control_type?: string;
  control_sub_type?: string;
  owner_membership_id?: string;
  include_disabled?: boolean;
  search?: string;
};

export type ControlCreateRequest = {
  code: string;
  name: string;
  description: string;
  category: string;
  control_type: string;
  control_sub_type?: string | null;
  implementation_guidance?: string | null;
  owner_membership_id?: string | null;
  requirement_ids?: string[];
};

export type ControlUpdateRequest = {
  name?: string;
  description?: string;
  implementation_guidance?: string | null;
  category?: string;
  control_type?: string;
  control_sub_type?: string | null;
  status?: ControlStatus;
  owner_membership_id?: string | null;
  clear_owner?: boolean;
  requirement_ids?: string[];
};

export type AdoptLibraryResult = {
  created: number;
  already_present: number;
  mappings_created: number;
};
