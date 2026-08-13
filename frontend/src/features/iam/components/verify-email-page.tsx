import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { AuthSplitLayout } from "@/features/iam/components/auth-split-layout";
import { CheckEmailPanel } from "@/features/iam/components/check-email-panel";
import { Button, ErrorBanner, Icon, TextField } from "@/components/ui";
import { authApi } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-context";
import { resumePendingAuth } from "@/lib/auth/resume-auth";
import { useAlertFocus } from "@/features/iam/hooks/use-alert-focus";

const resendSchema = z.object({
  email: z.string().email("Enter the email you signed up with."),
});

type ResendValues = z.infer<typeof resendSchema>;

function messageFrom(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback;
}

export function VerifyEmailPage() {
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const navigate = useNavigate();
  const { applyLogin, signOut } = useAuth();
  // Set once a resend from the error path succeeds — hands off to CheckEmailPanel.
  const [resentTo, setResentTo] = useState<string | null>(null);

  // Redeem the token exactly once: a single-use, short-lived credential must
  // never refetch or retry. TanStack Query owns the request state — no
  // useEffect+fetch here.
  const verifyQuery = useQuery({
    queryKey: ["verify-email", token],
    queryFn: () => authApi.verifyEmail(token),
    enabled: token.length > 0,
    staleTime: Infinity,
    retry: false,
  });

  const resendForm = useForm<ResendValues>({
    resolver: zodResolver(resendSchema),
    defaultValues: { email: "" },
    mode: "onBlur",
  });

  const resendMutation = useMutation({
    mutationFn: (values: ResendValues) =>
      authApi.resendVerification(values.email),
    onSuccess: (_data, values) => setResentTo(values.email),
  });

  const data = verifyQuery.data;

  // Route the terminal branches by the SAME logic login/switch use. This side
  // effect reacts to already-fetched query data; it does not fetch.
  useEffect(() => {
    if (!data) return;
    if (data.status === "authenticated") {
      applyLogin(data);
      navigate("/quick-start", { replace: true });
      return;
    }
    if (data.status === "mfa_enrollment_required") {
      navigate(`/mfa/enroll?challenge=${data.challenge_token}`, {
        replace: true,
      });
      return;
    }
    if (data.status === "mfa_required" || data.status === "select_workspace") {
      // Both resume on the sign-in surface behind PublicOnly — drop any session
      // first (signOut also resets in-memory auth) or that gate bounces us back.
      signOut();
      resumePendingAuth(data, navigate);
    }
    // email_verification_required is handled in render (shouldn't reach here).
  }, [data, applyLogin, navigate, signOut]);

  const verifyAlertRef = useAlertFocus(verifyQuery.isError);
  const resendAlertRef = useAlertFocus(resendMutation.isError);

  // A resend succeeded from the error path — show the standard check-email body.
  if (resentTo) {
    return (
      <AuthSplitLayout
        title="Check your email"
        subtitle="Confirm your address to finish setting up your workspace."
      >
        <CheckEmailPanel email={resentTo} />
      </AuthSplitLayout>
    );
  }

  if (!token) {
    return (
      <AuthSplitLayout
        title="Verify your email"
        subtitle="This link is missing its token. Open the full link from your email, or sign in to request a new one."
      >
        <Link className="font-semibold text-text-link" to="/sign-in">
          Back to sign in
        </Link>
      </AuthSplitLayout>
    );
  }

  if (verifyQuery.isError) {
    return (
      <AuthSplitLayout
        title="Verify your email"
        subtitle="We couldn't confirm this link. Enter your email and we'll send a fresh one."
      >
        <ErrorBanner
          ref={verifyAlertRef}
          className="mb-4"
          title="This link is invalid or has expired."
        >
          Enter the email you signed up with to get a new verification link.
        </ErrorBanner>
        <form
          className="flex flex-col gap-3"
          onSubmit={(e) =>
            void resendForm.handleSubmit((values) =>
              resendMutation.mutate(values),
            )(e)
          }
          noValidate
        >
          {resendMutation.isError ? (
            <ErrorBanner ref={resendAlertRef} title="Couldn't send the email">
              {messageFrom(
                resendMutation.error,
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
            error={resendForm.formState.errors.email?.message}
            {...resendForm.register("email")}
          />
          <Button
            type="submit"
            className="mt-1 w-full"
            size="lg"
            loading={resendMutation.isPending}
          >
            Send a new link
            <Icon name="arrowr" className="size-4" />
          </Button>
        </form>
        <p className="mt-6 text-body-sm text-text-secondary">
          Already verified?{" "}
          <Link className="font-semibold text-text-link" to="/sign-in">
            Sign in
          </Link>
        </p>
      </AuthSplitLayout>
    );
  }

  if (data?.status === "email_verification_required") {
    return (
      <AuthSplitLayout
        title="Check your email"
        subtitle="Confirm your address to finish setting up your workspace."
      >
        <CheckEmailPanel email={data.email} />
      </AuthSplitLayout>
    );
  }

  // Verifying, or a terminal status whose effect is navigating away.
  return (
    <AuthSplitLayout
      title="Verifying your email"
      subtitle="One moment while we confirm your link and set up your session."
    >
      <div
        className="flex items-center gap-3 text-body-md text-text-secondary"
        role="status"
      >
        <Icon name="spinner" className="size-5 animate-spin text-action-accent" />
        Verifying…
      </div>
    </AuthSplitLayout>
  );
}
