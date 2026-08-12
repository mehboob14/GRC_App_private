import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { Badge } from "@/components/ui";
import { tenantApi } from "@/lib/api/endpoints";
import { useAuth } from "@/lib/auth/auth-context";

type PolicyRowProps = {
  title: string;
  description: string;
  status: ReactNode;
};

function PolicyRow({ title, description, status }: PolicyRowProps) {
  return (
    <div className="flex items-center gap-3 border-t border-border py-[11px]">
      <div className="min-w-0 flex-1">
        <p className="text-body-lg font-semibold text-text">{title}</p>
        <p className="pt-px text-body-sm text-text-faint">{description}</p>
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

  const enforced = <Badge variant="statusPass">Enforced</Badge>;

  return (
    <div className="rounded-xl border border-border bg-bg-elevated px-5 py-[18px] shadow-sm">
      <p className="type-overline">Platform policy</p>
      <h2 className="mt-1 font-display text-title-md text-text">
        Security policy
      </h2>
      <p className="mt-1 text-body-sm text-text-faint">{scopeLine}</p>
      <div className="mt-[13px]">
        <PolicyRow
          title="Multi-factor authentication"
          description="Required for Admin-role memberships and all platform administrators — always on, never a toggle"
          status={enforced}
        />
        <PolicyRow
          title="Session expiry"
          description="Sessions end 12 hours after sign-in; MFA challenges expire after 5 minutes"
          status={
            <span className="text-body-md font-semibold text-text">
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
      <p className="mt-3 text-caption text-text-faint">
        Workspace-configurable controls (SSO enforcement, IP allowlists, SIEM
        export) arrive in a later phase.
      </p>
    </div>
  );
}
