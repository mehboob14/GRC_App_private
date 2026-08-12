import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { AuthSplitLayout } from "@/features/iam/components/auth-split-layout";
import { Button, Icon, PasswordField, TextField } from "@/components/ui";
import { authApi } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-context";
import type { LoginResponse, WorkspaceSummary } from "@/lib/api/types";
import { DEMO_MFA_CODE, DEMO_PASSWORD } from "@/mocks/fixtures";

const schema = z.object({
  email: z
    .string()
    .email("Enter a work email — personal domains aren't allowed."),
  password: z.string().min(1, "Enter your password."),
});

type FormValues = z.infer<typeof schema>;

export function SignInPage() {
  const navigate = useNavigate();
  const { applyLogin } = useAuth();
  const [serverError, setServerError] = useState<string | null>(null);
  const [pending, setPending] = useState<LoginResponse | null>(null);
  const [mfaCode, setMfaCode] = useState("");
  const [busy, setBusy] = useState(false);

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      email: "alex.okafor@northwind.cloud",
      password: DEMO_PASSWORD,
    },
    mode: "onBlur",
  });

  useEffect(() => {
    if (pending?.status === "mfa_enrollment_required") {
      navigate(`/mfa/enroll?challenge=${pending.challenge_token}`, {
        replace: true,
      });
    }
  }, [pending, navigate]);

  async function finishAuth(response: LoginResponse) {
    if (response.status === "authenticated") {
      applyLogin(response);
      navigate("/quick-start", { replace: true });
      return;
    }
    setPending(response);
  }

  async function onSubmit(values: FormValues) {
    setServerError(null);
    setBusy(true);
    try {
      const response = await authApi.login(values);
      await finishAuth(response);
    } catch (error) {
      setServerError(
        error instanceof ApiError
          ? error.message
          : "Sign in failed. Try again.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function onVerifyMfa() {
    if (!pending || pending.status !== "mfa_required") return;
    setBusy(true);
    setServerError(null);
    try {
      const response = await authApi.verifyMfa({
        challenge_token: pending.challenge_token,
        code: mfaCode,
      });
      await finishAuth(response);
    } catch (error) {
      setServerError(
        error instanceof ApiError
          ? error.message
          : "That code is incorrect or expired.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function onSelectWorkspace(ws: WorkspaceSummary) {
    if (!pending || pending.status !== "select_workspace") return;
    setBusy(true);
    setServerError(null);
    try {
      const response = await authApi.selectWorkspace(
        pending.selection_token,
        ws.membership_id,
      );
      await finishAuth(response);
    } catch (error) {
      setServerError(
        error instanceof ApiError ? error.message : "Could not open workspace.",
      );
    } finally {
      setBusy(false);
    }
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
              disabled={busy}
              onClick={() => void onSelectWorkspace(ws)}
              className="flex h-[52px] items-center gap-3 rounded-[10px] border border-border px-3 text-left hover:bg-bg-sunken"
            >
              <span className="flex size-9 items-center justify-center rounded-lg bg-accent font-display text-[13px] font-bold text-accent-fg">
                {ws.tenant_name.slice(0, 1)}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-[14px] font-semibold text-text">
                  {ws.tenant_name}
                </span>
                <span className="block text-[12px] text-text-faint">
                  {ws.role_name}
                </span>
              </span>
              <Icon name="chevr" className="size-4 text-text-faint" />
            </button>
          ))}
        </div>
        {serverError ? (
          <p className="mt-3 text-[12px] text-fail-fg" role="alert">
            {serverError}
          </p>
        ) : null}
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
          placeholder="123456"
          value={mfaCode}
          onChange={(e) =>
            setMfaCode(e.target.value.replace(/\D/g, "").slice(0, 6))
          }
          hint={`Demo code: ${DEMO_MFA_CODE}`}
        />
        {serverError ? (
          <p className="mt-2 text-[12px] text-fail-fg" role="alert">
            {serverError}
          </p>
        ) : null}
        <Button
          className="mt-4 h-[46px] w-full rounded-[10px]"
          size="lg"
          loading={busy}
          onClick={() => void onVerifyMfa()}
        >
          Verify and continue
          <Icon name="arrowr" className="size-4" />
        </Button>
        <button
          type="button"
          className="mt-4 text-[13px] text-accent"
          onClick={() => setPending(null)}
        >
          Back to sign in
        </button>
      </AuthSplitLayout>
    );
  }

  return (
    <AuthSplitLayout
      title="Welcome back"
      subtitle="Sign in to the Northwind Cloud compliance workspace."
    >
      <Button
        type="button"
        variant="secondary"
        size="lg"
        className="h-[46px] w-full rounded-[10px] border-border-strong font-semibold"
        disabled
        aria-disabled
        title="Coming soon — federation is Phase 3"
      >
        <span className="flex size-5 items-center justify-center rounded-[5px] bg-[#0a6dd8] text-[12px] font-medium text-white">
          OK
        </span>
        Continue with Okta SSO
      </Button>

      <div className="my-[18px] flex items-center gap-3">
        <span className="h-px flex-1 bg-border" />
        <span className="text-[12px] font-medium text-text-faint">
          or sign in with email
        </span>
        <span className="h-px flex-1 bg-border" />
      </div>

      <form
        className="flex flex-col"
        onSubmit={(e) => void form.handleSubmit(onSubmit)(e)}
        noValidate
      >
        <TextField
          label="Work email"
          type="email"
          autoComplete="username"
          placeholder="you@company.com"
          className="h-11 rounded-[9px]"
          error={form.formState.errors.email?.message}
          {...form.register("email")}
        />
        <div className="mb-1.5 mt-1 flex items-center justify-between">
          <span className="text-[12px] font-semibold text-text-muted">
            Password
          </span>
          <span className="text-[12px] font-semibold text-accent">Forgot?</span>
        </div>
        <PasswordField
          label=""
          aria-label="Password"
          placeholder="••••••••••••"
          className="h-11 rounded-[9px]"
          error={form.formState.errors.password?.message}
          {...form.register("password")}
        />
        {serverError ? (
          <p className="mt-2 text-[12px] text-fail-fg" role="alert">
            {serverError}
          </p>
        ) : null}
        <Button
          type="submit"
          className="mt-1 h-[46px] w-full rounded-[10px]"
          size="lg"
          loading={busy}
        >
          Sign in
          <Icon name="arrowr" className="size-4" />
        </Button>
      </form>

      <div className="mt-[22px] flex items-center gap-2 rounded-[9px] border border-[#c7e9d9] bg-pass-bg px-[13px] py-[11px]">
        <Icon name="shield" className="size-[15px] text-pass-fg" />
        <p className="text-[12px] font-semibold text-pass-fg">
          Protected by SSO &amp; enforced MFA · SOC 2 Type II
        </p>
      </div>

      <p className="mt-6 text-[13px] text-text-muted">
        New here?{" "}
        <Link className="font-semibold text-accent" to="/sign-up">
          Start a trial
        </Link>
      </p>
    </AuthSplitLayout>
  );
}
