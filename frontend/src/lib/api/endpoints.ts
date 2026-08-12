import { apiFetch } from "@/lib/api/client";
import type {
  AcceptInvitationRequest,
  AcceptInvitationResponse,
  AuditEvent,
  CursorPage,
  Group,
  InviteMemberRequest,
  InviteMemberResponse,
  LoginPasswordRequest,
  LoginResponse,
  Member,
  MfaEnrollStartResponse,
  MfaVerifyRequest,
  Role,
  SignupRequest,
  SignupResponse,
  TenantSummary,
  WorkspaceSummary,
} from "@/lib/api/types";

export const authApi = {
  login: (body: LoginPasswordRequest) =>
    apiFetch<LoginResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  signup: (body: SignupRequest) =>
    apiFetch<SignupResponse>("/auth/signup", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  verifyMfa: (body: MfaVerifyRequest) =>
    apiFetch<LoginResponse>("/auth/mfa/verify", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  startMfaEnroll: (challengeToken: string) =>
    apiFetch<MfaEnrollStartResponse>("/auth/mfa/enroll", {
      method: "POST",
      body: JSON.stringify({ challenge_token: challengeToken }),
    }),
  confirmMfaEnroll: (body: MfaVerifyRequest) =>
    apiFetch<LoginResponse>("/auth/mfa/confirm", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  listWorkspaces: () => apiFetch<WorkspaceSummary[]>("/auth/workspaces"),
  switchWorkspace: (membershipId: string) =>
    apiFetch<LoginResponse>("/auth/workspaces/switch", {
      method: "POST",
      body: JSON.stringify({ membership_id: membershipId }),
    }),
  selectWorkspace: (selectionToken: string, membershipId: string) =>
    apiFetch<LoginResponse>("/auth/workspaces/select", {
      method: "POST",
      body: JSON.stringify({
        selection_token: selectionToken,
        membership_id: membershipId,
      }),
    }),
  acceptInvitation: (body: AcceptInvitationRequest) =>
    apiFetch<AcceptInvitationResponse>("/auth/invitations/accept", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};

export const iamApi = {
  listMembers: () => apiFetch<Member[]>("/members"),
  inviteMember: (body: InviteMemberRequest) =>
    apiFetch<InviteMemberResponse>("/members/invite", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  disableMember: (membershipId: string) =>
    apiFetch<Member>(`/members/${membershipId}/disable`, { method: "POST" }),
  assignRole: (membershipId: string, roleId: string) =>
    apiFetch<Member>(`/members/${membershipId}/roles`, {
      method: "PUT",
      body: JSON.stringify({ role_id: roleId }),
    }),
  listGroups: () => apiFetch<Group[]>("/groups"),
  createGroup: (name: string) =>
    apiFetch<Group>("/groups", {
      method: "POST",
      body: JSON.stringify({ name }),
    }),
  addGroupMember: (groupId: string, membershipId: string) =>
    apiFetch<Group>(`/groups/${groupId}/members`, {
      method: "POST",
      body: JSON.stringify({ membership_id: membershipId }),
    }),
  listRoles: () => apiFetch<Role[]>("/roles"),
  createRole: (body: { name: string; permission_keys: string[] }) =>
    apiFetch<Role>("/roles", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};

export const tenantApi = {
  get: () => apiFetch<TenantSummary>("/tenant"),
};

export const auditApi = {
  list: (cursor?: string) => {
    const qs = cursor ? `?cursor=${encodeURIComponent(cursor)}` : "";
    return apiFetch<CursorPage<AuditEvent>>(`/audit-log${qs}`);
  },
};
