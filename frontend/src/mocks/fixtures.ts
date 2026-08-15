import { PERMISSION_KEYS } from "@/lib/api/types";
import type {
  AuditEvent,
  BuiltInRoleName,
  Group,
  Member,
  PermissionKey,
  Role,
  SessionPrincipal,
  User,
  WorkspaceSummary,
} from "@/lib/api/types";

const ALL_PERMS: PermissionKey[] = [...PERMISSION_KEYS];

export const DEMO_PASSWORD = "Password123!";
export const DEMO_MFA_CODE = "123456";

export const users: Record<
  string,
  User & { password: string; email_verified: boolean }
> = {
  "user-alex": {
    id: "user-alex",
    email: "alex.okafor@northwind.cloud",
    full_name: "Alex Okafor",
    status: "active",
    mfa_enabled: true,
    password: DEMO_PASSWORD,
    // Stable demo accounts are pre-verified so existing mock sign-in still works.
    email_verified: true,
  },
  "user-jordan": {
    id: "user-jordan",
    email: "jordan.park@northwind.cloud",
    full_name: "Jordan Park",
    status: "active",
    mfa_enabled: true,
    password: DEMO_PASSWORD,
    // Stable demo accounts are pre-verified so existing mock sign-in still works.
    email_verified: true,
  },
  "user-marcus": {
    id: "user-marcus",
    email: "marcus.bell@northwind.cloud",
    full_name: "Marcus Bell",
    status: "active",
    mfa_enabled: false,
    password: DEMO_PASSWORD,
    // Stable demo accounts are pre-verified so existing mock sign-in still works.
    email_verified: true,
  },
  "user-dana": {
    id: "user-dana",
    email: "dana.brenner@audit.example",
    full_name: "Dana Brenner",
    status: "active",
    mfa_enabled: true,
    password: DEMO_PASSWORD,
    // Stable demo accounts are pre-verified so existing mock sign-in still works.
    email_verified: true,
  },
  "user-priya": {
    id: "user-priya",
    email: "priya.raman@northwind.cloud",
    full_name: "Priya Raman",
    status: "active",
    mfa_enabled: false,
    password: DEMO_PASSWORD,
    // Stable demo accounts are pre-verified so existing mock sign-in still works.
    email_verified: true,
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
    // Marcus (active) + Priya (invited).
    assignment_count: 2,
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

const hoursAgo = (h: number) => new Date(Date.now() - h * 3_600_000).toISOString();

export const members: Member[] = [
  {
    membership_id: "mem-alex-nw",
    user_id: "user-alex",
    full_name: "Alex Okafor",
    email: "alex.okafor@northwind.cloud",
    status: "active",
    role_names: ["Admin"],
    group_names: ["Security", "Engineering"],
    mfa_enabled: true,
    last_login_at: hoursAgo(3),
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
    last_login_at: hoursAgo(28),
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
    last_login_at: hoursAgo(5),
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
    last_login_at: hoursAgo(24 * 40),
  },
  {
    membership_id: "mem-priya-nw",
    user_id: "user-priya",
    full_name: "Priya Raman",
    email: "priya.raman@northwind.cloud",
    status: "invited",
    role_names: ["Employee"],
    group_names: [],
    mfa_enabled: false,
    last_login_at: null,
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
    last_login_at: hoursAgo(3),
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
  "mem-priya-nw": {
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

type SeedEvent = Omit<AuditEvent, "id" | "tenant_id" | "occurred_at">;

const ALEX = {
  actor_type: "membership" as const,
  actor_id: "mem-alex-nw",
  actor_label: "Alex Okafor",
};
const JORDAN = {
  actor_type: "membership" as const,
  actor_id: "mem-jordan-nw",
  actor_label: "Jordan Park",
};
const SYSTEM = {
  actor_type: "system" as const,
  actor_id: null,
  actor_label: "Verity platform",
};

/**
 * Seed trail, newest first. Enough rows (> one page of 15) that cursor
 * pagination is exercised in the mock environment.
 */
const SEED_EVENTS: SeedEvent[] = [
  { ...ALEX, action: "create", object_type: "session", object_id: "sess-1", object_label: "Session", before: null, after: { membership_id: "mem-alex-nw", mfa: true } },
  { ...ALEX, action: "create", object_type: "tenant_membership", object_id: "mem-marcus-nw", object_label: "Marcus Bell", before: null, after: { email: "marcus.bell@northwind.cloud", role: "Employee" } },
  { ...ALEX, action: "update", object_type: "role_assignment", object_id: "ra-1", object_label: "Jordan Park → Compliance Manager", before: { role: "Employee" }, after: { role: "Compliance Manager" } },
  { ...JORDAN, action: "create", object_type: "session", object_id: "sess-2", object_label: "Session", before: null, after: { membership_id: "mem-jordan-nw", mfa: true } },
  { ...ALEX, action: "create", object_type: "group", object_id: "group-sec", object_label: "Security", before: null, after: { name: "Security" } },
  { ...ALEX, action: "create", object_type: "group", object_id: "group-eng", object_label: "Engineering", before: null, after: { name: "Engineering" } },
  { ...ALEX, action: "update", object_type: "group", object_id: "group-eng", object_label: "Engineering", before: { member_count: 1 }, after: { member_count: 2 } },
  { ...SYSTEM, action: "update", object_type: "tenant", object_id: "tenant-northwind", object_label: "Northwind Cloud", before: { status: "provisioning" }, after: { status: "active" } },
  { ...ALEX, action: "create", object_type: "tenant_membership", object_id: "mem-dana-nw", object_label: "Dana Brenner", before: null, after: { email: "dana.brenner@audit.example", role: "Auditor" } },
  { ...JORDAN, action: "update", object_type: "tenant_membership", object_id: "mem-dana-nw", object_label: "Dana Brenner", before: { status: "invited" }, after: { status: "active" } },
  { ...ALEX, action: "create", object_type: "group", object_id: "group-infra", object_label: "Infrastructure", before: null, after: { name: "Infrastructure" } },
  { ...ALEX, action: "create", object_type: "group", object_id: "group-ext", object_label: "External", before: null, after: { name: "External" } },
  { ...JORDAN, action: "create", object_type: "session", object_id: "sess-3", object_label: "Session", before: null, after: { membership_id: "mem-jordan-nw", mfa: true } },
  { ...ALEX, action: "update", object_type: "user_mfa", object_id: "user-alex", object_label: "Alex Okafor", before: { mfa_enabled: false }, after: { mfa_enabled: true } },
  { ...ALEX, action: "create", object_type: "tenant_membership", object_id: "mem-jordan-nw", object_label: "Jordan Park", before: null, after: { email: "jordan.park@northwind.cloud", role: "Employee" } },
  { ...JORDAN, action: "update", object_type: "tenant_membership", object_id: "mem-jordan-nw", object_label: "Jordan Park", before: { status: "invited" }, after: { status: "active" } },
  { ...ALEX, action: "create", object_type: "session", object_id: "sess-4", object_label: "Session", before: null, after: { membership_id: "mem-alex-nw", mfa: true } },
  { ...SYSTEM, action: "update", object_type: "tenant", object_id: "tenant-northwind", object_label: "Northwind Cloud", before: { name: "Northwind" }, after: { name: "Northwind Cloud" } },
  { ...ALEX, action: "create", object_type: "session", object_id: "sess-5", object_label: "Session", before: null, after: { membership_id: "mem-alex-nw", mfa: true } },
  { ...SYSTEM, action: "create", object_type: "tenant", object_id: "tenant-northwind", object_label: "Northwind Cloud", before: null, after: { name: "Northwind", status: "provisioning" } },
];

export let auditEvents: AuditEvent[] = SEED_EVENTS.map((event, index) => ({
  ...event,
  id: `aud-${index + 1}`,
  tenant_id: "tenant-northwind",
  // Space seed events ~3h40m apart, newest at the fixed demo "now".
  occurred_at: new Date(
    Date.parse("2026-08-11T14:02:00.000Z") - index * 13_200_000,
  ).toISOString(),
}));

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

// Stable demo invite: mock state is in-memory, so an ad-hoc invite dies on a
// full page reload before it can be accepted. This one always exists — open
// /accept-invite?token=invite-demo-priya while signed out to walk the
// accept journey end to end.
invites.set("invite-demo-priya", "mem-priya-nw");

/**
 * Guest access windows keyed by membership id. The mock only stores them —
 * nothing here enforces the window; the real backend models it on the role
 * assignment and refuses sessions outside it.
 */
export const accessWindows = new Map<
  string,
  { valid_from?: string; valid_until?: string }
>();

export function tokenFor(membershipId: string): string {
  return `mock-token:${membershipId}`;
}

export function membershipFromToken(authHeader: string | null): string | null {
  if (!authHeader?.startsWith("Bearer mock-token:")) return null;
  return authHeader.slice("Bearer mock-token:".length);
}
