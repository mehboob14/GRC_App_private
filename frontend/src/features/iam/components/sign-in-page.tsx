import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { AuthSplitLayout } from "@/features/iam/components/auth-split-layout";
import { CheckEmailPanel } from "@/features/iam/components/check-email-panel";
import {
  Button,
  ErrorBanner,
  Icon,
  identityBgClass,
  PasswordField,
  Skeleton,
  TextField,
  Tooltip,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { authApi } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-context";
import { useAlertFocus } from "@/features/iam/hooks/use-alert-focus";
import type { LoginResponse, WorkspaceSummary } from "@/lib/api/types";

const schema = z.object({
  email: z
    .string()
    .email("Enter a work email — personal domains aren't allowed."),
  password: z.string().min(1, "Enter your password."),
});

type FormValues = z.infer<typeof schema>;

function messageFrom(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback;
}

export function SignInPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { applyLogin } = useAuth();

  const state = location.state as {
    notice?: string;
    from?: { pathname?: string };
    /**
     * A workspace switch that needs another auth step (Admin → MFA) hands the
     * login union off here so this surface can resume it — the switcher can't
     * host the challenge itself. See Topbar.
     */
    pending?: LoginResponse;
  } | null;
  const notice = state?.notice ?? null;
  // RequireAuth stored the route the visitor was heading to — land there
  // after auth resolves instead of flashing the default dashboard.
  const destination = state?.from?.pathname ?? "/quick-start";

  const [pending, setPending] = useState<LoginResponse | null>(
    state?.pending ?? null,
  );
  const [mfaCode, setMfaCode] = useState("");
  const [recoveryMode, setRecoveryMode] = useState(false);
  const [recoveryCode, setRecoveryCode] = useState("");

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { email: "", password: "" },
    mode: "onBlur",
  });

  function finishAuth(response: LoginResponse) {
    if (response.status === "authenticated") {
      applyLogin(response);
      navigate(destination, { replace: true });
      return;
    }
    setPending(response);
  }

  const loginMutation = useMutation({
    mutationFn: (values: FormValues) => authApi.login(values),
    onSuccess: finishAuth,
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
    onSuccess: finishAuth,
  });

  const selectMutation = useMutation({
    mutationFn: (ws: WorkspaceSummary) => {
      if (pending?.status !== "select_workspace") {
        return Promise.reject(new Error("No workspace selection in progress."));
      }
      return authApi.selectWorkspace(
        pending.selection_token,
        ws.membership_id,
      );
    },
    onSuccess: finishAuth,
  });

  const loginAlertRef = useAlertFocus(loginMutation.isError);
  const verifyAlertRef = useAlertFocus(verifyMutation.isError);
  const selectAlertRef = useAlertFocus(selectMutation.isError);

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
    loginMutation.reset();
    verifyMutation.reset();
    selectMutation.reset();
  }

  if (pending?.status === "mfa_enrollment_required") {
    return (
      <AuthSplitLayout
        title="Set up authenticator"
        subtitle="Redirecting to enrollment…"
      >
        <Skeleton className="h-11 w-full" />
      </AuthSplitLayout>
    );
  }

  if (pending?.status === "email_verification_required") {
    // Signed up but never clicked the link — same check-email surface as signup.
    return (
      <AuthSplitLayout
        title="Check your email"
        subtitle="Confirm your address to finish setting up your workspace."
      >
        <CheckEmailPanel
          email={pending.email}
          password={form.getValues("password")}
        />
      </AuthSplitLayout>
    );
  }

  if (pending?.status === "select_workspace") {
    return (
      <AuthSplitLayout
        title="Choose a workspace"
        subtitle="You belong to more than one organisation. Switching is an explicit, audited action."
      >
        <div className="flex flex-col gap-2">
          {pending.workspaces.map((ws) => (
            <button
              key={ws.membership_id}
              type="button"
              disabled={selectMutation.isPending}
              onClick={() => selectMutation.mutate(ws)}
              className="flex h-14 items-center gap-3 rounded-md border border-border px-3 text-left transition-colors duration-80 ease-state hover:bg-surface-hover focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent disabled:opacity-45"
            >
              {/* Same workspace-mark anatomy as the topbar switcher. */}
              <span
                className={cn(
                  "flex size-9 items-center justify-center rounded-md font-display text-title-sm font-extrabold text-text-inverse",
                  identityBgClass(ws.tenant_id),
                )}
              >
                {ws.tenant_name.slice(0, 1).toUpperCase()}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-body-lg font-semibold text-text-primary">
                  {ws.tenant_name}
                </span>
                <span className="block text-body-sm text-text-subtle">
                  {ws.role_name}
                </span>
              </span>
              <Icon name="chevr" className="size-4 text-text-subtle" />
            </button>
          ))}
        </div>
        {selectMutation.isError ? (
          <ErrorBanner
            ref={selectAlertRef}
            className="mt-3"
            title="Couldn't open the workspace"
          >
            {messageFrom(
              selectMutation.error,
              "The selection didn't reach the server — check your connection and try again.",
            )}
          </ErrorBanner>
        ) : null}
        <Button
          variant="link"
          className="mt-4 self-start"
          onClick={backToSignIn}
        >
          Back to sign in
        </Button>
      </AuthSplitLayout>
    );
  }

  if (pending?.status === "mfa_required") {
    return (
      <AuthSplitLayout
        title={recoveryMode ? "Enter a recovery code" : "Enter your MFA code"}
        subtitle={
          recoveryMode
            ? "Use one of the single-use codes you saved when you enrolled."
            : "Admin sign-in requires a 6-digit authenticator code."
        }
      >
        {verifyMutation.isError ? (
          <ErrorBanner
            ref={verifyAlertRef}
            className="mb-4"
            title={
              recoveryMode
                ? "Couldn't verify that recovery code"
                : "Couldn't verify the code"
            }
          >
            {messageFrom(
              verifyMutation.error,
              recoveryMode
                ? "That recovery code didn't match, or it's already been used — try another."
                : "That code didn't match — check your authenticator app and try again.",
            )}
          </ErrorBanner>
        ) : null}
        {recoveryMode ? (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (recoveryCode.trim())
                verifyMutation.mutate({ recovery_code: recoveryCode.trim() });
            }}
            noValidate
          >
            <TextField
              label="Recovery code"
              size="lg"
              autoComplete="one-time-code"
              placeholder="xxxxx-xxxxx"
              value={recoveryCode}
              onChange={(e) => setRecoveryCode(e.target.value)}
            />
            <Button
              type="submit"
              className="mt-4 w-full"
              size="lg"
              loading={verifyMutation.isPending}
              disabled={!recoveryCode.trim()}
            >
              Verify and continue
              <Icon name="arrowr" className="size-4" />
            </Button>
          </form>
        ) : (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (mfaCode.length === 6)
                verifyMutation.mutate({ code: mfaCode });
            }}
            noValidate
          >
            <TextField
              label="Authenticator code"
              size="lg"
              inputMode="numeric"
              autoComplete="one-time-code"
              placeholder="000000"
              value={mfaCode}
              onChange={(e) =>
                setMfaCode(e.target.value.replace(/\D/g, "").slice(0, 6))
              }
            />
            <Button
              type="submit"
              className="mt-4 w-full"
              size="lg"
              loading={verifyMutation.isPending}
              disabled={mfaCode.length !== 6}
            >
              Verify and continue
              <Icon name="arrowr" className="size-4" />
            </Button>
          </form>
        )}
        <Button
          variant="link"
          className="mt-4 self-start"
          onClick={() => {
            verifyMutation.reset();
            setRecoveryMode((on) => !on);
          }}
        >
          {recoveryMode
            ? "Use an authenticator code instead"
            : "Use a recovery code instead"}
        </Button>
        <Button
          variant="link"
          className="mt-1 self-start"
          onClick={backToSignIn}
        >
          Back to sign in
        </Button>
      </AuthSplitLayout>
    );
  }

  return (
    <AuthSplitLayout
      title="Welcome back"
      subtitle="Sign in to your compliance workspace."
    >
      {notice ? (
        <div
          className="mb-4 flex items-center gap-2 rounded-md border border-status-success-border bg-status-success-bg px-3.5 py-3"
          role="status"
        >
          <Icon name="check" className="size-4 text-status-success-text" />
          <p className="text-body-sm font-semibold text-status-success-text">
            {notice}
          </p>
        </div>
      ) : null}

      {/* Honest later-phase affordance: disabled, and the tooltip says when. */}
      <Tooltip content="Microsoft SSO arrives with identity federation in a later phase">
        <span tabIndex={0} className="block w-full rounded-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent">
          <Button
            type="button"
            variant="secondary"
            size="lg"
            className="w-full rounded-full"
            disabled
          >
            <span className="grid size-4 grid-cols-2 gap-px" aria-hidden>
              <span className="bg-[#F25022]" />
              <span className="bg-[#7FBA00]" />
              <span className="bg-[#00A4EF]" />
              <span className="bg-[#FFB900]" />
            </span>
            Continue with Microsoft
          </Button>
        </span>
      </Tooltip>

      <div className="my-4 flex items-center gap-3">
        <span className="h-px flex-1 bg-border" />
        <span className="text-body-sm font-medium text-text-subtle">
          or sign in with email
        </span>
        <span className="h-px flex-1 bg-border" />
      </div>

      <form
        className="flex flex-col gap-3"
        onSubmit={(e) =>
          void form.handleSubmit((values) => loginMutation.mutate(values))(e)
        }
        noValidate
      >
        {loginMutation.isError ? (
          <ErrorBanner ref={loginAlertRef} title="Sign-in failed">
            {messageFrom(
              loginMutation.error,
              "The request didn't reach the server — check your connection and try again.",
            )}
          </ErrorBanner>
        ) : null}
        <TextField
          label="Work email"
          size="lg"
          type="email"
          autoComplete="username"
          placeholder="name@company.com"
          error={form.formState.errors.email?.message}
          {...form.register("email")}
        />
        <PasswordField
          label="Password"
          size="lg"
          placeholder="••••••••••••"
          error={form.formState.errors.password?.message}
          {...form.register("password")}
        />
        <div className="-mt-1 flex justify-end">
          <Link
            to="/forgot-password"
            className="text-body-sm font-semibold text-text-link"
          >
            Forgot password?
          </Link>
        </div>
        <Button
          type="submit"
          className="auth-cta mt-1 w-full rounded-full bg-gradient-to-r from-action-accent via-action-primary to-action-primary-hover"
          size="lg"
          loading={loginMutation.isPending}
        >
          Sign in
          <Icon name="arrowr" className="size-4" />
        </Button>
      </form>

      <p className="mt-6 text-body-md text-text-secondary">
        New here?{" "}
        <Link className="font-semibold text-text-link" to="/sign-up">
          Start a trial
        </Link>
      </p>
    </AuthSplitLayout>
  );
}
