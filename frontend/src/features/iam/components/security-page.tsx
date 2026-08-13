import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { StatusPill, Switch, statusFamilyFor } from "@/components/ui";
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
 * Admin MFA is a per-tenant toggle (off by default); the other protections are
 * platform-enforced facts, shown read-only. Only a member holding security:manage
 * can flip the toggle — everyone else sees its current state.
 */
export function SecurityPage() {
  const { principal } = useAuth();
  const queryClient = useQueryClient();
  const canManage = principal?.permissions.includes("security:manage") ?? false;

  const tenantQuery = useQuery({
    queryKey: ["tenant", principal?.tenant_id],
    queryFn: () => tenantApi.get(),
  });
  const securityQuery = useQuery({
    queryKey: ["security", principal?.tenant_id],
    queryFn: () => tenantApi.getSecurity(),
  });
  const mfaMutation = useMutation({
    mutationFn: (value: boolean) => tenantApi.setRequireAdminMfa(value),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: ["security", principal?.tenant_id],
        exact: true,
      }),
  });

  const scopeLine = tenantQuery.data
    ? `Access controls for ${tenantQuery.data.name}.`
    : "Access controls for this workspace.";

  const enforced = (
    <StatusPill
      status={statusFamilyFor("Enforced") ?? "unknown"}
      label="Enforced"
    />
  );

  const requireMfa = securityQuery.data?.require_admin_mfa ?? false;

  return (
    <div className="rounded-lg border border-border bg-surface-primary px-5 py-4">
      <p className="type-overline">Security</p>
      <h2 className="mt-1 font-display text-heading-sm text-text-primary">
        Security policy
      </h2>
      <p className="mt-1 text-body-sm text-text-subtle">{scopeLine}</p>
      <div className="mt-3">
        <PolicyRow
          title="Require MFA for admins"
          description="When on, Admin-role members must set up an authenticator app before they can sign in. Off by default."
          status={
            securityQuery.isError ? (
              <span className="text-body-sm text-status-danger-text">
                Couldn't load
              </span>
            ) : (
              <Switch
                checked={requireMfa}
                onCheckedChange={(value) => mfaMutation.mutate(value)}
                disabled={
                  !canManage || securityQuery.isLoading || mfaMutation.isPending
                }
                aria-label="Require MFA for admins"
              />
            )
          }
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
      {!canManage ? (
        <p className="mt-3 text-caption text-text-subtle">
          Only workspace admins can change these settings.
        </p>
      ) : null}
    </div>
  );
}
