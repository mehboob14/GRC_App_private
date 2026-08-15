import { useEffect } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { AuthSplitLayout } from "@/features/iam/components/auth-split-layout";
import { CheckEmailPanel } from "@/features/iam/components/check-email-panel";
import { Button, ErrorBanner, Icon, TextField } from "@/components/ui";
import { authApi } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import { announceEmailVerified } from "@/lib/auth/verify-signal";
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

  // Redeem the token exactly once: a single-use, short-lived credential must
  // never refetch or retry. TanStack Query owns the request state.
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
  });

  // Verified: this tab does NOT enter the app. It tells the sign-up tab (which
  // holds the credentials) to continue, and shows a done state to close.
  useEffect(() => {
    if (verifyQuery.isSuccess) announceEmailVerified();
  }, [verifyQuery.isSuccess]);

  const verifyAlertRef = useAlertFocus(verifyQuery.isError);
  const resendAlertRef = useAlertFocus(resendMutation.isError);

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

  if (verifyQuery.isSuccess) {
    return (
      <AuthSplitLayout
        title="Email verified"
        subtitle="You're all set."
      >
        <div className="flex flex-col gap-4">
          <div
            className="flex items-center gap-2 rounded-md border border-status-success-border bg-status-success-bg px-3.5 py-3"
            role="status"
          >
            <Icon name="check" className="size-5 text-status-success-text" />
            <p className="text-body-md font-semibold text-status-success-text">
              Your email is verified.
            </p>
          </div>
          <p className="text-body-md text-text-secondary">
            You can close this tab and return to the window where you signed up —
            it continues automatically. Or{" "}
            <Link className="font-semibold text-text-link" to="/sign-in">
              sign in here
            </Link>
            .
          </p>
        </div>
      </AuthSplitLayout>
    );
  }

  if (verifyQuery.isError) {
    if (resendMutation.isSuccess) {
      return (
        <AuthSplitLayout
          title="Check your email"
          subtitle="Confirm your address to finish setting up your workspace."
        >
          <CheckEmailPanel email={resendForm.getValues("email")} />
        </AuthSplitLayout>
      );
    }
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
      </AuthSplitLayout>
    );
  }

  return (
    <AuthSplitLayout
      title="Verifying your email"
      subtitle="One moment while we confirm your link."
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
