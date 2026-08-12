import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { AuthSplitLayout } from "@/features/iam/components/auth-split-layout";
import { Button, Icon, TextField } from "@/components/ui";
import { authApi } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-context";
import { DEMO_MFA_CODE } from "@/mocks/fixtures";

export function MfaEnrollPage() {
  const [params] = useSearchParams();
  const challengeToken = params.get("challenge") ?? "";
  const navigate = useNavigate();
  const { applyLogin } = useAuth();
  const [secret, setSecret] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!challengeToken) return;
    void authApi
      .startMfaEnroll(challengeToken)
      .then((res) => setSecret(res.secret))
      .catch((err: unknown) => {
        setError(
          err instanceof ApiError
            ? err.message
            : "Could not start MFA enrollment.",
        );
      });
  }, [challengeToken]);

  async function onConfirm() {
    setBusy(true);
    setError(null);
    try {
      const response = await authApi.confirmMfaEnroll({
        challenge_token: challengeToken,
        code,
      });
      if (response.status === "authenticated") {
        applyLogin(response);
        navigate("/quick-start", { replace: true });
      }
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Enter the 6-digit code from your authenticator.",
      );
    } finally {
      setBusy(false);
    }
  }

  if (!challengeToken) {
    return (
      <AuthSplitLayout title="MFA enrollment" subtitle="Missing challenge.">
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
        <p className="mt-1 font-mono text-body-md text-text">
          {secret ?? "Loading…"}
        </p>
      </div>

      <TextField
        label="Authenticator code"
        inputMode="numeric"
        autoComplete="one-time-code"
        placeholder="123456"
        value={code}
        onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
        hint={`Demo code: ${DEMO_MFA_CODE}`}
      />
      {error ? (
        <p className="mt-2 text-body-sm text-fail-fg" role="alert">
          {error}
        </p>
      ) : null}
      <Button
        className="mt-4 w-full"
        size="lg"
        loading={busy}
        disabled={code.length !== 6}
        onClick={() => void onConfirm()}
      >
        Confirm and continue
        <Icon name="arrowr" className="size-4" />
      </Button>
    </AuthSplitLayout>
  );
}
