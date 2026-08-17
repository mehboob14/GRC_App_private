import { apiFetch } from "@/lib/api/client";
import type {
  AcceptInvitationRequest,
  AcceptInvitationResponse,
  AdoptLibraryResult,
  AuditEvent,
  Control,
  ControlCreateRequest,
  ControlQuery,
  ControlTemplateDetail,
  ControlTemplatePage,
  ControlTemplateQuery,
  ControlUpdateRequest,
  ControlVocabulary,
  Coverage,
  CursorPage,
  Engagement,
  EngagementPut,
  Evidence,
  EvidenceLinkCreate,
  EvidenceQuery,
  EvidenceUpdate,
  EvidenceVocabulary,
  Framework,
  Group,
  InviteMemberRequest,
  InviteMemberResponse,
  LoginPasswordRequest,
  LoginResponse,
  Member,
  MfaEnrollStartResponse,
  MfaVerifyRequest,
  Requirement,
  Role,
  ScopeCriterion,
  SignupRequest,
  SignupResponse,
  CompanyProfile,
  CompanyProfilePatch,
  SecuritySettings,
  SmtpConfig,
  SmtpConfigUpdate,
  SmtpTestResult,
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
  verifyEmail: (token: string) =>
    apiFetch<LoginResponse>("/auth/verify-email", {
      method: "POST",
      body: JSON.stringify({ token }),
    }),
  resendVerification: (email: string) =>
    apiFetch<void>("/auth/verify-email/resend", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  requestPasswordReset: (email: string) =>
    apiFetch<void>("/auth/password-reset", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  confirmPasswordReset: (token: string, new_password: string) =>
    apiFetch<void>("/auth/password-reset/confirm", {
      method: "POST",
      body: JSON.stringify({ token, new_password }),
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
  logout: () => apiFetch<void>("/auth/logout", { method: "POST" }),
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
  updateRole: (
    roleId: string,
    body: { name?: string; permission_keys?: string[] },
  ) =>
    apiFetch<Role>(`/roles/${roleId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  deleteRole: (roleId: string) =>
    apiFetch<void>(`/roles/${roleId}`, { method: "DELETE" }),
};

export const tenantApi = {
  get: () => apiFetch<TenantSummary>("/tenant"),
  getSecurity: () => apiFetch<SecuritySettings>("/tenant/security"),
  setRequireAdminMfa: (require_admin_mfa: boolean) =>
    apiFetch<SecuritySettings>("/tenant/security", {
      method: "PATCH",
      body: JSON.stringify({ require_admin_mfa }),
    }),
  getCompanyProfile: () => apiFetch<CompanyProfile>("/tenant/profile"),
  updateCompanyProfile: (patch: CompanyProfilePatch) =>
    apiFetch<CompanyProfile>("/tenant/profile", {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),
  getSmtp: () => apiFetch<SmtpConfig>("/tenant/smtp"),
  updateSmtp: (patch: SmtpConfigUpdate) =>
    apiFetch<SmtpConfig>("/tenant/smtp", {
      method: "PUT",
      body: JSON.stringify(patch),
    }),
  testSmtp: (to_email: string) =>
    apiFetch<SmtpTestResult>("/tenant/smtp/test", {
      method: "POST",
      body: JSON.stringify({ to_email }),
    }),
};

export const auditApi = {
  list: (cursor?: string, includeSystem = false) => {
    const params = new URLSearchParams();
    if (cursor) params.set("cursor", cursor);
    if (includeSystem) params.set("include_system", "true");
    const qs = params.toString();
    return apiFetch<CursorPage<AuditEvent>>(`/audit-log${qs ? `?${qs}` : ""}`);
  },
};

export const complianceApi = {
  listFrameworks: () => apiFetch<Framework[]>("/frameworks"),
  listRequirements: (frameworkId: string, versionId?: string) => {
    const qs = versionId ? `?version_id=${encodeURIComponent(versionId)}` : "";
    return apiFetch<Requirement[]>(`/frameworks/${frameworkId}/requirements${qs}`);
  },
  listControlTemplates: (query: ControlTemplateQuery = {}) => {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== "") params.set(key, String(value));
    }
    const qs = params.toString();
    return apiFetch<ControlTemplatePage>(`/control-templates${qs ? `?${qs}` : ""}`);
  },
  getControlTemplate: (templateId: string) =>
    apiFetch<ControlTemplateDetail>(`/control-templates/${templateId}`),
};

export const controlsApi = {
  list: (query: ControlQuery = {}) => {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== "") params.set(key, String(value));
    }
    const qs = params.toString();
    return apiFetch<Control[]>(`/controls${qs ? `?${qs}` : ""}`);
  },
  get: (controlId: string) => apiFetch<Control>(`/controls/${controlId}`),
  vocabulary: () => apiFetch<ControlVocabulary>("/controls/vocabulary"),
  adopt: (requirement_ids?: string[]) =>
    apiFetch<AdoptLibraryResult>("/controls/adopt", {
      method: "POST",
      body: JSON.stringify(requirement_ids ? { requirement_ids } : {}),
    }),
  create: (body: ControlCreateRequest) =>
    apiFetch<Control>("/controls", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  update: (controlId: string, body: ControlUpdateRequest) =>
    apiFetch<Control>(`/controls/${controlId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  disable: (controlId: string, reason: string) =>
    apiFetch<Control>(`/controls/${controlId}/disable`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
  enable: (controlId: string) =>
    apiFetch<Control>(`/controls/${controlId}/enable`, { method: "POST" }),
};

export const engagementApi = {
  get: () => apiFetch<Engagement | null>("/engagement"),
  put: (body: EngagementPut) =>
    apiFetch<Engagement>("/engagement", {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  scope: () => apiFetch<ScopeCriterion[]>("/engagement/scope"),
  coverage: () => apiFetch<Coverage>("/engagement/coverage"),
};

export const evidenceApi = {
  list: (query: EvidenceQuery = {}) => {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== "") params.set(key, String(value));
    }
    const qs = params.toString();
    return apiFetch<Evidence[]>(`/evidence${qs ? `?${qs}` : ""}`);
  },
  get: (id: string) => apiFetch<Evidence>(`/evidence/${id}`),
  vocabulary: () => apiFetch<EvidenceVocabulary>("/evidence/vocabulary"),
  addLink: (body: EvidenceLinkCreate) =>
    apiFetch<Evidence>("/evidence/link", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  /** Multipart: the body is FormData, so no JSON Content-Type is set — the
   *  browser must supply its own boundary. */
  uploadFile: (form: FormData) =>
    apiFetch<Evidence>("/evidence/file", { method: "POST", body: form }),
  update: (id: string, body: EvidenceUpdate) =>
    apiFetch<Evidence>(`/evidence/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  downloadUrl: (id: string) => `/api/v1/evidence/${id}/download`,
};
