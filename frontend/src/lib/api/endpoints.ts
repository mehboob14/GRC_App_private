import { apiFetch } from "@/lib/api/client";
import type {
  AcceptInvitationRequest,
  AcceptInvitationResponse,
  AdoptLibraryResult,
  AuditEvent,
  AuditType,
  Control,
  ControlCreateRequest,
  ControlQuery,
  ControlTemplateDetail,
  ControlTemplatePage,
  ControlTemplateQuery,
  ControlUpdateRequest,
  ControlVocabulary,
  ComplianceDashboard,
  ControlReport,
  Coverage,
  CursorPage,
  Engagement,
  EngagementPut,
  ScopeItem,
  ScopeItemKind,
  Milestone,
  EngagementCycle,
  PeriodChange,
  Commitment,
  EngagementVendor,
  ScopeSuggestion,
  Evidence,
  EvidenceLinkCreate,
  EvidenceQuery,
  EvidenceUpdate,
  EvidenceVocabulary,
  LinkedRecord,
  LinkTargetType,
  MappingSuggestions,
  MaturityResult,
  Framework,
  Group,
  InviteMemberRequest,
  InviteMemberResponse,
  LoginPasswordRequest,
  LoginResponse,
  SessionPrincipal,
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
  ProfileSection,
  ProfileVersion,
  SecuritySettings,
  SecuritySettingsPatch,
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
  /** The caller's principal, read fresh from the server (not the cached copy). */
  me: () => apiFetch<SessionPrincipal>("/auth/me"),
  logout: () => apiFetch<void>("/auth/logout", { method: "POST" }),
  /** Sign in through Keycloak (openspec/changes/add-keycloak-sso). */
  ssoStatus: () => apiFetch<{ enabled: boolean }>("/auth/sso/status"),
  ssoStart: (email: string) =>
    apiFetch<{ authorize_url: string }>(`/auth/sso/start?email=${encodeURIComponent(email)}`),
  ssoComplete: (handoff: string) =>
    apiFetch<LoginResponse>("/auth/sso/complete", {
      method: "POST",
      body: JSON.stringify({ handoff }),
    }),
  ssoEndSession: () =>
    apiFetch<{ end_session_url: string | null }>("/auth/sso/end-session", { method: "POST" }),
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
  /** Correct a member's display name (global to the person, ADR-0011). */
  renameMember: (membershipId: string, full_name: string) =>
    apiFetch<Member>(`/members/${membershipId}`, {
      method: "PATCH",
      body: JSON.stringify({ full_name }),
    }),
  disableMember: (membershipId: string) =>
    apiFetch<Member>(`/members/${membershipId}/disable`, { method: "POST" }),
  assignRole: (membershipId: string, roleId: string) =>
    apiFetch<Member>(`/members/${membershipId}/roles`, {
      method: "PUT",
      body: JSON.stringify({ role_id: roleId }),
    }),
  listGroups: () => apiFetch<Group[]>("/groups"),
  createGroup: (body: { name: string; description?: string | null }) =>
    apiFetch<Group>("/groups", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  updateGroup: (
    groupId: string,
    body: { name?: string; description?: string | null },
  ) =>
    apiFetch<Group>(`/groups/${groupId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  deleteGroup: (groupId: string) =>
    apiFetch<void>(`/groups/${groupId}`, { method: "DELETE" }),
  addGroupMember: (groupId: string, membershipId: string) =>
    apiFetch<Group>(`/groups/${groupId}/members`, {
      method: "POST",
      body: JSON.stringify({ membership_id: membershipId }),
    }),
  removeGroupMember: (groupId: string, membershipId: string) =>
    apiFetch<Group>(`/groups/${groupId}/members/${membershipId}`, {
      method: "DELETE",
    }),
  listRoles: () => apiFetch<Role[]>("/roles"),
  createRole: (body: {
    name: string;
    description?: string | null;
    permission_keys: string[];
  }) =>
    apiFetch<Role>("/roles", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  updateRole: (
    roleId: string,
    body: {
      name?: string;
      description?: string | null;
      permission_keys?: string[];
    },
  ) =>
    apiFetch<Role>(`/roles/${roleId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  deleteRole: (roleId: string) =>
    apiFetch<void>(`/roles/${roleId}`, { method: "DELETE" }),
  /**
   * Assign one role to a membership. The backend is idempotent per assignee, so
   * the multi-select picker just calls this once per person rather than needing
   * a bulk endpoint.
   */
  assignRoleTo: (roleId: string, membershipId: string) =>
    apiFetch<unknown>(`/roles/${roleId}/assignments`, {
      method: "POST",
      body: JSON.stringify({
        assignee_type: "membership",
        assignee_id: membershipId,
      }),
    }),
};

export const tenantApi = {
  get: () => apiFetch<TenantSummary>("/tenant"),
  getSecurity: () => apiFetch<SecuritySettings>("/tenant/security"),
  setRequireAdminMfa: (require_admin_mfa: boolean) =>
    apiFetch<SecuritySettings>("/tenant/security", {
      method: "PATCH",
      body: JSON.stringify({ require_admin_mfa }),
    }),
  /** Patch any subset of the security policy — the screen sends what changed. */
  updateSecurity: (patch: SecuritySettingsPatch) =>
    apiFetch<SecuritySettings>("/tenant/security", {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),
  getCompanyProfile: () => apiFetch<CompanyProfile>("/tenant/profile"),
  updateCompanyProfile: (patch: CompanyProfilePatch) =>
    apiFetch<CompanyProfile>("/tenant/profile", {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),
  getProfileQuestions: () => apiFetch<ProfileSection[]>("/tenant/profile/questions"),
  confirmCompanyProfile: () =>
    apiFetch<CompanyProfile>("/tenant/profile/confirm", { method: "POST" }),
  getProfileVersions: () => apiFetch<ProfileVersion[]>("/tenant/profile/versions"),
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
  list: (
    cursor?: string,
    includeSystem = false,
    /** Scope to one record — what a per-object History tab needs, so the
     *  client does not pull the whole trail and filter it locally. */
    object?: { type: string; id: string },
  ) => {
    const params = new URLSearchParams();
    if (cursor) params.set("cursor", cursor);
    if (includeSystem) params.set("include_system", "true");
    if (object) {
      params.set("object_type", object.type);
      params.set("object_id", object.id);
    }
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
  report: () => apiFetch<ControlReport>("/controls/report"),
  reportExportUrl: (format: "csv" | "xlsx") =>
    `/api/v1/controls/report/export?format=${format}`,
};

/** `?framework=CODE`, or nothing for SOC 2, which is what every read answered before a
 *  second framework existed. */
const frameworkQuery = (framework?: string) =>
  framework && framework !== "SOC2" ? `?framework=${encodeURIComponent(framework)}` : "";

export const engagementApi = {
  get: (framework?: string) =>
    apiFetch<Engagement | null>(`/engagement${frameworkQuery(framework)}`),
  scopeItems: (framework: string) =>
    apiFetch<ScopeItem[]>(`/engagement/scope-items?framework=${encodeURIComponent(framework)}`),
  addScopeItem: (body: { kind: ScopeItemKind; name: string }) =>
    apiFetch<ScopeItem>("/engagement/scope-items", { method: "POST", body: JSON.stringify(body) }),
  decideScopeItem: (id: string, framework: string, body: { in_scope: boolean; reason: string | null }) =>
    apiFetch<{ item: ScopeItem; notices: string[] }>(
      `/engagement/scope-items/${id}/decision?framework=${encodeURIComponent(framework)}`,
      { method: "PUT", body: JSON.stringify(body) },
    ),
  milestones: (framework: string) =>
    apiFetch<Milestone[]>(`/engagement/milestones?framework=${encodeURIComponent(framework)}`),
  saveMilestones: (
    framework: string,
    milestones: { kind: string; planned_on: string | null; actual_on: string | null }[],
  ) =>
    apiFetch<Milestone[]>(`/engagement/milestones?framework=${encodeURIComponent(framework)}`, {
      method: "PUT",
      body: JSON.stringify({ milestones }),
    }),
  cycles: (framework: string) =>
    apiFetch<EngagementCycle[]>(`/engagement/cycles?framework=${encodeURIComponent(framework)}`),
  nextCycle: (framework: string, body: { name: string; audit_type: AuditType }) =>
    apiFetch<EngagementCycle>(`/engagement/next-cycle?framework=${encodeURIComponent(framework)}`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  changes: (framework: string) =>
    apiFetch<PeriodChange[]>(`/engagement/changes?framework=${encodeURIComponent(framework)}`),
  vendors: (framework: string) =>
    apiFetch<EngagementVendor[]>(`/engagement/vendors?framework=${encodeURIComponent(framework)}`),
  setVendor: (
    framework: string,
    vendorId: string,
    body: { role: "subservice" | "supplier"; method: "carve_out" | "included" | null; note: string | null },
  ) =>
    apiFetch<void>(`/engagement/vendors/${vendorId}?framework=${encodeURIComponent(framework)}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  removeVendor: (framework: string, vendorId: string, reason: string) =>
    apiFetch<void>(
      `/engagement/vendors/${vendorId}/remove?framework=${encodeURIComponent(framework)}`,
      { method: "POST", body: JSON.stringify({ reason }) },
    ),
  scopeSuggestions: () => apiFetch<ScopeSuggestion[]>("/engagement/scope-suggestions"),
  acceptScopeSuggestions: (refs: { ref_type: string; ref_id: string }[]) =>
    apiFetch<{ added: number }>("/engagement/scope-suggestions/accept", {
      method: "POST",
      body: JSON.stringify({ refs }),
    }),
  commitments: () => apiFetch<Commitment[]>("/commitments"),
  addCommitment: (body: Omit<Commitment, "id">) =>
    apiFetch<Commitment>("/commitments", { method: "POST", body: JSON.stringify(body) }),
  retireCommitment: (id: string, reason: string) =>
    apiFetch<void>(`/commitments/${id}/retire`, { method: "POST", body: JSON.stringify({ reason }) }),
  deactivateFramework: (frameworkId: string, reason: string) =>
    apiFetch<{ controls_only_here: string[] }>(`/tenant-frameworks/${frameworkId}/deactivate`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
  retireScopeItem: (id: string, reason: string) =>
    apiFetch<{ notices: string[] }>(`/engagement/scope-items/${id}/retire`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
  put: (body: EngagementPut) =>
    apiFetch<Engagement>("/engagement", {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  scope: (framework?: string) =>
    apiFetch<ScopeCriterion[]>(`/engagement/scope${frameworkQuery(framework)}`),
  coverage: (framework?: string) =>
    apiFetch<Coverage>(`/engagement/coverage${frameworkQuery(framework)}`),
  dashboard: (range?: { from?: string; to?: string }, framework?: string) => {
    const params = new URLSearchParams();
    if (range?.from) params.set("from", range.from);
    if (range?.to) params.set("to", range.to);
    if (framework && framework !== "SOC2") params.set("framework", framework);
    const qs = params.toString();
    return apiFetch<ComplianceDashboard>(
      `/engagement/dashboard${qs ? `?${qs}` : ""}`,
    );
  },
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
  review: (id: string, body: { decision: "approved" | "rejected"; note?: string }) =>
    apiFetch<Evidence>(`/evidence/${id}/review`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  suggestMappings: (id: string) =>
    apiFetch<MappingSuggestions>(`/evidence/${id}/suggest-mappings`, { method: "POST" }),
  assessMaturity: (id: string, controlId: string) =>
    apiFetch<MaturityResult>(`/evidence/${id}/maturity`, {
      method: "POST",
      body: JSON.stringify({ control_id: controlId }),
    }),
  approveMapping: (id: string, controlId: string) =>
    apiFetch<Evidence>(`/evidence/${id}/mappings/approve`, {
      method: "POST",
      body: JSON.stringify({ control_id: controlId }),
    }),
  /** Records of every module this evidence is linked to. One endpoint serves
   *  them all; pass a targetType to narrow it to one. */
  links: (id: string, targetType?: LinkTargetType) =>
    apiFetch<LinkedRecord[]>(
      `/evidence/${id}/links${targetType ? `?target_type=${targetType}` : ""}`,
    ),
  link: (id: string, targetType: LinkTargetType, targetId: string) =>
    apiFetch<LinkedRecord[]>(`/evidence/${id}/links`, {
      method: "POST",
      body: JSON.stringify({ target_type: targetType, target_id: targetId }),
    }),
  unlink: (id: string, linkId: string) =>
    apiFetch<LinkedRecord[]>(`/evidence/${id}/links/${linkId}`, { method: "DELETE" }),
  downloadUrl: (id: string) => `/api/v1/evidence/${id}/download`,
};
