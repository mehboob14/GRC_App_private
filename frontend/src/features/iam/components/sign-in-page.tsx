import { useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Icon, identityBgClass, Skeleton } from "@/components/ui";
import { cn } from "@/lib/cn";
import { authApi } from "@/lib/api/endpoints";
import { useAuth } from "@/lib/auth/auth-context";
import type { LoginResponse, WorkspaceSummary } from "@/lib/api/types";
import { authSuccessDelay } from "@/features/iam/auth-motion";
import { AuthSplitLayout } from "@/features/iam/components/auth-split-layout";
import { AuthSubmitButton } from "@/features/iam/components/auth-submit-button";
import { CheckEmailPanel } from "@/features/iam/components/check-email-panel";
import { AuthAlert, FailureAlert } from "@/features/iam/auth-kit/auth-alert";
import {
  EmailSuggestion,
  OrDivider,
  SentTo,
  SsoOptions,
} from "@/features/iam/auth-kit/auth-bits";
import {
  linkClass,
  normalizeRecoveryCode,
} from "@/features/iam/auth-kit/helpers";
import { describeAuthFailure } from "@/features/iam/auth-kit/auth-errors";
import {
  AuthField,
  AuthPasswordField,
} from "@/features/iam/auth-kit/auth-field";
import { OtpInput } from "@/features/iam/auth-kit/otp-input";

const schema = z.object({
  email: z
    .string()
    .trim()
    .min(1, "Enter your work email.")
    .email("Enter a valid email, like name@company.com."),
  password: z.string().min(1, "Enter your password."),
});

type FormValues = z.infer<typeof schema>;

type SignInState = {
  notice?: string;
  /** Prefill, when another screen already knows the address (sign up, reset). */
  email?: string;
  from?: { pathname?: string };
  /**
   * A workspace switch that needs another auth step (Admin to MFA) hands the
   * login union off here so this surface can resume it. See Topbar.
   */
  pending?: LoginResponse;
} | null;

const quietLink =
  "rounded-sm text-body-sm font-semibold text-text-subtle hover:text-text-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent";

export function SignInPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { applyLogin } = useAuth();
  const state = location.state as SignInState;
  // RequireAuth stored the route the visitor was heading to.
  const destination = state?.from?.pathname ?? "/quick-start";

  const [pending, setPending] = useState<LoginResponse | null>(
    state?.pending ?? null,
  );
  const [notice, setNotice] = useState(state?.notice ?? null);
  const [signedIn, setSignedIn] = useState(false);
  const [shakeKey, setShakeKey] = useState(0);
  const [mfaCode, setMfaCode] = useState("");
  const [recoveryMode, setRecoveryMode] = useState(false);
  const [recoveryCode, setRecoveryCode] = useState("");
  const [codeHint, setCodeHint] = useState<string | null>(null);
  const [verified, setVerified] = useState(false);
  const alertRef = useRef<HTMLDivElement>(null);
  const recoveryRef = useRef<HTMLInputElement>(null);

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { email: state?.email ?? "", password: "" },
    mode: "onTouched",
  });
  const email = form.watch("email");
  const shake = () => setShakeKey((k) => k + 1);
  const focusAlert = () =>
    window.requestAnimationFrame(() => alertRef.current?.focus());

  function finishAuth(response: LoginResponse) {
    if (response.status === "authenticated") {
      applyLogin(response);
      navigate(destination, { replace: true });
      return;
    }
    setPending(response);
  }

  // A full session gets its success beat on the button before the app opens;
  // a further step (MFA, workspace choice) moves on straight away.
  function succeed(response: LoginResponse, celebrate: () => void) {
    const delay = response.status === "authenticated" ? authSuccessDelay() : 0;
    if (!delay) {
      finishAuth(response);
      return;
    }
    celebrate();
    window.setTimeout(() => finishAuth(response), delay);
  }

  const loginMutation = useMutation({
    mutationFn: (values: FormValues) => authApi.login(values),
    onMutate: () => setNotice(null),
    onSuccess: (response) => succeed(response, () => setSignedIn(true)),
    onError: (error) => {
      shake();
      // Wrong credentials: keep the email, select the password so retyping replaces it.
      if (describeAuthFailure(error, "signin").field === "password") {
        form.setFocus("password", { shouldSelect: true });
      } else {
        focusAlert();
      }
    },
  });

  const verifyMutation = useMutation({
    mutationFn: (payload: { code?: string; recovery_code?: string }) => {
      if (pending?.status !== "mfa_required") {
        return Promise.reject(new Error("No MFA challenge in progress."));
      }
      return authApi.verifyMfa({
        challenge_token: pending.challenge_token,
        ...payload,
      });
    },
    onSuccess: (response) => succeed(response, () => setVerified(true)),
    onError: (error) => {
      shake();
      const failure = describeAuthFailure(
        error,
        recoveryMode ? "recovery" : "mfa",
      );
      if (failure.field !== "code") {
        focusAlert();
      } else if (recoveryMode) {
        window.requestAnimationFrame(() => recoveryRef.current?.select());
      } else {
        // The boxes clear and focus returns to the first one.
        setMfaCode("");
      }
    },
  });

  const selectMutation = useMutation({
    mutationFn: (ws: WorkspaceSummary) => {
      if (pending?.status !== "select_workspace") {
        return Promise.reject(new Error("No workspace selection in progress."));
      }
      return authApi.selectWorkspace(pending.selection_token, ws.membership_id);
    },
    onSuccess: finishAuth,
    onError: focusAlert,
  });

  useEffect(() => {
    if (pending?.status === "mfa_enrollment_required") {
      navigate(`/mfa/enroll?challenge=${pending.challenge_token}`, {
        replace: true,
      });
    }
  }, [pending, navigate]);

  function backToSignIn() {
    setPending(null);
    setMfaCode("");
    setRecoveryCode("");
    setRecoveryMode(false);
    setCodeHint(null);
    setVerified(false);
    form.setValue("password", "");
    loginMutation.reset();
    verifyMutation.reset();
    selectMutation.reset();
  }

  const startAgain = (
    <button type="button" className={linkClass} onClick={backToSignIn}>
      Start again
    </button>
  );

  if (pending?.status === "mfa_enrollment_required") {
    return (
      <AuthSplitLayout
        mark={{ icon: "fingerprint" }}
        title="Set up your authenticator"
        subtitle="Taking you to setup."
      >
        <Skeleton className="h-11 w-full rounded-full" />
      </AuthSplitLayout>
    );
  }

  if (pending?.status === "email_verification_required") {
    // Signed up but never clicked the link: the same check email surface as sign up.
    return (
      <AuthSplitLayout
        mark={{ icon: "mail" }}
        title="Confirm your email"
        subtitle="Click the link we sent to finish setting up your workspace."
      >
        <CheckEmailPanel
          email={pending.email}
          password={form.getValues("password")}
          onChangeEmail={backToSignIn}
        />
      </AuthSplitLayout>
    );
  }

  if (pending?.status === "select_workspace") {
    const failure = selectMutation.isError
      ? describeAuthFailure(selectMutation.error, "select")
      : null;
    const retryWith = selectMutation.variables;
    return (
      <AuthSplitLayout
        title="Choose a workspace"
        subtitle="You belong to more than one organisation."
      >
        {failure ? (
          <FailureAlert
            ref={alertRef}
            className="mb-4"
            failure={failure}
            action={failure.kind === "expired" ? startAgain : undefined}
            onRetry={
              retryWith ? () => selectMutation.mutate(retryWith) : undefined
            }
          />
        ) : null}
        <ul className="flex flex-col gap-2.5">
          {pending.workspaces.map((ws) => {
            const busy =
              selectMutation.isPending &&
              selectMutation.variables?.membership_id === ws.membership_id;
            return (
              <li key={ws.membership_id}>
                <button
                  type="button"
                  disabled={selectMutation.isPending}
                  onClick={() => selectMutation.mutate(ws)}
                  className={cn(
                    "group flex w-full items-center gap-3 rounded-2xl border border-border bg-surface-primary p-3 text-left shadow-1",
                    "transition-[border-color,box-shadow,transform] duration-200 ease-state hover:-translate-y-px hover:border-action-accent/50 hover:shadow-2",
                    "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent",
                    "disabled:pointer-events-none",
                    selectMutation.isPending && !busy && "opacity-50",
                  )}
                >
                  {/* Same workspace mark as the topbar switcher. */}
                  <span
                    className={cn(
                      "grid size-11 shrink-0 place-items-center rounded-xl font-display text-heading-sm text-text-inverse",
                      identityBgClass(ws.tenant_id),
                    )}
                  >
                    {ws.tenant_name.slice(0, 1).toUpperCase()}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-title-md text-text-primary">
                      {ws.tenant_name}
                    </span>
                    <span className="block truncate text-body-sm text-text-subtle">
                      {ws.role_name}
                    </span>
                  </span>
                  <span
                    className={cn(
                      "grid size-8 shrink-0 place-items-center rounded-full transition-colors",
                      busy
                        ? "text-action-accent"
                        : "bg-surface-sunken text-text-subtle group-hover:bg-action-accent group-hover:text-white",
                    )}
                  >
                    <Icon
                      name={busy ? "spinner" : "arrowr"}
                      className={cn("size-4", busy && "animate-spin")}
                    />
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
        <div className="mt-6 text-center">
          <button type="button" onClick={backToSignIn} className={quietLink}>
            Back to sign in
          </button>
        </div>
      </AuthSplitLayout>
    );
  }

  if (pending?.status === "mfa_required") {
    const failure = verifyMutation.isError
      ? describeAuthFailure(
          verifyMutation.error,
          recoveryMode ? "recovery" : "mfa",
        )
      : null;
    const signingInAs = form.getValues("email");
    const locked = verifyMutation.isPending || verified;
    const clear = () => {
      setCodeHint(null);
      if (verifyMutation.isError) verifyMutation.reset();
    };

    return (
      <AuthSplitLayout
        mark={{ icon: recoveryMode ? "key" : "fingerprint" }}
        title={recoveryMode ? "Use a recovery code" : "Verify it's you"}
        subtitle={
          recoveryMode
            ? "Enter one of the codes you saved when you set up MFA."
            : "Enter the 6 digit code from your authenticator app."
        }
      >
        {signingInAs ? (
          <SentTo
            label="Signing in as"
            email={signingInAs}
            onChange={backToSignIn}
          />
        ) : null}
        <form
          className="mt-5 flex flex-col gap-5"
          noValidate
          onSubmit={(e) => {
            e.preventDefault();
            if (locked) return;
            if (recoveryMode) {
              const code = normalizeRecoveryCode(recoveryCode);
              if (!code) {
                setCodeHint("Enter a recovery code.");
                shake();
                return;
              }
              verifyMutation.mutate({ recovery_code: code });
            } else if (mfaCode.length !== 6) {
              setCodeHint("Enter all 6 digits.");
              shake();
            } else {
              verifyMutation.mutate({ code: mfaCode });
            }
          }}
        >
          {failure ? (
            <FailureAlert
              ref={alertRef}
              failure={failure}
              action={failure.kind === "expired" ? startAgain : undefined}
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
              disabled={locked}
              value={recoveryCode}
              error={codeHint ?? undefined}
              onChange={(e) => {
                setRecoveryCode(e.target.value);
                clear();
              }}
            />
          ) : (
            <div>
              <OtpInput
                value={mfaCode}
                autoFocus
                disabled={locked}
                invalid={failure?.field === "code" || Boolean(codeHint)}
                onChange={(value) => {
                  setMfaCode(value);
                  clear();
                }}
                onComplete={(code) => {
                  if (!locked) verifyMutation.mutate({ code });
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
          )}
          <AuthSubmitButton
            label="Verify"
            steps={["Checking your code", "Securing your session"]}
            successLabel="Verified"
            phase={
              verified
                ? "success"
                : verifyMutation.isPending
                  ? "loading"
                  : "idle"
            }
            shakeKey={shakeKey}
          />
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
          <button type="button" onClick={backToSignIn} className={quietLink}>
            Back to sign in
          </button>
        </div>
      </AuthSplitLayout>
    );
  }

  const failure = loginMutation.isError
    ? describeAuthFailure(loginMutation.error, "signin")
    : null;
  const clearFailure = () => {
    if (loginMutation.isError) loginMutation.reset();
  };
  const submit = form.handleSubmit(
    (values) => loginMutation.mutate(values),
    shake,
  );

  return (
    <AuthSplitLayout
      title="Welcome back"
      subtitle="Sign in to your Verity workspace."
    >
      <form
        className="flex flex-col gap-4"
        noValidate
        onSubmit={(e) => void submit(e)}
      >
        {failure ? (
          <FailureAlert
            ref={alertRef}
            failure={failure}
            onRetry={() => void submit()}
            action={
              failure.kind === "credentials" ? (
                <Link
                  to="/forgot-password"
                  state={{ email }}
                  className={linkClass}
                >
                  Reset password
                </Link>
              ) : undefined
            }
          />
        ) : notice ? (
          <AuthAlert tone="success" title={notice} />
        ) : null}

        <AuthField
          label="Work email"
          icon="mail"
          type="email"
          inputMode="email"
          autoComplete="username"
          autoCapitalize="none"
          spellCheck={false}
          placeholder="name@company.com"
          error={form.formState.errors.email?.message}
          below={
            form.formState.errors.email ? null : (
              <EmailSuggestion
                email={email}
                onAccept={(value) =>
                  form.setValue("email", value, { shouldValidate: true })
                }
              />
            )
          }
          {...form.register("email", { onChange: clearFailure })}
        />
        <AuthPasswordField
          label="Password"
          autoComplete="current-password"
          labelAction={
            <Link
              to="/forgot-password"
              state={{ email }}
              className={cn(linkClass, "text-label-sm")}
            >
              Forgot password?
            </Link>
          }
          error={form.formState.errors.password?.message}
          {...form.register("password", { onChange: clearFailure })}
        />
        <AuthSubmitButton
          className="mt-1"
          label="Sign in"
          steps={["Checking credentials", "Securing your session"]}
          successLabel="Signed in"
          phase={
            signedIn ? "success" : loginMutation.isPending ? "loading" : "idle"
          }
          shakeKey={shakeKey}
        />
      </form>

      <OrDivider>or continue with</OrDivider>
      <SsoOptions />

      <p className="mt-7 text-center text-body-md text-text-secondary">
        New to Verity?{" "}
        <Link className={linkClass} to="/sign-up">
          Create a workspace
        </Link>
      </p>
    </AuthSplitLayout>
  );
}
