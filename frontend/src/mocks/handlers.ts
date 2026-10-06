import { http, HttpResponse, delay } from "msw";
import {
  DEMO_MFA_CODE,
  accessWindows,
  auditEvents,
  findUserByEmail,
  groups,
  invites,
  members,
  membersForTenant,
  membershipFromToken,
  membershipTenants,
  principalFromMembership,
  pushAudit,
  roles,
  tokenFor,
  users,
  workspacesForUser,
} from "@/mocks/fixtures";
import { isPermissionKey } from "@/lib/api/types";
import type {
  AcceptInvitationResponse,
  InviteMemberResponse,
  LoginResponse,
  Member,
  SignupRequest,
  TenantSummary,
} from "@/lib/api/types";

function err(status: number, code: string, message: string) {
  return HttpResponse.json(
    {
      error: {
        code,
        message,
        correlation_id: crypto.randomUUID(),
      },
    },
    { status },
  );
}

function successFromMembership(
  membershipId: string,
): Extract<LoginResponse, { status: "authenticated" }> | null {
  const principal = principalFromMembership(membershipId);
  if (!principal) return null;
  return {
    status: "authenticated",
    access_token: tokenFor(membershipId),
    principal,
    workspaces: workspacesForUser(principal.user.id),
  };
}

const challenges = new Map<
  string,
  { membershipId: string; kind: "mfa" | "enroll" | "select"; userId: string }
>();

// The most recent verify-first signup awaiting its emailed link. The mock has
// no real inbox, so verify-email accepts any non-empty token and redeems this.
// In-memory only, like the rest of the mock — it does not survive a reload.
let pendingVerification: { membershipId: string; userId: string } | null = null;

// Per-tenant admin-MFA toggle, off by default. In-memory, like the rest.
const requireAdminMfa: Record<string, boolean> = {};

export const handlers = [
  // Keepalive target for main.tsx: pinged so the browser never idle-kills
  // the MSW service worker (a restarted worker forgets its clients and
  // passes requests through to the dev proxy, which has no backend).
  http.get("/api/v1/_mock/health", () => HttpResponse.json({ ok: true })),

  http.post("/api/v1/auth/login", async ({ request }) => {
    await delay(250);
    const body = (await request.json()) as {
      email?: string;
      password?: string;
    };
    const user = findUserByEmail(body.email ?? "");
    // Constant-time-ish path for missing user
    if (!user || body.password !== user.password) {
      await delay(40);
      return err(401, "invalid_credentials", "Email or password is incorrect.");
    }

    // Verify-first: an unverified account never reaches a session, it is sent
    // back to the check-email surface (matches the backend's login gating).
    if (!user.email_verified) {
      return HttpResponse.json({
        status: "email_verification_required",
        email: user.email,
      } satisfies LoginResponse);
    }

    const workspaces = workspacesForUser(user.id);
    const firstWorkspace = workspaces[0];
    if (!firstWorkspace) {
      return err(401, "no_membership", "No active workspace membership.");
    }

    if (workspaces.length > 1) {
      const selection_token = crypto.randomUUID();
      challenges.set(selection_token, {
        membershipId: firstWorkspace.membership_id,
        kind: "select",
        userId: user.id,
      });
      return HttpResponse.json({
        status: "select_workspace",
        selection_token,
        workspaces,
      } satisfies LoginResponse);
    }

    const membershipId = firstWorkspace.membership_id;
    const member = members.find((m) => m.membership_id === membershipId);
    // Admin MFA is opt-in per tenant (default off). Only when the tenant has
    // turned it on does an Admin sign-in step up to enrol or verify a code.
    const isAdmin = member?.role_names.includes("Admin") ?? false;
    const mfaRequired = isAdmin && (requireAdminMfa[firstWorkspace.tenant_id] ?? false);

    if (mfaRequired) {
      if (!user.mfa_enabled) {
        const challenge_token = crypto.randomUUID();
        challenges.set(challenge_token, {
          membershipId,
          kind: "enroll",
          userId: user.id,
        });
        return HttpResponse.json({
          status: "mfa_enrollment_required",
          challenge_token,
          membership_id: membershipId,
        } satisfies LoginResponse);
      }
      const challenge_token = crypto.randomUUID();
      challenges.set(challenge_token, {
        membershipId,
        kind: "mfa",
        userId: user.id,
      });
      return HttpResponse.json({
        status: "mfa_required",
        challenge_token,
        membership_id: membershipId,
      } satisfies LoginResponse);
    }

    const result = successFromMembership(membershipId);
    if (!result) {
      return err(401, "no_membership", "No active workspace membership.");
    }
    pushAudit({
      actor_type: "membership",
      actor_id: membershipId,
      actor_label: user.full_name,
      action: "create",
      object_type: "session",
      object_id: crypto.randomUUID(),
      object_label: "Session",
      before: null,
      after: { membership_id: membershipId },
      tenant_id: result.principal.tenant_id,
    });
    return HttpResponse.json(result);
  }),

  http.post("/api/v1/auth/workspaces/select", async ({ request }) => {
    await delay(150);
    const body = (await request.json()) as {
      selection_token?: string;
      membership_id?: string;
    };
    const selectionToken = body.selection_token ?? "";
    const challenge = challenges.get(selectionToken);
    if (!challenge || challenge.kind !== "select") {
      return err(401, "invalid_challenge", "Workspace selection expired.");
    }
    const membershipId = body.membership_id ?? "";
    const allowed = workspacesForUser(challenge.userId).some(
      (w) => w.membership_id === membershipId,
    );
    if (!allowed) return err(404, "membership_not_found", "Membership not found.");

    const member = members.find((m) => m.membership_id === membershipId);
    const user = users[challenge.userId];
    if (!member || !user) {
      return err(404, "membership_not_found", "Membership not found.");
    }
    if (member.role_names.includes("Admin")) {
      const challenge_token = crypto.randomUUID();
      challenges.set(challenge_token, {
        membershipId,
        kind: user.mfa_enabled ? "mfa" : "enroll",
        userId: user.id,
      });
      challenges.delete(selectionToken);
      return HttpResponse.json(
        user.mfa_enabled
          ? {
              status: "mfa_required",
              challenge_token,
              membership_id: membershipId,
            }
          : {
              status: "mfa_enrollment_required",
              challenge_token,
              membership_id: membershipId,
            },
      );
    }

    challenges.delete(selectionToken);
    const result = successFromMembership(membershipId);
    if (!result) {
      return err(404, "membership_not_found", "Membership not found.");
    }
    return HttpResponse.json(result);
  }),

  http.post("/api/v1/auth/mfa/verify", async ({ request }) => {
    await delay(200);
    const body = (await request.json()) as {
      challenge_token?: string;
      code?: string;
    };
    const challengeToken = body.challenge_token ?? "";
    const challenge = challenges.get(challengeToken);
    if (!challenge || challenge.kind !== "mfa") {
      return err(401, "invalid_challenge", "MFA challenge expired.");
    }
    if (body.code !== DEMO_MFA_CODE) {
      return err(401, "invalid_mfa_code", "That code is incorrect or expired.");
    }
    challenges.delete(challengeToken);
    const result = successFromMembership(challenge.membershipId);
    if (!result) {
      return err(404, "membership_not_found", "Membership not found.");
    }
    pushAudit({
      actor_type: "membership",
      actor_id: challenge.membershipId,
      actor_label: result.principal.user.full_name,
      action: "create",
      object_type: "session",
      object_id: crypto.randomUUID(),
      object_label: "Session",
      before: null,
      after: { mfa: true },
      tenant_id: result.principal.tenant_id,
    });
    return HttpResponse.json(result);
  }),

  http.post("/api/v1/auth/mfa/enroll", async ({ request }) => {
    await delay(150);
    const body = (await request.json()) as { challenge_token?: string };
    const challenge = challenges.get(body.challenge_token ?? "");
    if (!challenge || challenge.kind !== "enroll") {
      return err(401, "invalid_challenge", "Enrollment challenge expired.");
    }
    const secret = "JBSWY3DPEHPK3PXP";
    const email = users[challenge.userId]?.email ?? "user@verity.local";
    return HttpResponse.json({
      challenge_token: body.challenge_token,
      secret,
      otpauth_url: `otpauth://totp/Verity:${encodeURIComponent(email)}?secret=${secret}&issuer=Verity`,
    });
  }),

  http.post("/api/v1/auth/mfa/confirm", async ({ request }) => {
    await delay(200);
    const body = (await request.json()) as {
      challenge_token?: string;
      code?: string;
    };
    const challengeToken = body.challenge_token ?? "";
    const challenge = challenges.get(challengeToken);
    if (!challenge || challenge.kind !== "enroll") {
      return err(401, "invalid_challenge", "Enrollment challenge expired.");
    }
    if (body.code !== DEMO_MFA_CODE) {
      return err(401, "invalid_mfa_code", "Enter the 6-digit code from your authenticator.");
    }
    const user = users[challenge.userId];
    if (user) user.mfa_enabled = true;
    const member = members.find((m) => m.membership_id === challenge.membershipId);
    if (member) member.mfa_enabled = true;
    challenges.delete(challengeToken);
    const result = successFromMembership(challenge.membershipId);
    if (!result) {
      return err(404, "membership_not_found", "Membership not found.");
    }
    return HttpResponse.json(result);
  }),

  http.post("/api/v1/auth/signup", async ({ request }) => {
    await delay(300);
    const body = (await request.json()) as SignupRequest;
    if (findUserByEmail(body.email)) {
      return err(409, "email_taken", "That work email is already registered.");
    }
    if (!body.company_name?.trim() || !body.full_name?.trim()) {
      return err(422, "validation_error", "Company name and full name are required.");
    }
    if ((body.password?.length ?? 0) < 10) {
      return err(
        422,
        "weak_password",
        "Use at least 10 characters for your password.",
      );
    }

    const userId = `user-${crypto.randomUUID().slice(0, 8)}`;
    const membershipId = `mem-${crypto.randomUUID().slice(0, 8)}`;
    const tenantId = `tenant-${crypto.randomUUID().slice(0, 8)}`;
    const slug = body.company_name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "")
      .slice(0, 32);
    users[userId] = {
      id: userId,
      email: body.email.toLowerCase(),
      full_name: body.full_name,
      status: "active",
      mfa_enabled: false,
      password: body.password,
      // Verify-first: unverified until the emailed link is redeemed.
      email_verified: false,
    };
    membershipTenants[membershipId] = {
      tenant_id: tenantId,
      tenant_name: body.company_name.trim(),
      tenant_slug: slug || tenantId,
    };
    members.push({
      membership_id: membershipId,
      user_id: userId,
      full_name: body.full_name,
      email: body.email.toLowerCase(),
      status: "active",
      role_names: ["Admin"],
      group_names: [],
      mfa_enabled: false,
      last_login_at: new Date().toISOString(),
    });

    // Verify-first: mail a link (mocked) and wait. MFA enrollment happens after
    // the token is redeemed at /verify-email, not here.
    pendingVerification = { membershipId, userId };

    pushAudit({
      actor_type: "membership",
      actor_id: membershipId,
      actor_label: body.full_name,
      action: "create",
      object_type: "tenant",
      object_id: tenantId,
      object_label: body.company_name,
      before: null,
      after: { name: body.company_name, status: "provisioning" },
      tenant_id: tenantId,
    });

    return HttpResponse.json({
      status: "email_verification_required",
      email: body.email.toLowerCase(),
    } satisfies LoginResponse);
  }),

  http.post("/api/v1/auth/verify-email", async ({ request }) => {
    await delay(200);
    const body = (await request.json()) as { token?: string };
    const token = (body.token ?? "").trim();
    // No inbox in the mock: any non-empty token redeems the pending signup.
    // "bad"/"invalid"/"expired" model the failed link so the error path is testable.
    if (!token || ["bad", "invalid", "expired"].includes(token.toLowerCase())) {
      return err(
        422,
        "invalid_input",
        "This verification link is invalid or has expired.",
      );
    }
    if (!pendingVerification) {
      return err(
        422,
        "invalid_input",
        "This verification link is invalid or has expired.",
      );
    }
    const { membershipId, userId } = pendingVerification;
    const user = users[userId];
    if (user) user.email_verified = true;
    pendingVerification = null;
    // MFA is opt-in and off for a brand-new workspace, so verification grants a
    // session outright — mirrors the backend's verify-email post-password step.
    const result = successFromMembership(membershipId);
    if (!result) {
      return err(401, "no_membership", "No active workspace membership.");
    }
    return HttpResponse.json(result);
  }),

  http.post("/api/v1/auth/verify-email/resend", async () => {
    await delay(150);
    // Always 202 with no body — no account disclosure.
    return new HttpResponse(null, { status: 202 });
  }),

  http.get("/api/v1/auth/workspaces", ({ request }) => {
    const membershipId = membershipFromToken(
      request.headers.get("Authorization"),
    );
    const principal = membershipId
      ? principalFromMembership(membershipId)
      : null;
    if (!principal) return err(401, "unauthenticated", "Sign in to continue.");
    return HttpResponse.json(workspacesForUser(principal.user.id));
  }),

  http.post("/api/v1/auth/workspaces/switch", async ({ request }) => {
    await delay(200);
    const membershipId = membershipFromToken(
      request.headers.get("Authorization"),
    );
    const current = membershipId
      ? principalFromMembership(membershipId)
      : null;
    if (!current) return err(401, "unauthenticated", "Sign in to continue.");

    const body = (await request.json()) as { membership_id?: string };
    const target = body.membership_id ?? "";
    const allowed = workspacesForUser(current.user.id).some(
      (w) => w.membership_id === target,
    );
    if (!allowed) return err(404, "membership_not_found", "Membership not found.");

    const result = successFromMembership(target);
    if (!result) {
      return err(404, "membership_not_found", "Membership not found.");
    }
    pushAudit({
      actor_type: "membership",
      actor_id: target,
      actor_label: current.user.full_name,
      action: "create",
      object_type: "session",
      object_id: crypto.randomUUID(),
      object_label: "Workspace switch",
      before: { membership_id: membershipId },
      after: { membership_id: target },
      tenant_id: result.principal.tenant_id,
    });
    return HttpResponse.json(result);
  }),

  http.get("/api/v1/members", ({ request }) => {
    const membershipId = membershipFromToken(
      request.headers.get("Authorization"),
    );
    const principal = membershipId
      ? principalFromMembership(membershipId)
      : null;
    if (!principal) return err(401, "unauthenticated", "Sign in to continue.");
    if (!principal.permissions.includes("members:read")) {
      return err(403, "permission_denied", "Missing permission: members:read");
    }
    return HttpResponse.json(membersForTenant(principal.tenant_id));
  }),

  http.post("/api/v1/members/invite", async ({ request }) => {
    await delay(200);
    const membershipId = membershipFromToken(
      request.headers.get("Authorization"),
    );
    const principal = membershipId
      ? principalFromMembership(membershipId)
      : null;
    if (!principal) return err(401, "unauthenticated", "Sign in to continue.");
    if (!principal.permissions.includes("members:invite")) {
      return err(403, "permission_denied", "Missing permission: members:invite");
    }
    const body = (await request.json()) as {
      email?: string;
      full_name?: string;
      role_id?: string;
      valid_from?: string;
      valid_until?: string;
    };
    const role = roles.find((r) => r.id === body.role_id);
    if (!role) return err(422, "validation_error", "Choose a role.");
    if (!body.email || !body.full_name) {
      return err(422, "validation_error", "Name and work email are required.");
    }
    if (body.valid_from && body.valid_until && body.valid_until <= body.valid_from) {
      return err(
        422,
        "invalid_access_window",
        "Access must end after it starts. Check the window dates.",
      );
    }

    const email = body.email.toLowerCase();
    const existing = membersForTenant(principal.tenant_id).find(
      (m) => m.email.toLowerCase() === email,
    );
    if (existing) {
      return err(
        409,
        "already_member",
        "That person already has a membership in this workspace.",
      );
    }

    let user = findUserByEmail(body.email);
    if (!user) {
      const userId = `user-${crypto.randomUUID().slice(0, 8)}`;
      users[userId] = {
        id: userId,
        email,
        full_name: body.full_name,
        status: "active",
        mfa_enabled: false,
        // Unusable until the invitee sets a password on accept.
        password: crypto.randomUUID(),
        // Invited users are verified by accepting the invitation, not by email.
        email_verified: false,
      };
      user = users[userId];
    }
    if (!user) return err(500, "internal", "Could not create the user.");
    const membershipIdNew = `mem-${crypto.randomUUID().slice(0, 8)}`;
    const tenantMeta = membershipTenants[principal.membership_id] ?? {
      tenant_id: principal.tenant_id,
      tenant_name: principal.tenant_name,
      tenant_slug: principal.tenant_id.replace(/^tenant-/, ""),
    };
    membershipTenants[membershipIdNew] = { ...tenantMeta };
    const newMember: Member = {
      membership_id: membershipIdNew,
      user_id: user.id,
      full_name: body.full_name,
      email,
      status: "invited",
      role_names: [role.name],
      group_names: [],
      mfa_enabled: user.mfa_enabled,
      last_login_at: null,
    };
    members.push(newMember);
    if (body.valid_from || body.valid_until) {
      // Stored only — the mock enforces nothing; the real backend models the
      // window on the role assignment (see lib/api/types.ts).
      accessWindows.set(membershipIdNew, {
        valid_from: body.valid_from,
        valid_until: body.valid_until,
      });
    }
    const inviteToken = `invite-${crypto.randomUUID()}`;
    invites.set(inviteToken, membershipIdNew);
    pushAudit({
      actor_type: "membership",
      actor_id: principal.membership_id,
      actor_label: principal.user.full_name,
      action: "create",
      object_type: "tenant_membership",
      object_id: newMember.membership_id,
      object_label: newMember.full_name,
      before: null,
      after: { email: newMember.email, role: role.name },
      tenant_id: principal.tenant_id,
    });
    return HttpResponse.json(
      {
        member: newMember,
        invite_token: inviteToken,
        // The mock has no mail server either — say so rather than imply delivery.
      email_sent: false,
      accept_url: `${window.location.origin}/accept-invite?token=${inviteToken}`,
      } satisfies InviteMemberResponse,
      { status: 201 },
    );
  }),

  http.post("/api/v1/auth/invitations/accept", async ({ request }) => {
    await delay(200);
    const body = (await request.json()) as {
      token?: string;
      full_name?: string;
      password?: string;
    };
    const token = body.token ?? "";
    const membershipId = invites.get(token);
    if (!membershipId) {
      return err(
        401,
        "invalid_invite",
        "This invite link is invalid or has expired. Ask a workspace admin to send a new one.",
      );
    }
    const member = members.find((m) => m.membership_id === membershipId);
    const user = member ? users[member.user_id] : undefined;
    if (!member || !user) {
      return err(404, "not_found", "Membership not found.");
    }
    if (member.status !== "invited") {
      invites.delete(token);
      return err(
        409,
        "invite_already_accepted",
        "This invitation was already accepted. Sign in with your email and password.",
      );
    }
    if (body.password !== undefined && body.password.length < 10) {
      return err(
        422,
        "weak_password",
        "Use at least 10 characters for your password.",
      );
    }
    if (body.password) {
      user.password = body.password;
    }
    if (body.full_name?.trim()) {
      user.full_name = body.full_name.trim();
      member.full_name = user.full_name;
    }
    // Accepting the invitation verifies the address (no separate email step).
    user.email_verified = true;
    member.status = "active";
    invites.delete(token);
    const tenant = membershipTenants[membershipId];
    pushAudit({
      actor_type: "membership",
      actor_id: membershipId,
      actor_label: member.full_name,
      action: "update",
      object_type: "tenant_membership",
      object_id: membershipId,
      object_label: member.full_name,
      before: { status: "invited" },
      after: { status: "active" },
      tenant_id: tenant?.tenant_id,
    });
    return HttpResponse.json({
      status: "accepted",
      tenant_name: tenant?.tenant_name ?? "your workspace",
    } satisfies AcceptInvitationResponse);
  }),

  http.post("/api/v1/members/:id/disable", async ({ params, request }) => {
    await delay(150);
    const membershipId = membershipFromToken(
      request.headers.get("Authorization"),
    );
    const principal = membershipId
      ? principalFromMembership(membershipId)
      : null;
    if (!principal) return err(401, "unauthenticated", "Sign in to continue.");
    if (!principal.permissions.includes("members:disable")) {
      return err(403, "permission_denied", "Missing permission: members:disable");
    }
    const member = members.find((m) => m.membership_id === params.id);
    if (!member) return err(404, "not_found", "Member not found.");
    const before = { ...member };
    member.status = "disabled";
    pushAudit({
      actor_type: "membership",
      actor_id: principal.membership_id,
      actor_label: principal.user.full_name,
      action: "update",
      object_type: "tenant_membership",
      object_id: member.membership_id,
      object_label: member.full_name,
      before: { status: before.status },
      after: { status: "disabled" },
      tenant_id: principal.tenant_id,
    });
    return HttpResponse.json(member);
  }),

  http.put("/api/v1/members/:id/roles", async ({ params, request }) => {
    await delay(150);
    const membershipId = membershipFromToken(
      request.headers.get("Authorization"),
    );
    const principal = membershipId
      ? principalFromMembership(membershipId)
      : null;
    if (!principal) return err(401, "unauthenticated", "Sign in to continue.");
    if (!principal.permissions.includes("roles:manage")) {
      return err(403, "permission_denied", "Missing permission: roles:manage");
    }
    const body = (await request.json()) as { role_id?: string };
    const role = roles.find((r) => r.id === body.role_id);
    const member = members.find((m) => m.membership_id === params.id);
    if (!member || !role) return err(404, "not_found", "Member or role not found.");
    const before = [...member.role_names];
    member.role_names = [role.name];
    pushAudit({
      actor_type: "membership",
      actor_id: principal.membership_id,
      actor_label: principal.user.full_name,
      action: "update",
      object_type: "role_assignment",
      object_id: member.membership_id,
      object_label: `${member.full_name} → ${role.name}`,
      before: { roles: before },
      after: { roles: member.role_names },
      tenant_id: principal.tenant_id,
    });
    return HttpResponse.json(member);
  }),

  http.get("/api/v1/groups", ({ request }) => {
    const membershipId = membershipFromToken(
      request.headers.get("Authorization"),
    );
    const principal = membershipId
      ? principalFromMembership(membershipId)
      : null;
    if (!principal) return err(401, "unauthenticated", "Sign in to continue.");
    if (!principal.permissions.includes("groups:read")) {
      return err(403, "permission_denied", "Missing permission: groups:read");
    }
    return HttpResponse.json(groups);
  }),

  http.post("/api/v1/groups", async ({ request }) => {
    await delay(150);
    const membershipId = membershipFromToken(
      request.headers.get("Authorization"),
    );
    const principal = membershipId
      ? principalFromMembership(membershipId)
      : null;
    if (!principal) return err(401, "unauthenticated", "Sign in to continue.");
    if (!principal.permissions.includes("groups:manage")) {
      return err(403, "permission_denied", "Missing permission: groups:manage");
    }
    const body = (await request.json()) as {
      name?: string;
      description?: string | null;
    };
    if (!body.name?.trim()) {
      return err(422, "validation_error", "Group name is required.");
    }
    const group = {
      id: `group-${crypto.randomUUID().slice(0, 6)}`,
      name: body.name.trim(),
      description: body.description?.trim() || null,
      member_count: 0,
      member_ids: [] as string[],
    };
    groups.push(group);
    pushAudit({
      actor_type: "membership",
      actor_id: principal.membership_id,
      actor_label: principal.user.full_name,
      action: "create",
      object_type: "group",
      object_id: group.id,
      object_label: group.name,
      before: null,
      after: { name: group.name },
      tenant_id: principal.tenant_id,
    });
    return HttpResponse.json(group, { status: 201 });
  }),

  http.post("/api/v1/groups/:id/members", async ({ params, request }) => {
    await delay(150);
    const membershipId = membershipFromToken(
      request.headers.get("Authorization"),
    );
    const principal = membershipId
      ? principalFromMembership(membershipId)
      : null;
    if (!principal) return err(401, "unauthenticated", "Sign in to continue.");
    if (!principal.permissions.includes("groups:manage")) {
      return err(403, "permission_denied", "Missing permission: groups:manage");
    }
    const body = (await request.json()) as { membership_id?: string };
    const group = groups.find((g) => g.id === params.id);
    const member = members.find((m) => m.membership_id === body.membership_id);
    if (!group || !member) return err(404, "not_found", "Group or member not found.");
    if (!group.member_ids.includes(member.membership_id)) {
      group.member_ids.push(member.membership_id);
      group.member_count = group.member_ids.length;
      if (!member.group_names.includes(group.name)) {
        member.group_names = [...member.group_names, group.name];
      }
    }
    return HttpResponse.json(group);
  }),

  http.get("/api/v1/roles", ({ request }) => {
    const membershipId = membershipFromToken(
      request.headers.get("Authorization"),
    );
    const principal = membershipId
      ? principalFromMembership(membershipId)
      : null;
    if (!principal) return err(401, "unauthenticated", "Sign in to continue.");
    if (!principal.permissions.includes("roles:read")) {
      return err(403, "permission_denied", "Missing permission: roles:read");
    }
    return HttpResponse.json(roles);
  }),

  http.post("/api/v1/roles", async ({ request }) => {
    await delay(150);
    const membershipId = membershipFromToken(
      request.headers.get("Authorization"),
    );
    const principal = membershipId
      ? principalFromMembership(membershipId)
      : null;
    if (!principal) return err(401, "unauthenticated", "Sign in to continue.");
    if (!principal.permissions.includes("roles:manage")) {
      return err(403, "permission_denied", "Missing permission: roles:manage");
    }
    const body = (await request.json()) as {
      name?: string;
      description?: string | null;
      permission_keys?: string[];
    };
    if (!body.name?.trim()) {
      return err(422, "validation_error", "Role name is required.");
    }
    const role = {
      id: `role-${crypto.randomUUID().slice(0, 6)}`,
      name: body.name.trim(),
      description: body.description?.trim() || null,
      built_in: false,
      permission_keys: (body.permission_keys ?? []).filter(isPermissionKey),
      assignment_count: 0,
    };
    roles.push(role);
    return HttpResponse.json(role, { status: 201 });
  }),

  http.get("/api/v1/tenant", ({ request }) => {
    const membershipId = membershipFromToken(
      request.headers.get("Authorization"),
    );
    const principal = membershipId
      ? principalFromMembership(membershipId)
      : null;
    if (!principal) return err(401, "unauthenticated", "Sign in to continue.");
    const tenant = membershipTenants[principal.membership_id];
    return HttpResponse.json({
      id: principal.tenant_id,
      name: principal.tenant_name,
      slug: tenant?.tenant_slug ?? principal.tenant_id,
      status: "active",
    } satisfies TenantSummary);
  }),

  http.get("/api/v1/tenant/security", ({ request }) => {
    const membershipId = membershipFromToken(request.headers.get("Authorization"));
    const principal = membershipId ? principalFromMembership(membershipId) : null;
    if (!principal) return err(401, "unauthenticated", "Sign in to continue.");
    return HttpResponse.json({
      require_admin_mfa: requireAdminMfa[principal.tenant_id] ?? false,
    });
  }),

  http.patch("/api/v1/tenant/security", async ({ request }) => {
    const membershipId = membershipFromToken(request.headers.get("Authorization"));
    const principal = membershipId ? principalFromMembership(membershipId) : null;
    if (!principal) return err(401, "unauthenticated", "Sign in to continue.");
    if (!principal.permissions.includes("security:manage"))
      return err(403, "permission_denied", "You can't change security settings.");
    const body = (await request.json()) as { require_admin_mfa: boolean };
    requireAdminMfa[principal.tenant_id] = Boolean(body.require_admin_mfa);
    return HttpResponse.json({
      require_admin_mfa: requireAdminMfa[principal.tenant_id],
    });
  }),

  http.get("/api/v1/audit-log", ({ request }) => {
    const membershipId = membershipFromToken(
      request.headers.get("Authorization"),
    );
    const principal = membershipId
      ? principalFromMembership(membershipId)
      : null;
    if (!principal) return err(401, "unauthenticated", "Sign in to continue.");
    if (!principal.permissions.includes("audit:read")) {
      return err(403, "permission_denied", "Missing permission: audit:read");
    }
    // Cursor pagination: the cursor is the id of the last event of the
    // previous page (matches the backend's keyset contract).
    const PAGE_SIZE = 15;
    const all = auditEvents.filter((e) => e.tenant_id === principal.tenant_id);
    const cursor = new URL(request.url).searchParams.get("cursor");
    const start = cursor ? all.findIndex((e) => e.id === cursor) + 1 : 0;
    const items = all.slice(start, start + PAGE_SIZE);
    const lastItem = items[items.length - 1];
    const next_cursor =
      lastItem && start + PAGE_SIZE < all.length ? lastItem.id : null;
    return HttpResponse.json({ items, next_cursor });
  }),

  // The export, oldest first. The mock cannot build a workbook, so Excel gets the
  // same CSV under a .csv name.
  http.get("/api/v1/audit-log/export", ({ request }) => {
    const membershipId = membershipFromToken(
      request.headers.get("Authorization"),
    );
    const principal = membershipId
      ? principalFromMembership(membershipId)
      : null;
    if (!principal) return err(401, "unauthenticated", "Sign in to continue.");
    if (!principal.permissions.includes("audit:read")) {
      return err(403, "permission_denied", "Missing permission: audit:read");
    }
    const params = new URL(request.url).searchParams;
    const from = params.get("from");
    const to = params.get("to");
    const system = new Set(["session", "auth_attempt", "tenant", "tenant_branding"]);
    const quote = (value: unknown) => `"${String(value ?? "").replace(/"/g, '""')}"`;
    const rows = auditEvents
      .filter((e) => e.tenant_id === principal.tenant_id)
      .filter((e) => params.get("include_system") === "true" || !system.has(e.object_type))
      .filter((e) => (!from || e.occurred_at.slice(0, 10) >= from) && (!to || e.occurred_at.slice(0, 10) <= to))
      .reverse()
      .map((e) =>
        [
          e.occurred_at,
          e.actor_label,
          e.actor_type,
          e.actor_id,
          e.action,
          e.object_type,
          e.object_label,
          e.object_id,
          e.before && JSON.stringify(e.before),
          e.after && JSON.stringify(e.after),
        ]
          .map(quote)
          .join(","),
      );
    const header =
      "occurred_at,actor,actor_type,actor_id,action,object_type,object,object_id,before,after";
    return new HttpResponse([header, ...rows].join("\r\n"), {
      headers: {
        "Content-Type": "text/csv",
        "Content-Disposition": 'attachment; filename="audit-log.csv"',
      },
    });
  }),
];
