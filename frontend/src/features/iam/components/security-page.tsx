import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { Switch, useToast } from "@/components/ui";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { tenantApi } from "@/lib/api/endpoints";
import { useAuth } from "@/lib/auth/auth-context";
import { PasswordPolicyCard } from "@/features/iam/components/password-policy-card";

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
  const { toast } = useToast();
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
    // The switch snaps back on failure; without this it would do so silently.
    onError: (error: unknown) =>
      toast({ title: errorToast(error, "security setting"), tone: "danger" }),
  });

  const scopeLine = tenantQuery.data
    ? `Access controls for ${tenantQuery.data.name}.`
    : "Access controls for this workspace.";

  const requireMfa = securityQuery.data?.require_admin_mfa ?? false;

  return (
    <div className="space-y-5">
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
                    !canManage ||
                    securityQuery.isLoading ||
                    mfaMutation.isPending
                  }
                  aria-label="Require MFA for admins"
                />
              )
            }
          />
        </div>
        {/* The row's badge only says it failed; this says why. */}
        {securityQuery.isError ? (
          <p className="mt-2 text-body-sm text-status-danger-text">
            {describeError(securityQuery.error, "security setting").message}
          </p>
        ) : null}
        {!canManage ? (
          <p className="mt-3 text-caption text-text-subtle">
            Only workspace admins can change these settings.
          </p>
        ) : null}
      </div>
    </div>
  );
}

/** Settings → Security → Password policy. Its own tab: nobody looks for
 *  password rules under "MFA". */
export function PasswordPolicyPage() {
  return <PasswordPolicyCard />;
}
