import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { AuthSplitLayout } from "@/features/iam/components/auth-split-layout";
import { Button, ErrorBanner, Icon, TextField } from "@/components/ui";
import { authApi } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import { useAlertFocus } from "@/features/iam/hooks/use-alert-focus";

const schema = z.object({
  email: z.string().email("Enter the email you sign in with."),
});
type Values = z.infer<typeof schema>;

export function ForgotPasswordPage() {
  const [sentTo, setSentTo] = useState<string | null>(null);
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { email: "" },
    mode: "onBlur",
  });
  const mutation = useMutation({
    mutationFn: (values: Values) => authApi.requestPasswordReset(values.email),
    onSuccess: (_data, values) => setSentTo(values.email),
  });
  const alertRef = useAlertFocus(mutation.isError);

  if (sentTo) {
    return (
      <AuthSplitLayout
        title="Check your email"
        subtitle="Follow the link to set a new password."
      >
        <div className="flex flex-col gap-4">
          <div
            className="flex items-center gap-2 rounded-md border border-status-success-border bg-status-success-bg px-3.5 py-3"
            role="status"
          >
            <Icon name="check" className="size-5 text-status-success-text" />
            <p className="text-body-md text-status-success-text">
              If an account exists for{" "}
              <span className="font-semibold">{sentTo}</span>, a reset link is on
              its way.
            </p>
          </div>
          <p className="text-body-sm text-text-secondary">
            The link expires in 45 minutes and works once. Didn&rsquo;t get it?
            Check spam, or{" "}
            <button
              type="button"
              className="font-semibold text-text-link"
              onClick={() => setSentTo(null)}
            >
              try another email
            </button>
            .
          </p>
          <Link
            className="text-body-sm font-semibold text-text-link"
            to="/sign-in"
          >
            Back to sign in
          </Link>
        </div>
      </AuthSplitLayout>
    );
  }

  return (
    <AuthSplitLayout
      title="Reset your password"
      subtitle="Enter your email and we’ll send a link to set a new one."
    >
      <form
        className="flex flex-col gap-3"
        onSubmit={(e) =>
          void form.handleSubmit((v) => mutation.mutate(v))(e)
        }
        noValidate
      >
        {mutation.isError ? (
          <ErrorBanner ref={alertRef} title="Couldn’t send the reset link">
            {mutation.error instanceof ApiError
              ? mutation.error.message
              : "The request didn’t reach the server. Check your connection and try again."}
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
        <Button
          type="submit"
          className="auth-cta mt-1 w-full rounded-full bg-gradient-to-r from-action-accent via-action-primary to-action-primary-hover"
          size="lg"
          loading={mutation.isPending}
        >
          Send reset link
          <Icon name="arrowr" className="size-4" />
        </Button>
      </form>
      <p className="mt-6 text-body-sm text-text-secondary">
        Remembered it?{" "}
        <Link className="font-semibold text-text-link" to="/sign-in">
          Sign in
        </Link>
      </p>
      <p className="mt-3 text-body-sm text-text-subtle">
        Signs in with Microsoft or Okta? Reset your password with your identity
        provider instead.
      </p>
    </AuthSplitLayout>
  );
}
