import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { QRCodeSVG } from "qrcode.react";
import { AuthSplitLayout } from "@/features/iam/components/auth-split-layout";
import { RecoveryCodesPanel } from "@/features/iam/components/recovery-codes-panel";
import { Button, ErrorBanner, Icon, Skeleton, TextField } from "@/components/ui";
import { authApi } from "@/lib/api/endpoints";
import { describeAuthError } from "@/lib/api/describe-error";
import { useAuth } from "@/lib/auth/auth-context";
import { useAlertFocus } from "@/features/iam/hooks/use-alert-focus";
import type { LoginSuccess } from "@/lib/api/types";

export function MfaEnrollPage() {
  const [params] = useSearchParams();
  const challengeToken = params.get("challenge") ?? "";
  const navigate = useNavigate();
  const { applyLogin } = useAuth();
  const [code, setCode] = useState("");
  const [saved, setSaved] = useState<LoginSuccess | null>(null);

  function enterApp(session: LoginSuccess) {
    applyLogin(session);
    navigate("/quick-start", { replace: true });
  }

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
      if (response.status !== "authenticated") return;
      // The plaintext recovery codes are returned exactly here, once. Hold the
      // session and make the user acknowledge them before entering the app.
      if (response.recovery_codes && response.recovery_codes.length > 0) {
        setSaved(response);
      } else {
        enterApp(response);
      }
    },
  });

  const enrollAlertRef = useAlertFocus(enrollQuery.isError);
  const confirmAlertRef = useAlertFocus(confirmMutation.isError);

  if (saved?.recovery_codes) {
    return (
      <AuthSplitLayout
        title="Save your recovery codes"
        subtitle="Each code works once, if you lose your authenticator. This is the only time they're shown. Store them somewhere safe."
      >
        <RecoveryCodesPanel
          codes={saved.recovery_codes}
          onContinue={() => enterApp(saved)}
        />
      </AuthSplitLayout>
    );
  }

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
        <>
          <ErrorBanner
            ref={enrollAlertRef}
            className="mb-2"
            title={describeAuthError(enrollQuery.error).message}
          />
          <p className="mb-4">
            <Link className="font-semibold text-text-link" to="/sign-in">
              Back to sign in
            </Link>
          </p>
        </>
      ) : null}

      <ol className="mb-5 list-decimal space-y-2 pl-4 text-body-md text-text-secondary">
        <li>Open your authenticator app (Google Authenticator, Authy, 1Password…).</li>
        <li>Scan the QR code below.</li>
        <li>Enter the 6-digit code it shows to confirm.</li>
      </ol>

      <div className="mb-4 flex flex-col items-center gap-3">
        {enrollQuery.data ? (
          // QR encodes the otpauth:// URL; rendered locally, never leaves the page.
          <div className="rounded-lg border border-border bg-white p-3">
            <QRCodeSVG
              value={enrollQuery.data.otpauth_url}
              size={168}
              level="M"
              aria-label="Authenticator setup QR code"
            />
          </div>
        ) : (
          <Skeleton className="size-[186px] rounded-lg" />
        )}

        <details className="w-full">
          <summary className="cursor-pointer text-body-sm text-text-link">
            Can't scan? Enter the key manually
          </summary>
          <div className="mt-2 rounded-md border border-border bg-surface-sunken px-3 py-2">
            <p className="type-overline text-text-subtle">Setup key</p>
            {enrollQuery.data ? (
              <p className="mt-1 select-all font-mono text-body-md tracking-wide text-text-primary">
                {enrollQuery.data.secret}
              </p>
            ) : (
              <Skeleton className="mt-1 h-5 w-56 max-w-full" />
            )}
          </div>
        </details>
      </div>

      {confirmMutation.isError ? (
        <ErrorBanner
          ref={confirmAlertRef}
          className="mb-4"
          title={describeAuthError(confirmMutation.error).message}
        />
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
