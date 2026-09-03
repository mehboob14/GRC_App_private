import { useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { Button, ErrorBanner, Icon, useToast } from "@/components/ui";
import { authApi } from "@/lib/api/endpoints";
import { describeAuthError } from "@/lib/api/describe-error";
import { useAuth } from "@/lib/auth/auth-context";
import { resumePendingAuth } from "@/lib/auth/resume-auth";
import { onEmailVerified } from "@/lib/auth/verify-signal";
import { useAlertFocus } from "@/features/iam/hooks/use-alert-focus";
import type { LoginResponse } from "@/lib/api/types";

/**
 * Shared body for the verify-first flow. Shows which inbox to check and a resend.
 * When the credentials are on hand (sign-up, sign-in), it continues on its own:
 * it listens for the verify-email tab's signal (same browser) and, on it, signs
 * the user straight in — with an "I've verified" button as the cross-device fallback.
 */
export function CheckEmailPanel({
  email,
  password,
}: {
  email: string;
  password?: string;
}) {
  const { toast } = useToast();
  const { applyLogin } = useAuth();
  const navigate = useNavigate();
  const [notYet, setNotYet] = useState(false);

  const resendMutation = useMutation({
    mutationFn: () => authApi.resendVerification(email),
    onSuccess: () => toast({ title: "Sent. Check your inbox", tone: "success" }),
  });

  const continueMutation = useMutation({
    mutationFn: () => authApi.login({ email, password: password ?? "" }),
    onSuccess: (response: LoginResponse) => {
      if (response.status === "authenticated") {
        applyLogin(response);
        navigate("/quick-start", { replace: true });
        return;
      }
      if (response.status === "email_verification_required") {
        // The click beat the confirmation — still unverified.
        setNotYet(true);
        return;
      }
      // MFA (enroll or challenge) or workspace choice — hand to the surface
      // that finishes it.
      resumePendingAuth(response, navigate);
    },
  });

  const { mutate: continueLogin } = continueMutation;

  useEffect(() => {
    if (!password) return;
    return onEmailVerified(() => {
      setNotYet(false);
      continueLogin();
    });
  }, [password, continueLogin]);

  const alertRef = useAlertFocus(resendMutation.isError);

  return (
    <div className="flex flex-col gap-4">
      <p className="text-body-lg text-text-secondary">
        We sent a verification link to{" "}
        <span className="font-semibold text-text-primary">{email}</span>. Click
        it to finish setting up your workspace.
        {password
          ? " This page continues on its own once you do."
          : null}
      </p>

      {password && continueMutation.isPending ? (
        <div
          className="flex items-center gap-2 text-body-md text-text-secondary"
          role="status"
        >
          <Icon
            name="spinner"
            className="size-4 animate-spin text-action-accent"
          />
          Signing you in…
        </div>
      ) : null}

      {notYet ? (
        <p className="text-body-sm text-status-warning-text">
          Not verified yet. Open the link in your email, then try again.
        </p>
      ) : null}

      {resendMutation.isError ? (
        <ErrorBanner
          ref={alertRef}
          title={describeAuthError(resendMutation.error).message}
        />
      ) : null}

      <div className="flex flex-wrap gap-2">
        {password ? (
          <Button
            type="button"
            size="lg"
            loading={continueMutation.isPending}
            onClick={() => continueLogin()}
          >
            I've verified, continue
            <Icon name="arrowr" className="size-4" />
          </Button>
        ) : null}
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
