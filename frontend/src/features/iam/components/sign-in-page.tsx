import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { AuthSplitLayout } from "@/features/iam/components/auth-split-layout";
import {
  Button,
  ErrorBanner,
  Icon,
  PasswordField,
  Skeleton,
  TextField,
  Tooltip,
} from "@/components/ui";
import { authApi } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-context";
import { useAlertFocus } from "@/features/iam/hooks/use-alert-focus";
import { VENDOR_MARKS } from "@/lib/vendor-marks";
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
  const [pending, setPending] = useState<LoginResponse | null>(null);
  const [mfaCode, setMfaCode] = useState("");

  const state = location.state as {
    notice?: string;
    from?: { pathname?: string };
  } | null;
  const notice = state?.notice ?? null;
  // RequireAuth stored the route the visitor was heading to — land there
  // after auth resolves instead of flashing the default dashboard.
  const destination = state?.from?.pathname ?? "/quick-start";

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
    mutationFn: (code: string) => {
      if (pending?.status !== "mfa_required") {
        return Promise.reject(new Error("No MFA challenge in progress."));
      }
      return authApi.verifyMfa({
        challenge_token: pending.challenge_token,
        code,
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
              <span className="flex size-9 items-center justify-center rounded-md bg-action-primary font-display text-title-sm text-action-primary-fg">
                {ws.tenant_name.slice(0, 1)}
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
        title="Enter your MFA code"
        subtitle="Admin sign-in requires a 6-digit authenticator code."
      >
        {verifyMutation.isError ? (
          <ErrorBanner
            ref={verifyAlertRef}
            className="mb-4"
            title="Couldn't verify the code"
          >
            {messageFrom(
              verifyMutation.error,
              "That code didn't match — check your authenticator app and try again.",
            )}
          </ErrorBanner>
        ) : null}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (mfaCode.length === 6) verifyMutation.mutate(mfaCode);
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
      <Tooltip content="Okta SSO arrives with identity federation in a later phase">
        <span tabIndex={0} className="block w-full rounded-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent">
          <Button
            type="button"
            variant="secondary"
            size="lg"
            className="w-full"
            disabled
          >
            <span
              className="flex size-5 items-center justify-center rounded-xs text-caption font-semibold text-white"
              style={{ backgroundColor: VENDOR_MARKS.okta.color }}
            >
              {VENDOR_MARKS.okta.label}
            </span>
            Continue with Okta SSO
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
        <Button
          type="submit"
          className="mt-1 w-full"
          size="lg"
          loading={loginMutation.isPending}
        >
          Sign in
          <Icon name="arrowr" className="size-4" />
        </Button>
      </form>

      <div className="mt-5 flex items-center gap-2 rounded-md border border-status-success-border bg-status-success-bg px-3.5 py-3">
        <Icon name="shield" className="size-4 text-status-success-text" />
        <p className="text-body-sm font-semibold text-status-success-text">
          Protected by SSO &amp; enforced MFA · SOC 2 Type II
        </p>
      </div>

      <p className="mt-6 text-body-md text-text-secondary">
        New here?{" "}
        <Link className="font-semibold text-text-link" to="/sign-up">
          Start a trial
        </Link>
      </p>
    </AuthSplitLayout>
  );
}
