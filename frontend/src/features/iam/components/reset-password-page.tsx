import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { AuthSplitLayout } from "@/features/iam/components/auth-split-layout";
import { Button, ErrorBanner, Icon, PasswordField } from "@/components/ui";
import { authApi } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import { useAlertFocus } from "@/features/iam/hooks/use-alert-focus";

const schema = z
  .object({
    password: z.string().min(10, "Use at least 10 characters."),
    confirm: z.string(),
  })
  .refine((v) => v.password === v.confirm, {
    path: ["confirm"],
    message: "Passwords don’t match.",
  });
type Values = z.infer<typeof schema>;

export function ResetPasswordPage() {
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const [done, setDone] = useState(false);

  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { password: "", confirm: "" },
    mode: "onBlur",
  });
  const mutation = useMutation({
    mutationFn: (values: Values) =>
      authApi.confirmPasswordReset(token, values.password),
    onSuccess: () => setDone(true),
  });
  const alertRef = useAlertFocus(mutation.isError);

  if (!token) {
    return (
      <AuthSplitLayout
        title="Reset your password"
        subtitle="This link is missing its token."
      >
        <p className="text-body-md text-text-secondary">
          Open the full link from your email, or{" "}
          <Link className="font-semibold text-text-link" to="/forgot-password">
            request a new one
          </Link>
          .
        </p>
      </AuthSplitLayout>
    );
  }

  if (done) {
    return (
      <AuthSplitLayout title="Password updated" subtitle="You’re all set.">
        <div className="flex flex-col gap-4">
          <div
            className="flex items-center gap-2 rounded-md border border-status-success-border bg-status-success-bg px-3.5 py-3"
            role="status"
          >
            <Icon name="check" className="size-5 text-status-success-text" />
            <p className="text-body-md text-status-success-text">
              Your password was changed and any other sessions were signed out.
            </p>
          </div>
          <Link
            className="text-body-sm font-semibold text-text-link"
            to="/sign-in"
          >
            Continue to sign in
          </Link>
        </div>
      </AuthSplitLayout>
    );
  }

  return (
    <AuthSplitLayout
      title="Set a new password"
      subtitle="Choose a strong password you don’t use anywhere else."
    >
      <form
        className="flex flex-col gap-3"
        onSubmit={(e) =>
          void form.handleSubmit((v) => mutation.mutate(v))(e)
        }
        noValidate
      >
        {mutation.isError ? (
          <ErrorBanner ref={alertRef} title="Couldn’t reset your password">
            {mutation.error instanceof ApiError
              ? mutation.error.message
              : "The request didn’t reach the server. Check your connection and try again."}{" "}
            <Link className="font-semibold underline" to="/forgot-password">
              Request a new link
            </Link>
            .
          </ErrorBanner>
        ) : null}
        <PasswordField
          label="New password"
          size="lg"
          autoComplete="new-password"
          placeholder="At least 10 characters"
          error={form.formState.errors.password?.message}
          {...form.register("password")}
        />
        <PasswordField
          label="Confirm new password"
          size="lg"
          autoComplete="new-password"
          placeholder="Re-enter password"
          error={form.formState.errors.confirm?.message}
          {...form.register("confirm")}
        />
        <Button
          type="submit"
          className="auth-cta mt-1 w-full rounded-full bg-gradient-to-r from-action-accent via-action-primary to-action-primary-hover"
          size="lg"
          loading={mutation.isPending}
        >
          Update password
          <Icon name="arrowr" className="size-4" />
        </Button>
      </form>
    </AuthSplitLayout>
  );
}
