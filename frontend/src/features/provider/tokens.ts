import type { StatusFamily } from "@/components/ui";
import type { ProvisioningStepName, Tenant, TenantStatus } from "./types";

/** The same words and colours as everywhere else: progress while it is being set up. */
export const STATUS_META: Record<
  TenantStatus,
  { label: string; family: StatusFamily }
> = {
  provisioning: { label: "Provisioning", family: "progress" },
  active: { label: "Active", family: "success" },
  suspended: { label: "Suspended", family: "warning" },
  terminated: { label: "Terminated", family: "neutral" },
};

/** What the four provisioning steps are, and what each is waiting for, in the operator's words. */
export const STEP_META: Record<
  ProvisioningStepName,
  { label: string; done: string; waiting: string }
> = {
  create_tenant: {
    label: "Create workspace",
    done: "The workspace exists.",
    waiting: "The workspace is being created.",
  },
  seed_content: {
    label: "Prepare content",
    done: "Frameworks and control templates are ready.",
    waiting: "Runs when you run provisioning.",
  },
  invite_admin: {
    label: "Invite first admin",
    done: "An admin has been invited.",
    waiting: "Waiting for the first admin to be invited.",
  },
  verify: {
    label: "Verify",
    done: "An admin has accepted and can sign in.",
    waiting: "Waiting for an admin to accept the invite.",
  },
};

/** The name a workspace goes by: its trading name where it has one. */
export function tenantName(tenant: Pick<Tenant, "trading_name" | "legal_name">) {
  return tenant.trading_name || tenant.legal_name;
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { dateStyle: "medium" });
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

/** A workspace address from a company name: lowercase, hyphens, at most 63 characters. */
export function slugify(name: string): string {
  return name
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 63)
    .replace(/-+$/g, "");
}

/** The shape the API accepts for a workspace address (a DNS label). */
export const SLUG_PATTERN = /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/;

/** Blank form text means "not set": the API stores null, never an empty string. */
export function blankToNull(value: string | undefined): string | null {
  const trimmed = (value ?? "").trim();
  return trimmed === "" ? null : trimmed;
}
