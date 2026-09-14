import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Icon } from "@/components/ui";
import { authApi } from "@/lib/api/endpoints";
import { announceEmailVerified } from "@/lib/auth/verify-signal";
import { AuthSplitLayout } from "@/features/iam/components/auth-split-layout";
import { AuthSubmitButton } from "@/features/iam/components/auth-submit-button";
import { CheckEmailPanel } from "@/features/iam/components/check-email-panel";
import { FailureAlert } from "@/features/iam/auth-kit/auth-alert";
import { EmailSuggestion } from "@/features/iam/auth-kit/auth-bits";
import { linkClass, secondaryPill } from "@/features/iam/auth-kit/helpers";
import { describeAuthFailure } from "@/features/iam/auth-kit/auth-errors";
import { AuthField } from "@/features/iam/auth-kit/auth-field";

const resendSchema = z.object({
  email: z
    .string()
    .trim()
    .min(1, "Enter the email you signed up with.")
    .email("Enter a valid email, like name@company.com."),
});

type ResendValues = z.infer<typeof resendSchema>;

export function VerifyEmailPage() {
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const [shakeKey, setShakeKey] = useState(0);

  // Redeem the token exactly once: a single use, short lived credential must
  // never refetch or retry on its own. A network failure offers a manual retry.
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
    mode: "onTouched",
  });
  const email = resendForm.watch("email");
  const resendMutation = useMutation({
    mutationFn: (values: ResendValues) =>
      authApi.resendVerification(values.email),
    onError: () => setShakeKey((k) => k + 1),
  });

  // Verified: this tab does not enter the app. It tells the sign up tab (which
  // holds the credentials) to continue, and shows a done state to close.
  useEffect(() => {
    if (verifyQuery.isSuccess) announceEmailVerified();
  }, [verifyQuery.isSuccess]);

  if (!token) {
    return (
      <AuthSplitLayout
        mark={{ icon: "alert", tone: "warning" }}
        title="This link is incomplete"
        subtitle="Open the full link from your email, or sign in to get a new one."
      >
        <Link to="/sign-in" className={secondaryPill}>
          Back to sign in
        </Link>
      </AuthSplitLayout>
    );
  }

  if (verifyQuery.isSuccess) {
    return (
      <AuthSplitLayout
        mark={{ icon: "check", tone: "success" }}
        title="Email verified"
        subtitle="Go back to the tab where you signed up. It continues on its own."
      >
        <div className="flex flex-col gap-3">
          <Link to="/sign-in" className={secondaryPill}>
            Sign in on this tab instead
          </Link>
        </div>
      </AuthSplitLayout>
    );
  }

  if (verifyQuery.isError) {
    const failure = describeAuthFailure(verifyQuery.error, "verify");

    if (resendMutation.isSuccess) {
      return (
        <AuthSplitLayout
          mark={{ icon: "mail" }}
          title="Check your inbox"
          subtitle="A fresh verification link is on its way."
        >
          <CheckEmailPanel
            email={resendForm.getValues("email")}
            onChangeEmail={() => resendMutation.reset()}
          />
        </AuthSplitLayout>
      );
    }

    // A dropped connection is not a dead link: offer the retry, not a new email.
    if (failure.retryable) {
      return (
        <AuthSplitLayout
          mark={{ icon: "wifiOff", tone: "warning" }}
          title="We couldn't check your link"
          subtitle="Your link may still be fine."
        >
          <div className="flex flex-col gap-4">
            <FailureAlert failure={failure} />
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void verifyQuery.refetch();
              }}
            >
              <AuthSubmitButton
                label="Try again"
                steps={["Checking your link"]}
                successLabel="Email verified"
                phase={verifyQuery.isFetching ? "loading" : "idle"}
              />
            </form>
          </div>
        </AuthSplitLayout>
      );
    }

    const resendFailure = resendMutation.isError
      ? describeAuthFailure(resendMutation.error, "verify")
      : null;
    const submit = resendForm.handleSubmit(
      (values) => resendMutation.mutate(values),
      () => setShakeKey((k) => k + 1),
    );

    return (
      <AuthSplitLayout
        mark={{ icon: "countdown", tone: "warning" }}
        title="This link no longer works"
        subtitle="Links expire and work once. Get a fresh one below."
      >
        <form
          className="flex flex-col gap-4"
          noValidate
          onSubmit={(e) => void submit(e)}
        >
          {resendFailure ? (
            <FailureAlert
              failure={resendFailure}
              onRetry={() => void submit()}
            />
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
            error={resendForm.formState.errors.email?.message}
            below={
              resendForm.formState.errors.email ? null : (
                <EmailSuggestion
                  email={email}
                  onAccept={(value) =>
                    resendForm.setValue("email", value, {
                      shouldValidate: true,
                    })
                  }
                />
              )
            }
            {...resendForm.register("email", {
              onChange: () => {
                if (resendMutation.isError) resendMutation.reset();
              },
            })}
          />
          <AuthSubmitButton
            label="Send a new link"
            steps={["Sending a new link"]}
            successLabel="Link sent"
            phase={resendMutation.isPending ? "loading" : "idle"}
            shakeKey={shakeKey}
          />
        </form>
        <p className="mt-7 text-center text-body-md text-text-secondary">
          Already verified?{" "}
          <Link className={linkClass} to="/sign-in">
            Sign in
          </Link>
        </p>
      </AuthSplitLayout>
    );
  }

  return (
    <AuthSplitLayout
      mark={{ icon: "mail" }}
      title="Verifying your email"
      subtitle="One moment while we confirm your link."
    >
      <p
        role="status"
        className="flex items-center justify-center gap-2.5 text-body-md text-text-secondary"
      >
        <Icon
          name="spinner"
          className="size-5 animate-spin text-action-accent"
        />
        Checking your link
      </p>
    </AuthSplitLayout>
  );
}
