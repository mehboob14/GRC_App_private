import { useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { authApi } from "@/lib/api/endpoints";
import { useAuth } from "@/lib/auth/auth-context";
import { resumePendingAuth } from "@/lib/auth/resume-auth";
import { onEmailVerified } from "@/lib/auth/verify-signal";
import type { LoginResponse } from "@/lib/api/types";
import { authSuccessDelay } from "@/features/iam/auth-motion";
import { AuthSubmitButton } from "@/features/iam/components/auth-submit-button";
import { AuthAlert, FailureAlert } from "@/features/iam/auth-kit/auth-alert";
import { SentTo, WebmailLinks } from "@/features/iam/auth-kit/auth-bits";
import { linkClass, useCooldown } from "@/features/iam/auth-kit/helpers";
import { describeAuthFailure } from "@/features/iam/auth-kit/auth-errors";

const RESEND_COOLDOWN_S = 30;

/**
 * The verify first step after sign up (or a sign in before verifying). It says
 * where the link went, opens that inbox in one click, and when the credentials
 * are on hand it continues by itself: the verify tab signals this one, which
 * signs straight in. "I've verified" covers the other device case.
 */
export function CheckEmailPanel({
  email,
  password,
  onChangeEmail,
}: {
  email: string;
  password?: string;
  onChangeEmail?: () => void;
}) {
  const { applyLogin } = useAuth();
  const navigate = useNavigate();
  const cooldown = useCooldown();
  const [notYet, setNotYet] = useState(false);
  const [done, setDone] = useState(false);
  const [shakeKey, setShakeKey] = useState(0);

  const resendMutation = useMutation({
    mutationFn: () => authApi.resendVerification(email),
    onSuccess: () => cooldown.start(RESEND_COOLDOWN_S),
  });

  const continueMutation = useMutation({
    mutationFn: () => authApi.login({ email, password: password ?? "" }),
    onMutate: () => setNotYet(false),
    onSuccess: (response: LoginResponse) => {
      if (response.status === "authenticated") {
        const delay = authSuccessDelay();
        const enter = () => {
          applyLogin(response);
          navigate("/quick-start", { replace: true });
        };
        if (!delay) {
          enter();
          return;
        }
        setDone(true);
        window.setTimeout(enter, delay);
        return;
      }
      if (response.status === "email_verification_required") {
        // The click beat the confirmation: still unverified.
        setNotYet(true);
        setShakeKey((k) => k + 1);
        return;
      }
      // MFA (enroll or challenge) or a workspace choice: hand to the surface that finishes it.
      resumePendingAuth(response, navigate);
    },
    onError: () => setShakeKey((k) => k + 1),
  });

  const { mutate: continueLogin } = continueMutation;

  useEffect(() => {
    if (!password) return;
    return onEmailVerified(() => continueLogin());
  }, [password, continueLogin]);

  const resendFailure = resendMutation.isError
    ? describeAuthFailure(resendMutation.error, "verify")
    : null;
  const continueFailure = continueMutation.isError
    ? describeAuthFailure(continueMutation.error, "signin")
    : null;

  return (
    <div className="flex flex-col gap-4">
      <SentTo email={email} onChange={onChangeEmail} />

      {password && !notYet && !continueFailure ? (
        <p
          role="status"
          className="flex items-center justify-center gap-2.5 text-body-sm text-text-secondary"
        >
          <span className="auth-wait-dot" aria-hidden />
          {continueMutation.isPending || done
            ? "Signing you in"
            : "This page continues once you click the link"}
        </p>
      ) : null}

      {notYet ? (
        <AuthAlert tone="warning" icon="mail" title="Not verified yet">
          Open the link in the email first, then continue.
        </AuthAlert>
      ) : null}
      {continueFailure ? (
        <FailureAlert
          failure={continueFailure}
          onRetry={() => continueLogin()}
        />
      ) : null}
      {resendFailure ? (
        <FailureAlert
          failure={resendFailure}
          onRetry={() => resendMutation.mutate()}
        />
      ) : null}
      {resendMutation.isSuccess && cooldown.left > 0 ? (
        <AuthAlert tone="success" title="A new link is on its way" />
      ) : null}

      <WebmailLinks email={email} />

      {password ? (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (!continueMutation.isPending && !done) continueLogin();
          }}
        >
          <AuthSubmitButton
            label="I've verified, continue"
            steps={["Checking your email", "Signing you in"]}
            successLabel="Email verified"
            phase={
              done ? "success" : continueMutation.isPending ? "loading" : "idle"
            }
            shakeKey={shakeKey}
          />
        </form>
      ) : null}

      <p className="text-center text-body-sm text-text-subtle">
        No email? Check spam, or{" "}
        {cooldown.left > 0 ? (
          <span className="font-semibold tabular-nums text-text-secondary">
            resend in {cooldown.left}s
          </span>
        ) : (
          <button
            type="button"
            className={linkClass}
            disabled={resendMutation.isPending}
            onClick={() => resendMutation.mutate()}
          >
            {resendMutation.isPending ? "sending" : "send it again"}
          </button>
        )}
      </p>
    </div>
  );
}
