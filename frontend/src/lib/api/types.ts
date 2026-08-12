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

export type LoginResponse =
  | LoginSuccess
  | LoginMfaChallenge
  | LoginMfaEnroll
  | LoginWorkspaceChoice;

export type SignupRequest = {
  company_name: string;
  full_name: string;
  email: string;
  password: string;
};

/** Signup creates a tenant + Admin membership, then requires MFA enrollment. */
export type SignupResponse = LoginMfaEnroll | LoginSuccess;

export type MfaVerifyRequest = {
  challenge_token: string;
  code: string;
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
  actor_label: string;
  action: AuditAction;
  object_type: string;
  object_id: string;
  object_label: string;
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
