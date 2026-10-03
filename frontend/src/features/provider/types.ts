/**
 * What the platform API returns for the provider plane (backend `modules/tenancy`
 * and the first-admin route in `modules/iam`). Hand-written, like the other
 * features, so a field renamed on the server fails the type check here.
 */

export const TENANT_STATUSES = [
  "provisioning",
  "active",
  "suspended",
  "terminated",
] as const;
export type TenantStatus = (typeof TENANT_STATUSES)[number];

export type Tenant = {
  id: string;
  legal_name: string;
  trading_name: string | null;
  slug: string;
  industry: string | null;
  registration_number: string | null;
  address_line1: string | null;
  address_line2: string | null;
  city: string | null;
  state_region: string | null;
  postal_code: string | null;
  country: string | null;
  primary_contact_name: string | null;
  primary_contact_email: string | null;
  primary_contact_phone: string | null;
  plan: string;
  status: TenantStatus;
  created_by: string | null;
  onboarded_at: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type TenantPage = {
  items: Tenant[];
  /** Opaque. Pass it back as the cursor for the next page; null at the end. */
  next_cursor: string | null;
};

/** The profile fields a tenant can be registered or edited with, all optional. */
export type TenantProfileFields = {
  trading_name?: string | null;
  industry?: string | null;
  registration_number?: string | null;
  address_line1?: string | null;
  address_line2?: string | null;
  city?: string | null;
  state_region?: string | null;
  postal_code?: string | null;
  country?: string | null;
  primary_contact_name?: string | null;
  primary_contact_email?: string | null;
  primary_contact_phone?: string | null;
  onboarded_at?: string | null;
  notes?: string | null;
};

export type TenantRegistration = TenantProfileFields & {
  legal_name: string;
  slug: string;
  plan: string;
};

/** A patch: only what is sent changes. The slug and the status are not editable. */
export type TenantUpdate = TenantProfileFields & {
  legal_name?: string;
  plan?: string;
};

export type TenantQuery = {
  search?: string;
  status?: TenantStatus;
  cursor?: string | null;
  limit?: number;
};

export type Branding = {
  tenant_id: string;
  /** The stored key of the uploaded logo. Never shown; null means no logo. */
  logo_ref: string | null;
  primary_color: string | null;
  secondary_color: string | null;
  custom_domain: string | null;
  email_from_name: string | null;
  email_from_address: string | null;
  document_footer: string | null;
  created_at: string;
  updated_at: string;
};

/**
 * A full replace: a field left out clears its column. The mail credential is not
 * part of it, because the API never returns it and keeps it when it is omitted.
 */
export type BrandingPut = {
  logo_ref: string | null;
  primary_color: string | null;
  secondary_color: string | null;
  custom_domain: string | null;
  email_from_name: string | null;
  email_from_address: string | null;
  document_footer: string | null;
};

export type ProvisioningStepName =
  | "create_tenant"
  | "seed_content"
  | "invite_admin"
  | "verify";

export type ProvisioningStep = {
  step: ProvisioningStepName;
  status: "pending" | "done";
  completed_at: string | null;
};

export type Provisioning = {
  tenant_id: string;
  tenant_status: TenantStatus;
  steps: ProvisioningStep[];
  remaining: ProvisioningStepName[];
};

export type AdminInviteRequest = { email: string; full_name: string };

export type AdminInvite = {
  member: { membership_id: string; email: string; full_name: string };
  /** One time. Shown once for the operator to hand over when mail did not go out. */
  invite_token: string;
  accept_url: string;
  email_sent: boolean;
};

// Sign in. A correct password buys a challenge, never a session.

export type ProviderChallenge = {
  next_step: "mfa_verify" | "mfa_enroll";
  challenge_token: string;
  expires_at: string;
};

export type ProviderSession = {
  token: string;
  token_type: "bearer";
  expires_at: string;
};

export type ProviderEnrollStart = { secret: string; otpauth_uri: string };

export type ProviderEnrollConfirm = ProviderSession & {
  /** Plaintext leaves the server exactly once, here. */
  recovery_codes: string[];
};
