import { useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { authApi } from "@/lib/api/endpoints";
import { authSuccessDelay } from "@/features/iam/auth-motion";
import { AuthSplitLayout } from "@/features/iam/components/auth-split-layout";
import { AuthSubmitButton } from "@/features/iam/components/auth-submit-button";
import { FailureAlert } from "@/features/iam/auth-kit/auth-alert";
import { CtaLink } from "@/features/iam/auth-kit/auth-bits";
import { linkClass, secondaryPill } from "@/features/iam/auth-kit/helpers";
import { describeAuthFailure } from "@/features/iam/auth-kit/auth-errors";
import { AuthPasswordField } from "@/features/iam/auth-kit/auth-field";
import { newPasswordSchema } from "@/features/iam/auth-kit/password-rules";

const schema = z
  .object({
    password: newPasswordSchema,
    confirm: z.string().min(1, "Enter the new password again."),
  })
  .refine((v) => v.password === v.confirm, {
    path: ["confirm"],
    message: "Passwords don't match.",
  });
type Values = z.infer<typeof schema>;

export function ResetPasswordPage() {
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const [done, setDone] = useState(false);
  const [updated, setUpdated] = useState(false);
  const [shakeKey, setShakeKey] = useState(0);
  const alertRef = useRef<HTMLDivElement>(null);

  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { password: "", confirm: "" },
    mode: "onTouched",
  });
  const password = form.watch("password");
  const confirm = form.watch("confirm");

  const mutation = useMutation({
    mutationFn: (values: Values) =>
      authApi.confirmPasswordReset(token, values.password),
    onSuccess: () => {
      const delay = authSuccessDelay();
      if (!delay) {
        setDone(true);
        return;
      }
      setUpdated(true);
      window.setTimeout(() => setDone(true), delay);
    },
    onError: (error) => {
      setShakeKey((k) => k + 1);
      // Too weak or recently used: say it on the field. A dead link gets the banner.
      const failure = describeAuthFailure(error, "reset");
      if (failure.field === "password") {
        form.setError(
          "password",
          { type: "server", message: failure.title },
          { shouldFocus: true },
        );
      } else {
        window.requestAnimationFrame(() => alertRef.current?.focus());
      }
    },
  });

  if (!token) {
    return (
      <AuthSplitLayout
        mark={{ icon: "alert", tone: "warning" }}
        title="This link is incomplete"
        subtitle="Open the full link from your email, or request a new one."
      >
        <div className="flex flex-col gap-3">
          <CtaLink to="/forgot-password">Request a new link</CtaLink>
          <Link to="/sign-in" className={secondaryPill}>
            Back to sign in
          </Link>
        </div>
      </AuthSplitLayout>
    );
  }

  if (done) {
    return (
      <AuthSplitLayout
        mark={{ icon: "check", tone: "success" }}
        title="Password updated"
        subtitle="Other sessions were signed out. Sign in with your new password."
      >
        <CtaLink
          to="/sign-in"
          replace
          state={{
            notice: "Password updated. Sign in with your new password.",
          }}
        >
          Continue to sign in
        </CtaLink>
      </AuthSplitLayout>
    );
  }

  const failure = mutation.isError
    ? describeAuthFailure(mutation.error, "reset")
    : null;
  const bannerFailure = failure && !failure.field ? failure : null;
  const submit = form.handleSubmit(
    (values) => mutation.mutate(values),
    () => setShakeKey((k) => k + 1),
  );
  const clearFailure = () => {
    if (mutation.isError) mutation.reset();
  };

  return (
    <AuthSplitLayout
      mark={{ icon: "key" }}
      title="Set a new password"
      subtitle="Choose one you don't use anywhere else."
    >
      <form
        className="flex flex-col gap-4"
        noValidate
        onSubmit={(e) => void submit(e)}
      >
        {bannerFailure ? (
          <FailureAlert
            ref={alertRef}
            failure={bannerFailure}
            onRetry={() => void submit()}
            action={
              bannerFailure.kind === "rejected" ? (
                <Link className={linkClass} to="/forgot-password">
                  Request a new link
                </Link>
              ) : undefined
            }
          />
        ) : null}
        <AuthPasswordField
          label="New password"
          autoComplete="new-password"
          autoFocus
          rules
          typed={password}
          error={form.formState.errors.password?.message}
          {...form.register("password", { onChange: clearFailure })}
        />
        <AuthPasswordField
          label="Confirm new password"
          autoComplete="new-password"
          valid={
            Boolean(confirm) &&
            confirm === password &&
            !form.formState.errors.confirm
          }
          error={form.formState.errors.confirm?.message}
          {...form.register("confirm", { onChange: clearFailure })}
        />
        <AuthSubmitButton
          label="Update password"
          steps={["Updating your password", "Signing out other sessions"]}
          successLabel="Password updated"
          phase={updated ? "success" : mutation.isPending ? "loading" : "idle"}
          shakeKey={shakeKey}
        />
      </form>
    </AuthSplitLayout>
  );
}
