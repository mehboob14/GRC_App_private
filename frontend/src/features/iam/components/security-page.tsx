import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ErrorState,
  Skeleton,
  Switch,
} from "@/components/ui";
import { iamApi } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-context";
import { cn } from "@/lib/cn";

type PolicyRowProps = {
  title: string;
  description: string;
  checked: boolean;
  disabled?: boolean;
  onCheckedChange?: (checked: boolean) => void;
};

function PolicyRow({
  title,
  description,
  checked,
  disabled,
  onCheckedChange,
}: PolicyRowProps) {
  return (
    <div className="flex items-center gap-3 border-t border-border py-[11px]">
      <div className="min-w-0 flex-1">
        <p className="text-[14px] font-semibold leading-5 text-text">{title}</p>
        <p className="pt-px text-[12px] leading-4 text-text-faint">
          {description}
        </p>
      </div>
      <Switch
        checked={checked}
        disabled={disabled}
        onCheckedChange={onCheckedChange}
        aria-label={title}
        className={cn(disabled && "opacity-70")}
      />
    </div>
  );
}

/** Figma 43:5093 — Security policy card (white mode). */
export function SecurityPage() {
  const { principal } = useAuth();
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["security-policy", principal?.tenant_id],
    queryFn: () => iamApi.getSecurityPolicy(),
  });

  const mutation = useMutation({
    mutationFn: (require_mfa: boolean) =>
      iamApi.updateSecurityPolicy({ require_mfa }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["security-policy"] });
    },
  });

  const isAdmin = principal?.role_names.includes("Admin");

  if (query.isLoading) {
    return <Skeleton className="h-72 w-full rounded-xl" />;
  }

  if (query.isError) {
    return (
      <ErrorState
        title="Couldn’t load security policy"
        description={
          query.error instanceof ApiError ? query.error.message : "Try again."
        }
        onRetry={() => void query.refetch()}
      />
    );
  }

  const policy = query.data!;

  return (
    <div className="rounded-xl border border-border bg-bg-elevated px-5 py-[18px] shadow-sm">
      <h2 className="font-display text-[16px] font-semibold leading-5 tracking-[-0.08px] text-text">
        Security policy
      </h2>
      <div className="mt-[13px]">
        <PolicyRow
          title="Enforce SSO"
          description="Require Okta SSO for all workspace members"
          checked={false}
          disabled
        />
        <PolicyRow
          title="Require MFA"
          description="Block sign-in without multi-factor"
          checked={policy.require_mfa}
          disabled={!isAdmin || mutation.isPending}
          onCheckedChange={(checked) => mutation.mutate(checked)}
        />
        <PolicyRow
          title="Session timeout"
          description={`Sign out after ${policy.session_timeout_hours} hours of inactivity`}
          checked
          disabled
        />
        <PolicyRow
          title="IP allowlist"
          description="Restrict access to corporate IP ranges"
          checked={false}
          disabled
        />
        <PolicyRow
          title="Audit log export"
          description="Stream audit events to SIEM"
          checked={false}
          disabled
        />
      </div>
      {mutation.isError ? (
        <p className="mt-2 text-[12px] text-fail-fg" role="alert">
          {mutation.error instanceof ApiError
            ? mutation.error.message
            : "Update failed."}
        </p>
      ) : null}
      <p className="mt-3 text-[11px] text-text-faint">
        Enforce SSO, IP allowlist, and SIEM export are Phase 3 — shown as in
        Figma, disabled until then. Require MFA is live for Admins.
      </p>
    </div>
  );
}
