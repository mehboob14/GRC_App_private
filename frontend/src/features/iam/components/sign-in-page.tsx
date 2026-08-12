import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { AuthSplitLayout } from "@/features/iam/components/auth-split-layout";
import { Button, Icon, PasswordField, TextField } from "@/components/ui";
import { authApi } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-context";
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

  const notice =
    (location.state as { notice?: string } | null)?.notice ?? null;

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { email: "", password: "" },
    mode: "onBlur",
  });

  function finishAuth(response: LoginResponse) {
    if (response.status === "authenticated") {
      applyLogin(response);
      navigate("/quick-start", { replace: true });
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
        <div className="h-10 animate-pulse rounded-lg bg-na-bg" />
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
              className="flex h-[52px] items-center gap-3 rounded-[10px] border border-border px-3 text-left hover:bg-bg-sunken"
            >
              <span className="flex size-9 items-center justify-center rounded-lg bg-accent font-display text-title-sm text-accent-fg">
                {ws.tenant_name.slice(0, 1)}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-body-lg font-semibold text-text">
                  {ws.tenant_name}
                </span>
                <span className="block text-body-sm text-text-faint">
                  {ws.role_name}
                </span>
              </span>
              <Icon name="chevr" className="size-4 text-text-faint" />
            </button>
          ))}
        </div>
        {selectMutation.isError ? (
          <p className="mt-3 text-body-sm text-fail-fg" role="alert">
            {messageFrom(selectMutation.error, "Could not open workspace.")}
          </p>
        ) : null}
        <button
          type="button"
          className="mt-4 text-body-md font-medium text-accent"
          onClick={backToSignIn}
        >
          Back to sign in
        </button>
      </AuthSplitLayout>
    );
  }

  if (pending?.status === "mfa_required") {
    return (
      <AuthSplitLayout
        title="Enter your MFA code"
        subtitle="Admin sign-in requires a 6-digit authenticator code."
      >
        <TextField
          label="Authenticator code"
          inputMode="numeric"
          autoComplete="one-time-code"
          placeholder="000000"
          value={mfaCode}
          onChange={(e) =>
            setMfaCode(e.target.value.replace(/\D/g, "").slice(0, 6))
          }
        />
        {verifyMutation.isError ? (
          <p className="mt-2 text-body-sm text-fail-fg" role="alert">
            {messageFrom(
              verifyMutation.error,
              "That code is incorrect or expired.",
            )}
          </p>
        ) : null}
        <Button
          className="mt-4 h-[46px] w-full rounded-[10px]"
          size="lg"
          loading={verifyMutation.isPending}
          disabled={mfaCode.length !== 6}
          onClick={() => verifyMutation.mutate(mfaCode)}
        >
          Verify and continue
          <Icon name="arrowr" className="size-4" />
        </Button>
        <button
          type="button"
          className="mt-4 text-body-md font-medium text-accent"
          onClick={backToSignIn}
        >
          Back to sign in
        </button>
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
          className="mb-4 flex items-center gap-2 rounded-lg border border-pass-border bg-pass-bg px-[13px] py-[11px]"
          role="status"
        >
          <Icon name="check" className="size-[15px] text-pass-fg" />
          <p className="text-body-sm font-semibold text-pass-fg">{notice}</p>
        </div>
      ) : null}

      <Button
        type="button"
        variant="secondary"
        size="lg"
        className="h-[46px] w-full rounded-[10px] border-border-strong font-semibold"
        disabled
        aria-disabled
        title="Coming soon — federation is Phase 3"
      >
        <span
          className="flex size-5 items-center justify-center rounded-sm text-body-sm font-medium text-white"
          style={{ backgroundColor: VENDOR_MARKS.okta.color }}
        >
          {VENDOR_MARKS.okta.label}
        </span>
        Continue with Okta SSO
      </Button>

      <div className="my-[18px] flex items-center gap-3">
        <span className="h-px flex-1 bg-border" />
        <span className="text-body-sm font-medium text-text-faint">
          or sign in with email
        </span>
        <span className="h-px flex-1 bg-border" />
      </div>

      <form
        className="flex flex-col"
        onSubmit={(e) =>
          void form.handleSubmit((values) => loginMutation.mutate(values))(e)
        }
        noValidate
      >
        <TextField
          label="Work email"
          type="email"
          autoComplete="username"
          placeholder="name@company.com"
          className="h-11 rounded-[9px]"
          error={form.formState.errors.email?.message}
          {...form.register("email")}
        />
        <div className="mb-1.5 mt-1 flex items-center justify-between">
          <span className="text-body-sm font-semibold text-text-muted">
            Password
          </span>
          <span className="text-body-sm font-semibold text-accent">
            Forgot?
          </span>
        </div>
        <PasswordField
          label=""
          aria-label="Password"
          placeholder="••••••••••••"
          className="h-11 rounded-[9px]"
          error={form.formState.errors.password?.message}
          {...form.register("password")}
        />
        {loginMutation.isError ? (
          <p className="mt-2 text-body-sm text-fail-fg" role="alert">
            {messageFrom(loginMutation.error, "Sign in failed. Try again.")}
          </p>
        ) : null}
        <Button
          type="submit"
          className="mt-1 h-[46px] w-full rounded-[10px]"
          size="lg"
          loading={loginMutation.isPending}
        >
          Sign in
          <Icon name="arrowr" className="size-4" />
        </Button>
      </form>

      <div className="mt-[22px] flex items-center gap-2 rounded-[9px] border border-pass-border bg-pass-bg px-[13px] py-[11px]">
        <Icon name="shield" className="size-[15px] text-pass-fg" />
        <p className="text-body-sm font-semibold text-pass-fg">
          Protected by SSO &amp; enforced MFA · SOC 2 Type II
        </p>
      </div>

      <p className="mt-6 text-body-md text-text-muted">
        New here?{" "}
        <Link className="font-semibold text-accent" to="/sign-up">
          Start a trial
        </Link>
      </p>
    </AuthSplitLayout>
  );
}
