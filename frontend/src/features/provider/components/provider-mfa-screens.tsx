import { useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { QRCodeSVG } from "qrcode.react";
import { Button, Icon, Skeleton } from "@/components/ui";
import { cn } from "@/lib/cn";
import { FailureAlert } from "@/features/iam/auth-kit/auth-alert";
import { SentTo } from "@/features/iam/auth-kit/auth-bits";
import { AuthField } from "@/features/iam/auth-kit/auth-field";
import {
  linkClass,
  normalizeRecoveryCode,
} from "@/features/iam/auth-kit/helpers";
import { OtpInput } from "@/features/iam/auth-kit/otp-input";
import { RecoveryCodesPanel } from "@/features/iam/components/recovery-codes-panel";
import { providerAuthApi } from "../api";
import { describeProviderAuthFailure } from "../errors";
import type {
  ProviderChallenge,
  ProviderEnrollConfirm,
  ProviderSession,
} from "../types";
import { ProviderAuthShell } from "./provider-auth-shell";

const quietLink =
  "rounded-sm text-body-sm font-semibold text-text-subtle hover:text-text-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent";

function CodeHint({ children }: { children: string }) {
  return (
    <p
      role="alert"
      className="auth-msg-in mt-2 flex items-center gap-1.5 text-body-sm font-medium text-status-danger-text"
    >
      <Icon name="alert" className="size-3.5" />
      {children}
    </p>
  );
}

/** The second factor for an admin who has already enrolled: a code, or one recovery code. */
export function VerifyScreen({
  email,
  challenge,
  onSession,
  onRestart,
}: {
  email: string;
  challenge: ProviderChallenge;
  onSession: (session: ProviderSession) => void;
  onRestart: () => void;
}) {
  const [code, setCode] = useState("");
  const [recoveryMode, setRecoveryMode] = useState(false);
  const [recoveryCode, setRecoveryCode] = useState("");
  const [hint, setHint] = useState<string | null>(null);
  const alertRef = useRef<HTMLDivElement>(null);
  const recoveryRef = useRef<HTMLInputElement>(null);

  const mutation = useMutation({
    mutationFn: (payload: { code?: string; recovery_code?: string }) =>
      providerAuthApi.verify({
        challenge_token: challenge.challenge_token,
        ...payload,
      }),
    onSuccess: onSession,
    onError: (error) => {
      const failure = describeProviderAuthFailure(
        error,
        recoveryMode ? "recovery" : "mfa",
      );
      if (failure.field !== "code") {
        window.requestAnimationFrame(() => alertRef.current?.focus());
      } else if (recoveryMode) {
        window.requestAnimationFrame(() => recoveryRef.current?.select());
      } else {
        setCode("");
      }
    },
  });

  const failure = mutation.isError
    ? describeProviderAuthFailure(
        mutation.error,
        recoveryMode ? "recovery" : "mfa",
      )
    : null;
  const clear = () => {
    setHint(null);
    if (mutation.isError) mutation.reset();
  };

  return (
    <ProviderAuthShell
      title={recoveryMode ? "Use a recovery code" : "Verify it's you"}
      subtitle={
        recoveryMode
          ? "Enter one of the codes you saved when you set up."
          : "Enter the 6 digit code from your authenticator app."
      }
    >
      <SentTo label="Signing in as" email={email} onChange={onRestart} />
      <form
        className="mt-5 flex flex-col gap-5"
        noValidate
        onSubmit={(event) => {
          event.preventDefault();
          if (mutation.isPending) return;
          if (recoveryMode) {
            const value = normalizeRecoveryCode(recoveryCode);
            if (!value) {
              setHint("Enter a recovery code.");
              return;
            }
            mutation.mutate({ recovery_code: value });
          } else if (code.length !== 6) {
            setHint("Enter all 6 digits.");
          } else {
            mutation.mutate({ code });
          }
        }}
      >
        {failure ? (
          <FailureAlert
            ref={alertRef}
            failure={failure}
            action={
              failure.kind === "expired" ? (
                <button type="button" className={linkClass} onClick={onRestart}>
                  Start again
                </button>
              ) : undefined
            }
          />
        ) : null}
        {recoveryMode ? (
          <AuthField
            ref={recoveryRef}
            label="Recovery code"
            icon="key"
            autoFocus
            autoComplete="off"
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
            placeholder="xxxxx xxxxx"
            disabled={mutation.isPending}
            value={recoveryCode}
            error={hint ?? undefined}
            onChange={(event) => {
              setRecoveryCode(event.target.value);
              clear();
            }}
          />
        ) : (
          <div>
            <OtpInput
              value={code}
              autoFocus
              disabled={mutation.isPending}
              invalid={failure?.field === "code" || Boolean(hint)}
              onChange={(value) => {
                setCode(value);
                clear();
              }}
              onComplete={(value) => {
                if (!mutation.isPending) mutation.mutate({ code: value });
              }}
            />
            {hint ? <CodeHint>{hint}</CodeHint> : null}
          </div>
        )}
        <Button type="submit" size="lg" className="w-full" loading={mutation.isPending}>
          Verify
        </Button>
      </form>
      <div className="mt-5 flex items-center justify-between gap-4">
        <button
          type="button"
          className={cn(linkClass, "text-body-sm")}
          onClick={() => {
            clear();
            setRecoveryMode((on) => !on);
          }}
        >
          {recoveryMode ? "Use authenticator app" : "Use a recovery code"}
        </button>
        <button type="button" onClick={onRestart} className={quietLink}>
          Back to sign in
        </button>
      </div>
    </ProviderAuthShell>
  );
}

/**
 * First sign in: the admin is created without a second factor, so the password
 * only buys the right to enrol one. A QR code, then a first code to prove it
 * took, then the one time recovery codes.
 */
export function EnrollScreen({
  email,
  challenge,
  onEnrolled,
  onRestart,
}: {
  email: string;
  challenge: ProviderChallenge;
  onEnrolled: (result: ProviderEnrollConfirm) => void;
  onRestart: () => void;
}) {
  const [code, setCode] = useState("");
  const [hint, setHint] = useState<string | null>(null);
  const [showKey, setShowKey] = useState(false);
  const [copied, setCopied] = useState(false);
  const alertRef = useRef<HTMLDivElement>(null);

  const setup = useQuery({
    queryKey: ["provider-auth", "enroll", challenge.challenge_token],
    queryFn: () => providerAuthApi.startEnrollment(challenge.challenge_token),
    // The challenge is short lived and the secret is shown once: never refetch
    // it, never retry it, and never keep it in the cache after this screen.
    staleTime: Infinity,
    gcTime: 0,
    retry: false,
  });

  const confirm = useMutation({
    mutationFn: (value: string) =>
      providerAuthApi.confirmEnrollment(challenge.challenge_token, value),
    onSuccess: onEnrolled,
    onError: (error) => {
      if (describeProviderAuthFailure(error, "enroll").field === "code") {
        setCode("");
      } else {
        window.requestAnimationFrame(() => alertRef.current?.focus());
      }
    },
  });

  if (setup.isError) {
    return (
      <ProviderAuthShell title="We couldn't start setup">
        <div className="flex flex-col gap-4">
          <FailureAlert
            failure={describeProviderAuthFailure(setup.error, "enroll")}
          />
          <Button variant="secondary" size="lg" onClick={onRestart}>
            Back to sign in
          </Button>
        </div>
      </ProviderAuthShell>
    );
  }

  const failure = confirm.isError
    ? describeProviderAuthFailure(confirm.error, "enroll")
    : null;
  const secret = setup.data;

  async function copyKey() {
    if (!secret) return;
    try {
      await navigator.clipboard.writeText(secret.secret);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard blocked: the key is on screen to copy by hand.
    }
  }

  return (
    <ProviderAuthShell
      title="Set up your authenticator"
      subtitle="Platform admins always sign in with a code."
    >
      <SentTo label="Signing in as" email={email} onChange={onRestart} />
      <div className="mt-5 flex flex-col items-center gap-3 rounded-2xl border border-border bg-surface-sunken p-4">
        {secret ? (
          // Encodes the otpauth URI; drawn here in the browser, never sent anywhere.
          <div className="rounded-xl bg-white p-3 shadow-2 ring-1 ring-border">
            <QRCodeSVG
              value={secret.otpauth_uri}
              size={152}
              level="M"
              aria-label="Authenticator setup QR code"
            />
          </div>
        ) : (
          <Skeleton className="size-[176px] rounded-xl" />
        )}
        <p className="text-center text-body-sm text-text-secondary">
          Scan it with Google Authenticator, Authy or 1Password.
        </p>
        {showKey && secret ? (
          <div className="auth-msg-in flex w-full items-center gap-2 rounded-xl border border-border bg-surface-primary py-1.5 pl-3 pr-1.5">
            <span className="min-w-0 flex-1 select-all break-all font-mono text-body-sm font-semibold tracking-wide text-text-primary">
              {secret.secret}
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
            disabled={!secret}
          >
            Can't scan? Show the setup key
          </button>
        )}
      </div>

      <form
        className="mt-5 flex flex-col gap-4"
        noValidate
        onSubmit={(event) => {
          event.preventDefault();
          if (confirm.isPending || !secret) return;
          if (code.length !== 6) {
            setHint("Enter all 6 digits.");
            return;
          }
          confirm.mutate(code);
        }}
      >
        {failure ? <FailureAlert ref={alertRef} failure={failure} /> : null}
        <div>
          <p className="mb-2 text-label-sm font-semibold text-text-primary">
            Enter the 6 digit code the app shows
          </p>
          <OtpInput
            value={code}
            disabled={!secret || confirm.isPending}
            invalid={failure?.field === "code" || Boolean(hint)}
            onChange={(value) => {
              setCode(value);
              setHint(null);
              if (confirm.isError) confirm.reset();
            }}
            onComplete={(value) => {
              if (secret && !confirm.isPending) confirm.mutate(value);
            }}
          />
          {hint ? <CodeHint>{hint}</CodeHint> : null}
        </div>
        <Button type="submit" size="lg" className="w-full" loading={confirm.isPending}>
          Turn on two step sign in
        </Button>
      </form>
    </ProviderAuthShell>
  );
}

/** The one time display of the recovery codes. The session is held until they are saved. */
export function RecoveryCodesScreen({
  codes,
  onContinue,
}: {
  codes: string[];
  onContinue: () => void;
}) {
  return (
    <ProviderAuthShell
      title="Save your recovery codes"
      subtitle="Each works once if you lose your phone. You won't see them again."
    >
      <RecoveryCodesPanel codes={codes} onContinue={onContinue} />
    </ProviderAuthShell>
  );
}
