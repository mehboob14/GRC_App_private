import type {
  AuditEvent,
  BuiltInRoleName,
  Group,
  Member,
  PermissionKey,
  Role,
  SecurityPolicy,
  SessionPrincipal,
  User,
  WorkspaceSummary,
} from "@/lib/api/types";

const ALL_PERMS: PermissionKey[] = [
  "tenant:read",
  "members:read",
  "members:invite",
  "members:disable",
  "groups:read",
  "groups:manage",
  "roles:read",
  "roles:manage",
  "audit:read",
];

export const DEMO_PASSWORD = "Password123!";
export const DEMO_MFA_CODE = "123456";

export const users: Record<string, User & { password: string }> = {
  "user-alex": {
    id: "user-alex",
    email: "alex.okafor@northwind.cloud",
    full_name: "Alex Okafor",
    status: "active",
    mfa_enabled: true,
    password: DEMO_PASSWORD,
  },
  "user-jordan": {
    id: "user-jordan",
    email: "jordan.park@northwind.cloud",
    full_name: "Jordan Park",
    status: "active",
    mfa_enabled: true,
    password: DEMO_PASSWORD,
  },
  "user-marcus": {
    id: "user-marcus",
    email: "marcus.bell@northwind.cloud",
    full_name: "Marcus Bell",
    status: "active",
    mfa_enabled: false,
    password: DEMO_PASSWORD,
  },
  "user-dana": {
    id: "user-dana",
    email: "dana.brenner@audit.example",
    full_name: "Dana Brenner",
    status: "active",
    mfa_enabled: true,
    password: DEMO_PASSWORD,
  },
};

export const roles: Role[] = [
  {
    id: "role-admin",
    name: "Admin" satisfies BuiltInRoleName,
    built_in: true,
    permission_keys: ALL_PERMS,
    assignment_count: 1,
  },
  {
    id: "role-cm",
    name: "Compliance Manager" satisfies BuiltInRoleName,
    built_in: true,
    permission_keys: [
      "tenant:read",
      "members:read",
      "groups:read",
      "roles:read",
      "audit:read",
    ],
    assignment_count: 1,
  },
  {
    id: "role-owner",
    name: "Control Owner" satisfies BuiltInRoleName,
    built_in: true,
    permission_keys: ["tenant:read"],
    assignment_count: 1,
  },
  {
    id: "role-employee",
    name: "Employee" satisfies BuiltInRoleName,
    built_in: true,
    permission_keys: ["tenant:read"],
    assignment_count: 1,
  },
  {
    id: "role-auditor",
    name: "Auditor" satisfies BuiltInRoleName,
    built_in: true,
    permission_keys: ["tenant:read", "audit:read"],
    assignment_count: 1,
  },
];

export const groups: Group[] = [
  {
    id: "group-sec",
    name: "Security",
    member_count: 1,
    member_ids: ["mem-alex-nw"],
  },
  {
    id: "group-eng",
    name: "Engineering",
    member_count: 2,
    member_ids: ["mem-alex-nw", "mem-marcus-nw"],
  },
  {
    id: "group-infra",
    name: "Infrastructure",
    member_count: 1,
    member_ids: ["mem-jordan-nw"],
  },
  {
    id: "group-ext",
    name: "External",
    member_count: 1,
    member_ids: ["mem-dana-nw"],
  },
];

export let members: Member[] = [
  {
    membership_id: "mem-alex-nw",
    user_id: "user-alex",
    full_name: "Alex Okafor",
    email: "alex.okafor@northwind.cloud",
    status: "active",
    role_names: ["Admin"],
    group_names: ["Security", "Engineering"],
    mfa_enabled: true,
  },
  {
    membership_id: "mem-jordan-nw",
    user_id: "user-jordan",
    full_name: "Jordan Park",
    email: "jordan.park@northwind.cloud",
    status: "active",
    role_names: ["Compliance Manager"],
    group_names: ["Infrastructure"],
    mfa_enabled: true,
  },
  {
    membership_id: "mem-marcus-nw",
    user_id: "user-marcus",
    full_name: "Marcus Bell",
    email: "marcus.bell@northwind.cloud",
    status: "active",
    role_names: ["Employee"],
    group_names: ["Engineering"],
    mfa_enabled: false,
  },
  {
    membership_id: "mem-dana-nw",
    user_id: "user-dana",
    full_name: "Dana Brenner",
    email: "dana.brenner@audit.example",
    status: "active",
    role_names: ["Auditor"],
    group_names: ["External"],
    mfa_enabled: true,
  },
  {
    membership_id: "mem-alex-acme",
    user_id: "user-alex",
    full_name: "Alex Okafor",
    email: "alex.okafor@northwind.cloud",
    status: "active",
    role_names: ["Admin"],
    group_names: [],
    mfa_enabled: true,
  },
];

type TenantRef = {
  tenant_id: string;
  tenant_name: string;
  tenant_slug: string;
};

export const membershipTenants: Record<string, TenantRef> = {
  "mem-alex-nw": {
    tenant_id: "tenant-northwind",
    tenant_name: "Northwind Cloud",
    tenant_slug: "northwind",
  },
  "mem-jordan-nw": {
    tenant_id: "tenant-northwind",
    tenant_name: "Northwind Cloud",
    tenant_slug: "northwind",
  },
  "mem-marcus-nw": {
    tenant_id: "tenant-northwind",
    tenant_name: "Northwind Cloud",
    tenant_slug: "northwind",
  },
  "mem-dana-nw": {
    tenant_id: "tenant-northwind",
    tenant_name: "Northwind Cloud",
    tenant_slug: "northwind",
  },
  "mem-alex-acme": {
    tenant_id: "tenant-acme",
    tenant_name: "Acme Holdings",
    tenant_slug: "acme",
  },
};

function tenantForMembership(membershipId: string): TenantRef {
  const mapped = membershipTenants[membershipId];
  if (mapped) return mapped;
  if (membershipId.endsWith("-acme")) {
    return {
      tenant_id: "tenant-acme",
      tenant_name: "Acme Holdings",
      tenant_slug: "acme",
    };
  }
  return {
    tenant_id: "tenant-northwind",
    tenant_name: "Northwind Cloud",
    tenant_slug: "northwind",
  };
}

export function membersForTenant(tenantId: string): Member[] {
  return members.filter(
    (m) => tenantForMembership(m.membership_id).tenant_id === tenantId,
  );
}

export const workspacesForUser = (userId: string): WorkspaceSummary[] => {
  return members
    .filter((m) => m.user_id === userId && m.status === "active")
    .map((m) => {
      const tenant = tenantForMembership(m.membership_id);
      return {
        membership_id: m.membership_id,
        tenant_id: tenant.tenant_id,
        tenant_name: tenant.tenant_name,
        tenant_slug: tenant.tenant_slug,
        role_name: m.role_names[0] ?? "Employee",
        status: m.status,
      };
    });
};

export function principalFromMembership(
  membershipId: string,
): SessionPrincipal | null {
  const member = members.find((m) => m.membership_id === membershipId);
  if (!member || member.status !== "active") return null;
  const user = users[member.user_id];
  if (!user) return null;
  const role = roles.find((r) => r.name === member.role_names[0]);
  const tenant = tenantForMembership(membershipId);
  return {
    user: {
      id: user.id,
      email: user.email,
      full_name: user.full_name,
      status: user.status,
      mfa_enabled: user.mfa_enabled,
    },
    membership_id: membershipId,
    tenant_id: tenant.tenant_id,
    tenant_name: tenant.tenant_name,
    permissions: role?.permission_keys ?? ["tenant:read"],
    role_names: member.role_names,
  };
}

export let securityPolicy: SecurityPolicy = {
  require_mfa: true,
  enforce_sso: false,
  ip_allowlist: false,
  audit_log_export: false,
  session_timeout_hours: 8,
};

export let auditEvents: AuditEvent[] = [
  {
    id: "aud-1",
    tenant_id: "tenant-northwind",
    actor_type: "membership",
    actor_id: "mem-alex-nw",
    actor_label: "Alex Okafor",
    action: "create",
    object_type: "session",
    object_id: "sess-1",
    object_label: "Session",
    before: null,
    after: { membership_id: "mem-alex-nw" },
    occurred_at: "2026-08-11T14:02:00.000Z",
  },
  {
    id: "aud-2",
    tenant_id: "tenant-northwind",
    actor_type: "membership",
    actor_id: "mem-alex-nw",
    actor_label: "Alex Okafor",
    action: "create",
    object_type: "tenant_membership",
    object_id: "mem-marcus-nw",
    object_label: "Marcus Bell",
    before: null,
    after: { email: "marcus.bell@northwind.cloud", role: "Employee" },
    occurred_at: "2026-08-11T13:40:00.000Z",
  },
  {
    id: "aud-3",
    tenant_id: "tenant-northwind",
    actor_type: "membership",
    actor_id: "mem-alex-nw",
    actor_label: "Alex Okafor",
    action: "update",
    object_type: "role_assignment",
    object_id: "ra-1",
    object_label: "Jordan Park → Compliance Manager",
    before: { role: "Employee" },
    after: { role: "Compliance Manager" },
    occurred_at: "2026-08-11T12:15:00.000Z",
  },
  {
    id: "aud-4",
    tenant_id: "tenant-northwind",
    actor_type: "membership",
    actor_id: "mem-alex-nw",
    actor_label: "Alex Okafor",
    action: "create",
    object_type: "group",
    object_id: "group-sec",
    object_label: "Security",
    before: null,
    after: { name: "Security" },
    occurred_at: "2026-08-10T18:00:00.000Z",
  },
];

export function pushAudit(
  partial: Omit<AuditEvent, "id" | "occurred_at" | "tenant_id"> & {
    tenant_id?: string;
  },
): void {
  auditEvents = [
    {
      id: `aud-${crypto.randomUUID()}`,
      tenant_id: partial.tenant_id ?? "tenant-northwind",
      occurred_at: new Date().toISOString(),
      ...partial,
    },
    ...auditEvents,
  ];
}

export function findUserByEmail(email: string) {
  return Object.values(users).find(
    (u) => u.email.toLowerCase() === email.toLowerCase(),
  );
}

/** Outstanding one-time invite tokens → the invited membership id. */
export const invites = new Map<string, string>();

export function tokenFor(membershipId: string): string {
  return `mock-token:${membershipId}`;
}

export function membershipFromToken(authHeader: string | null): string | null {
  if (!authHeader?.startsWith("Bearer mock-token:")) return null;
  return authHeader.slice("Bearer mock-token:".length);
}
