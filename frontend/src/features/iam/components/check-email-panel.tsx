import { useMutation } from "@tanstack/react-query";
import { Button, ErrorBanner, useToast } from "@/components/ui";
import { authApi } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import { useAlertFocus } from "@/features/iam/hooks/use-alert-focus";

/**
 * Shared body for the verify-first flow. The page owns the AuthSplitLayout
 * heading; this renders the instruction plus a resend affordance. Used by
 * sign-up, sign-in (unverified) and verify-email so the copy can't drift.
 */
export function CheckEmailPanel({ email }: { email: string }) {
  const { toast } = useToast();

  // Resend always 202s (no account disclosure), so success is unconditional —
  // a transient toast, per DS §7.2 for a user-triggered result.
  const resendMutation = useMutation({
    mutationFn: () => authApi.resendVerification(email),
    onSuccess: () =>
      toast({ title: "Sent — check your inbox", tone: "success" }),
  });

  const alertRef = useAlertFocus(resendMutation.isError);

  return (
    <div className="flex flex-col gap-4">
      <p className="text-body-lg text-text-secondary">
        We sent a verification link to{" "}
        <span className="font-semibold text-text-primary">{email}</span>. Click
        it to finish setting up your workspace.
      </p>

      {resendMutation.isError ? (
        <ErrorBanner ref={alertRef} title="Couldn't resend the email">
          {resendMutation.error instanceof ApiError
            ? resendMutation.error.message
            : "The request didn't reach the server — check your connection and try again."}
        </ErrorBanner>
      ) : null}

      <div>
        <Button
          type="button"
          variant="secondary"
          size="lg"
          loading={resendMutation.isPending}
          onClick={() => resendMutation.mutate()}
        >
          Resend email
        </Button>
      </div>
    </div>
  );
}
