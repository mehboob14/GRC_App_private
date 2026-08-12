import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { StatusPill, statusFamilyFor } from "@/components/ui";
import { tenantApi } from "@/lib/api/endpoints";
import { useAuth } from "@/lib/auth/auth-context";

type PolicyRowProps = {
  title: string;
  description: string;
  status: ReactNode;
};

function PolicyRow({ title, description, status }: PolicyRowProps) {
  return (
    <div className="flex items-center gap-3 border-t border-border py-3">
      <div className="min-w-0 flex-1">
        <p className="text-body-lg font-semibold text-text-primary">{title}</p>
        <p className="text-body-sm text-text-subtle">{description}</p>
      </div>
      <div className="shrink-0">{status}</div>
    </div>
  );
}

/**
 * The security policy is the platform's, not the tenant's: nothing here is a
 * workspace toggle (week1-review-decisions.md #19/#20). Rendered read-only
 * from fixed platform facts plus GET /api/v1/tenant for the workspace name.
 */
export function SecurityPage() {
  const { principal } = useAuth();

  const tenantQuery = useQuery({
    queryKey: ["tenant", principal?.tenant_id],
    queryFn: () => tenantApi.get(),
  });

  const scopeLine = tenantQuery.isLoading
    ? "Loading workspace details…"
    : tenantQuery.data
      ? `Enforced by the platform for ${tenantQuery.data.name} — these protections are not configurable per workspace.`
      : "Enforced by the platform for every workspace — these protections are not configurable per workspace.";

  const enforced = (
    <StatusPill
      status={statusFamilyFor("Enforced") ?? "unknown"}
      label="Enforced"
    />
  );

  return (
    <div className="rounded-lg border border-border bg-surface-primary px-5 py-4">
      <p className="type-overline">Platform policy</p>
      <h2 className="mt-1 font-display text-heading-sm text-text-primary">
        Security policy
      </h2>
      <p className="mt-1 text-body-sm text-text-subtle">{scopeLine}</p>
      <div className="mt-3">
        <PolicyRow
          title="Multi-factor authentication"
          description="Required for Admin-role memberships and all platform administrators — always on, never a toggle"
          status={enforced}
        />
        <PolicyRow
          title="Session expiry"
          description="Sessions end 12 hours after sign-in; MFA challenges expire after 5 minutes"
          status={
            <span className="tabular text-body-md font-semibold text-text-primary">
              12 hours
            </span>
          }
        />
        <PolicyRow
          title="Tenant isolation"
          description="Workspace data is separated at the database with PostgreSQL row-level security"
          status={enforced}
        />
        <PolicyRow
          title="Audit trail"
          description="State changes are recorded append-only — audit events are never updated or deleted"
          status={enforced}
        />
      </div>
      <p className="mt-3 text-caption text-text-subtle">
        Workspace-configurable controls (SSO enforcement, IP allowlists, SIEM
        export) arrive in a later phase.
      </p>
    </div>
  );
}
