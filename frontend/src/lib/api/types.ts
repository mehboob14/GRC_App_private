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

export type PermissionKey =
  | "tenant:read"
  | "members:read"
  | "members:invite"
  | "members:disable"
  | "groups:read"
  | "groups:manage"
  | "roles:read"
  | "roles:manage"
  | "audit:read";

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

export type SecurityPolicy = {
  require_mfa: boolean;
  enforce_sso: boolean;
  ip_allowlist: boolean;
  audit_log_export: boolean;
  session_timeout_hours: number;
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
