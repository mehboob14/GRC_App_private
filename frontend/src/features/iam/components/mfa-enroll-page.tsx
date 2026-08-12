import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { AuthSplitLayout } from "@/features/iam/components/auth-split-layout";
import { Button, Icon, TextField } from "@/components/ui";
import { authApi } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-context";

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

  if (!challengeToken) {
    return (
      <AuthSplitLayout
        title="MFA enrollment"
        subtitle="This enrollment link is missing its challenge. Sign in again to restart."
      >
        <Link className="text-accent" to="/sign-in">
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
      <ol className="mb-5 list-decimal space-y-2 pl-4 text-body-md text-text-muted">
        <li>Open your authenticator app.</li>
        <li>Add a new account with the secret below.</li>
        <li>Enter the 6-digit code to confirm.</li>
      </ol>

      <div className="mb-4 rounded-lg border border-border bg-bg-sunken px-3 py-3">
        <p className="type-overline text-text-faint">Manual secret</p>
        {enrollQuery.isError ? (
          <p className="mt-1 text-body-sm text-fail-fg" role="alert">
            {messageFrom(
              enrollQuery.error,
              "Could not start MFA enrollment. Sign in again to get a fresh challenge.",
            )}
          </p>
        ) : (
          <p className="mt-1 font-mono text-body-md text-text">
            {enrollQuery.data?.secret ?? "Loading…"}
          </p>
        )}
      </div>

      <TextField
        label="Authenticator code"
        inputMode="numeric"
        autoComplete="one-time-code"
        placeholder="000000"
        value={code}
        onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
      />
      {confirmMutation.isError ? (
        <p className="mt-2 text-body-sm text-fail-fg" role="alert">
          {messageFrom(
            confirmMutation.error,
            "Enter the 6-digit code from your authenticator.",
          )}
        </p>
      ) : null}
      <Button
        className="mt-4 w-full"
        size="lg"
        loading={confirmMutation.isPending}
        disabled={code.length !== 6 || !enrollQuery.data}
        onClick={() => confirmMutation.mutate()}
      >
        Confirm and continue
        <Icon name="arrowr" className="size-4" />
      </Button>
    </AuthSplitLayout>
  );
}
