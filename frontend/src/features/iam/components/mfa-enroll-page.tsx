import { useRef, useState, type ReactNode } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { QRCodeSVG } from "qrcode.react";
import { Icon, Skeleton } from "@/components/ui";
import { cn } from "@/lib/cn";
import { authApi } from "@/lib/api/endpoints";
import { useAuth } from "@/lib/auth/auth-context";
import type { LoginSuccess } from "@/lib/api/types";
import { AuthSplitLayout } from "@/features/iam/components/auth-split-layout";
import { AuthSubmitButton } from "@/features/iam/components/auth-submit-button";
import { RecoveryCodesPanel } from "@/features/iam/components/recovery-codes-panel";
import { FailureAlert } from "@/features/iam/auth-kit/auth-alert";
import { linkClass, secondaryPill } from "@/features/iam/auth-kit/helpers";
import { describeAuthFailure } from "@/features/iam/auth-kit/auth-errors";
import { OtpInput } from "@/features/iam/auth-kit/otp-input";

function Step({ n, children }: { n: number; children: ReactNode }) {
  return (
    <li className="flex items-start gap-3">
      <span className="grid size-6 shrink-0 place-items-center rounded-full bg-action-accent-tint text-caption font-bold text-action-primary">
        {n}
      </span>
      <span className="pt-0.5 text-body-md text-text-secondary">
        {children}
      </span>
    </li>
  );
}

export function MfaEnrollPage() {
  const [params] = useSearchParams();
  const challengeToken = params.get("challenge") ?? "";
  const navigate = useNavigate();
  const { applyLogin } = useAuth();
  const [code, setCode] = useState("");
  const [codeHint, setCodeHint] = useState<string | null>(null);
  const [saved, setSaved] = useState<LoginSuccess | null>(null);
  const [showKey, setShowKey] = useState(false);
  const [copied, setCopied] = useState(false);
  const [shakeKey, setShakeKey] = useState(0);
  const alertRef = useRef<HTMLDivElement>(null);

  function enterApp(session: LoginSuccess) {
    applyLogin(session);
    navigate("/quick-start", { replace: true });
  }

  const enrollQuery = useQuery({
    queryKey: ["mfa-enroll", challengeToken],
    queryFn: () => authApi.startMfaEnroll(challengeToken),
    enabled: challengeToken.length > 0,
    // The challenge is single use and short lived: never refetch or retry it.
    staleTime: Infinity,
    retry: false,
  });

  const confirmMutation = useMutation({
    mutationFn: (value: string) =>
      authApi.confirmMfaEnroll({
        challenge_token: challengeToken,
        code: value,
      }),
    onSuccess: (response) => {
      if (response.status !== "authenticated") return;
      // The plaintext recovery codes are returned exactly here, once. Hold the
      // session until the user has saved them.
      if (response.recovery_codes && response.recovery_codes.length > 0) {
        setSaved(response);
      } else {
        enterApp(response);
      }
    },
    onError: (error) => {
      setShakeKey((k) => k + 1);
      if (describeAuthFailure(error, "enroll").field === "code") setCode("");
      else window.requestAnimationFrame(() => alertRef.current?.focus());
    },
  });

  if (saved?.recovery_codes) {
    return (
      <AuthSplitLayout
        mark={{ icon: "key", tone: "success" }}
        title="Save your recovery codes"
        subtitle="Each works once if you lose your phone. You won't see them again."
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
        mark={{ icon: "alert", tone: "warning" }}
        title="This setup link is incomplete"
        subtitle="Sign in again to restart MFA setup."
      >
        <Link to="/sign-in" className={secondaryPill}>
          Back to sign in
        </Link>
      </AuthSplitLayout>
    );
  }

  if (enrollQuery.isError) {
    const failure = describeAuthFailure(enrollQuery.error, "select");
    return (
      <AuthSplitLayout
        mark={{ icon: "fingerprint", tone: "warning" }}
        title="We couldn't start setup"
      >
        <div className="flex flex-col gap-4">
          <FailureAlert failure={failure} />
          <Link to="/sign-in" className={secondaryPill}>
            Back to sign in
          </Link>
        </div>
      </AuthSplitLayout>
    );
  }

  const failure = confirmMutation.isError
    ? describeAuthFailure(confirmMutation.error, "enroll")
    : null;
  const setup = enrollQuery.data;
  const phase = confirmMutation.isPending ? "loading" : "idle";

  async function copyKey() {
    if (!setup) return;
    try {
      await navigator.clipboard.writeText(setup.secret);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard blocked: the key is on screen to copy by hand.
    }
  }

  return (
    <AuthSplitLayout
      mark={{ icon: "fingerprint" }}
      title="Protect your admin account"
      subtitle="Admins sign in with a code from an authenticator app."
    >
      <ol className="flex flex-col gap-3">
        <Step n={1}>
          Open an authenticator app such as Google Authenticator, Authy or
          1Password.
        </Step>
        <Step n={2}>Scan this QR code.</Step>
      </ol>

      <div className="mt-4 flex flex-col items-center gap-3 rounded-2xl border border-border bg-surface-sunken p-4">
        {setup ? (
          // Encodes the otpauth URL; rendered locally, never leaves the page.
          <div className="auth-mark-in rounded-xl bg-white p-3 shadow-2 ring-1 ring-border">
            <QRCodeSVG
              value={setup.otpauth_url}
              size={152}
              level="M"
              aria-label="Authenticator setup QR code"
            />
          </div>
        ) : (
          <Skeleton className="size-[176px] rounded-xl" />
        )}
        {showKey && setup ? (
          <div className="auth-msg-in flex w-full items-center gap-2 rounded-xl border border-border bg-surface-primary py-1.5 pl-3 pr-1.5">
            <span className="min-w-0 flex-1 select-all break-all font-mono text-body-sm font-semibold tracking-wide text-text-primary">
              {setup.secret}
            </span>
            <button
              type="button"
              onClick={() => void copyKey()}
              className="inline-flex h-8 shrink-0 items-center gap-1.5 rounded-lg px-2.5 text-label-sm text-text-link hover:bg-surface-hover focus-visible:outline focus-visible:outline-2 focus-visible:outline-action-accent"
            >
              <Icon name={copied ? "check" : "copy"} className="size-3.5" />
              {copied ? "Copied" : "Copy"}
            </button>
          </div>
        ) : (
          <button
            type="button"
            className={cn(linkClass, "text-body-sm")}
            onClick={() => setShowKey(true)}
            disabled={!setup}
          >
            Can't scan? Enter a setup key instead
          </button>
        )}
      </div>

      <ol className="mt-4 flex flex-col gap-3">
        <Step n={3}>Enter the 6 digit code the app shows.</Step>
      </ol>

      <form
        className="mt-3 flex flex-col gap-4"
        noValidate
        onSubmit={(e) => {
          e.preventDefault();
          if (confirmMutation.isPending || !setup) return;
          if (code.length !== 6) {
            setCodeHint("Enter all 6 digits.");
            setShakeKey((k) => k + 1);
            return;
          }
          confirmMutation.mutate(code);
        }}
      >
        {failure ? <FailureAlert ref={alertRef} failure={failure} /> : null}
        <div>
          <OtpInput
            value={code}
            disabled={!setup || confirmMutation.isPending}
            invalid={failure?.field === "code" || Boolean(codeHint)}
            onChange={(value) => {
              setCode(value);
              setCodeHint(null);
              if (confirmMutation.isError) confirmMutation.reset();
            }}
            onComplete={(value) => {
              if (setup && !confirmMutation.isPending)
                confirmMutation.mutate(value);
            }}
          />
          {codeHint ? (
            <p
              role="alert"
              className="auth-msg-in mt-2 flex items-center gap-1.5 text-body-sm font-medium text-status-danger-text"
            >
              <Icon name="alert" className="size-3.5" />
              {codeHint}
            </p>
          ) : null}
        </div>
        <AuthSubmitButton
          label="Turn on MFA"
          steps={["Checking your code", "Creating recovery codes"]}
          successLabel="MFA is on"
          phase={phase}
          shakeKey={shakeKey}
        />
      </form>
    </AuthSplitLayout>
  );
}
