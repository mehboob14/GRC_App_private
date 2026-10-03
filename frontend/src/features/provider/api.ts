import { apiFetch } from "@/lib/api/client";
import { fetchImageDataUrl } from "@/lib/api/image";
import type {
  AdminInvite,
  AdminInviteRequest,
  Branding,
  BrandingPut,
  Provisioning,
  ProviderChallenge,
  ProviderEnrollConfirm,
  ProviderEnrollStart,
  ProviderSession,
  Tenant,
  TenantPage,
  TenantQuery,
  TenantRegistration,
  TenantUpdate,
} from "./types";

const json = (body: unknown) => JSON.stringify(body);

/**
 * Sign in on the platform plane. These calls carry no session: the challenge token
 * from the password step is the partial credential for the steps after it.
 */
export const providerAuthApi = {
  login: (email: string, password: string) =>
    apiFetch<ProviderChallenge>("/provider/login", {
      method: "POST",
      body: json({ email, password }),
    }),
  verify: (body: {
    challenge_token: string;
    code?: string;
    recovery_code?: string;
  }) =>
    apiFetch<ProviderSession>("/provider/mfa/verify", {
      method: "POST",
      body: json(body),
    }),
  startEnrollment: (challengeToken: string) =>
    apiFetch<ProviderEnrollStart>("/provider/mfa/enroll", {
      method: "POST",
      body: json({ challenge_token: challengeToken }),
    }),
  confirmEnrollment: (challengeToken: string, code: string) =>
    apiFetch<ProviderEnrollConfirm>("/provider/mfa/confirm", {
      method: "POST",
      body: json({ challenge_token: challengeToken, code }),
    }),
};

function listPath(query: TenantQuery): string {
  const params = new URLSearchParams();
  params.set("limit", String(query.limit ?? 25));
  if (query.search) params.set("search", query.search);
  if (query.status) params.set("status", query.status);
  if (query.cursor) params.set("cursor", query.cursor);
  return `/provider/tenants?${params.toString()}`;
}

const tenantPath = (id: string) => `/provider/tenants/${id}`;

export const tenantsApi = {
  list: (query: TenantQuery) => apiFetch<TenantPage>(listPath(query)),
  get: (id: string) => apiFetch<Tenant>(tenantPath(id)),
  /** A repeat with the same key and body returns the first tenant instead of a second. */
  register: (body: TenantRegistration, idempotencyKey: string) =>
    apiFetch<Tenant>("/provider/tenants", {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: json(body),
    }),
  update: (id: string, body: TenantUpdate) =>
    apiFetch<Tenant>(tenantPath(id), { method: "PATCH", body: json(body) }),

  branding: (id: string) => apiFetch<Branding>(`${tenantPath(id)}/branding`),
  saveBranding: (id: string, body: BrandingPut) =>
    apiFetch<Branding>(`${tenantPath(id)}/branding`, {
      method: "PUT",
      body: json(body),
    }),
  uploadLogo: (id: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return apiFetch<Branding>(`${tenantPath(id)}/branding/logo`, {
      method: "POST",
      body: form,
    });
  },
  removeLogo: (id: string) =>
    apiFetch<Branding>(`${tenantPath(id)}/branding/logo`, { method: "DELETE" }),
  logo: (id: string) => fetchImageDataUrl(`${tenantPath(id)}/branding/logo`),

  provisioning: (id: string) =>
    apiFetch<Provisioning>(`${tenantPath(id)}/provisioning`),
  runProvisioning: (id: string) =>
    apiFetch<Provisioning>(`${tenantPath(id)}/provision`, { method: "POST" }),
  inviteAdmin: (id: string, body: AdminInviteRequest) =>
    apiFetch<AdminInvite>(`${tenantPath(id)}/admin-invite`, {
      method: "POST",
      body: json(body),
    }),
};
