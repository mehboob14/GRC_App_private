import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { AuthSplitLayout } from "@/features/iam/components/auth-split-layout";
import { Button, ErrorBanner, Icon, Skeleton, TextField } from "@/components/ui";
import { authApi } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-context";
import { useAlertFocus } from "@/features/iam/hooks/use-alert-focus";

function messageFrom(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback;
}

export function MfaEnrollPage() {
  const [params] = useSearchParams();
  const challengeToken = params.get("challenge") ?? "";
  const navigate = useNavigate();
  const { applyLogin } = useAuth();
  const [code, setCode] = useState("");

  const enrollQuery = useQuery({
    queryKey: ["mfa-enroll", challengeToken],
    queryFn: () => authApi.startMfaEnroll(challengeToken),
    enabled: challengeToken.length > 0,
    // The challenge is single-use and short-lived: never refetch or retry it.
    staleTime: Infinity,
    retry: false,
  });

  const confirmMutation = useMutation({
    mutationFn: () =>
      authApi.confirmMfaEnroll({ challenge_token: challengeToken, code }),
    onSuccess: (response) => {
      if (response.status === "authenticated") {
        applyLogin(response);
        navigate("/quick-start", { replace: true });
      }
    },
  });

  const enrollAlertRef = useAlertFocus(enrollQuery.isError);
  const confirmAlertRef = useAlertFocus(confirmMutation.isError);

  if (!challengeToken) {
    return (
      <AuthSplitLayout
        title="MFA enrollment"
        subtitle="This enrollment link is missing its challenge. Sign in again to restart."
      >
        <Link
          className="font-semibold text-text-link"
          to="/sign-in"
        >
          Back to sign in
        </Link>
      </AuthSplitLayout>
    );
  }

  return (
    <AuthSplitLayout
      title="Set up authenticator"
      subtitle="Admins must enroll MFA before accessing the workspace."
    >
      {enrollQuery.isError ? (
        <ErrorBanner
          ref={enrollAlertRef}
          className="mb-4"
          title="Couldn't start MFA enrollment"
        >
          {messageFrom(
            enrollQuery.error,
            "The challenge may have expired — sign in again to get a fresh one.",
          )}{" "}
          <Link className="font-semibold text-text-link" to="/sign-in">
            Back to sign in
          </Link>
        </ErrorBanner>
      ) : null}

      <ol className="mb-5 list-decimal space-y-2 pl-4 text-body-md text-text-secondary">
        <li>Open your authenticator app.</li>
        <li>Add a new account with the secret below.</li>
        <li>Enter the 6-digit code to confirm.</li>
      </ol>

      <div className="mb-4 rounded-md border border-border bg-surface-sunken px-3 py-3">
        <p className="type-overline text-text-subtle">Manual secret</p>
        {enrollQuery.data ? (
          <p className="mt-1 font-mono text-body-md text-text-primary">
            {enrollQuery.data.secret}
          </p>
        ) : (
          // Bone matches the secret's line height — no shift when it lands.
          <Skeleton className="mt-1 h-5 w-56 max-w-full" />
        )}
      </div>

      {confirmMutation.isError ? (
        <ErrorBanner
          ref={confirmAlertRef}
          className="mb-4"
          title="Couldn't confirm enrollment"
        >
          {messageFrom(
            confirmMutation.error,
            "That code didn't match — check your authenticator app and try again.",
          )}
        </ErrorBanner>
      ) : null}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (code.length === 6 && enrollQuery.data) confirmMutation.mutate();
        }}
        noValidate
      >
        <TextField
          label="Authenticator code"
          size="lg"
          inputMode="numeric"
          autoComplete="one-time-code"
          placeholder="000000"
          value={code}
          onChange={(e) =>
            setCode(e.target.value.replace(/\D/g, "").slice(0, 6))
          }
        />
        <Button
          type="submit"
          className="mt-4 w-full"
          size="lg"
          loading={confirmMutation.isPending}
          disabled={code.length !== 6 || !enrollQuery.data}
        >
          Confirm and continue
          <Icon name="arrowr" className="size-4" />
        </Button>
      </form>
    </AuthSplitLayout>
  );
}
