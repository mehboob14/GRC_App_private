import { useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { authApi } from "@/lib/api/endpoints";
import { authSuccessDelay } from "@/features/iam/auth-motion";
import { AuthSplitLayout } from "@/features/iam/components/auth-split-layout";
import { AuthSubmitButton } from "@/features/iam/components/auth-submit-button";
import { AuthAlert, FailureAlert } from "@/features/iam/auth-kit/auth-alert";
import {
  EmailSuggestion,
  SentTo,
  WebmailLinks,
} from "@/features/iam/auth-kit/auth-bits";
import {
  linkClass,
  secondaryPill,
  useCooldown,
} from "@/features/iam/auth-kit/helpers";
import { describeAuthFailure } from "@/features/iam/auth-kit/auth-errors";
import { AuthField } from "@/features/iam/auth-kit/auth-field";

const schema = z.object({
  email: z
    .string()
    .trim()
    .min(1, "Enter your work email.")
    .email("Enter a valid email, like name@company.com."),
});
type Values = z.infer<typeof schema>;

export function ForgotPasswordPage() {
  const location = useLocation();
  const prefill = (location.state as { email?: string } | null)?.email ?? "";
  const [sentTo, setSentTo] = useState<string | null>(null);
  const [sent, setSent] = useState(false);
  const [resent, setResent] = useState(false);
  const [shakeKey, setShakeKey] = useState(0);
  const alertRef = useRef<HTMLDivElement>(null);
  const cooldown = useCooldown();

  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { email: prefill },
    mode: "onTouched",
  });
  const email = form.watch("email");

  const mutation = useMutation({
    mutationFn: (values: Values) => authApi.requestPasswordReset(values.email),
    onSuccess: (_data, values) => {
      cooldown.start(30);
      if (sentTo) {
        // A resend from the sent screen stays put and says so.
        setResent(true);
        return;
      }
      const delay = authSuccessDelay();
      if (!delay) {
        setSentTo(values.email);
        return;
      }
      setSent(true);
      window.setTimeout(() => setSentTo(values.email), delay);
    },
    onError: () => {
      setShakeKey((k) => k + 1);
      window.requestAnimationFrame(() => alertRef.current?.focus());
    },
  });
  const failure = mutation.isError
    ? describeAuthFailure(mutation.error, "forgot")
    : null;

  if (sentTo) {
    return (
      <AuthSplitLayout
        mark={{ icon: "mail" }}
        title="Check your inbox"
        subtitle="If an account uses this email, a reset link is on its way."
      >
        <div className="flex flex-col gap-4">
          <SentTo
            email={sentTo}
            onChange={() => {
              setSentTo(null);
              setSent(false);
              setResent(false);
              mutation.reset();
              window.requestAnimationFrame(() =>
                form.setFocus("email", { shouldSelect: true }),
              );
            }}
          />
          {failure ? (
            <FailureAlert
              ref={alertRef}
              failure={failure}
              onRetry={() => mutation.mutate({ email: sentTo })}
            />
          ) : null}
          {resent && cooldown.left > 0 ? (
            <AuthAlert tone="success" title="A new link is on its way" />
          ) : null}
          <WebmailLinks email={sentTo} />
          <p className="text-center text-body-sm text-text-subtle">
            The link works once and expires in 45 minutes. No email? Check spam,
            or{" "}
            {cooldown.left > 0 ? (
              <span className="font-semibold tabular-nums text-text-secondary">
                resend in {cooldown.left}s
              </span>
            ) : (
              <button
                type="button"
                className={linkClass}
                disabled={mutation.isPending}
                onClick={() => mutation.mutate({ email: sentTo })}
              >
                {mutation.isPending ? "sending" : "send it again"}
              </button>
            )}
          </p>
          <Link
            to="/sign-in"
            state={{ email: sentTo }}
            className={secondaryPill}
          >
            Back to sign in
          </Link>
        </div>
      </AuthSplitLayout>
    );
  }

  const submit = form.handleSubmit(
    (values) => mutation.mutate(values),
    () => setShakeKey((k) => k + 1),
  );

  return (
    <AuthSplitLayout
      mark={{ icon: "key" }}
      title="Reset your password"
      subtitle="Enter your email and we'll send you a link to set a new one."
    >
      <form
        className="flex flex-col gap-4"
        noValidate
        onSubmit={(e) => void submit(e)}
      >
        {failure ? (
          <FailureAlert
            ref={alertRef}
            failure={failure}
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
          autoFocus={!prefill}
          error={form.formState.errors.email?.message}
          below={
            form.formState.errors.email ? null : (
              <EmailSuggestion
                email={email}
                onAccept={(value) =>
                  form.setValue("email", value, { shouldValidate: true })
                }
              />
            )
          }
          {...form.register("email", {
            onChange: () => {
              if (mutation.isError) mutation.reset();
            },
          })}
        />
        <AuthSubmitButton
          label="Send reset link"
          steps={["Sending your reset link"]}
          successLabel="Link sent"
          phase={sent ? "success" : mutation.isPending ? "loading" : "idle"}
          shakeKey={shakeKey}
        />
      </form>
      <p className="mt-7 text-center text-body-md text-text-secondary">
        Remembered it?{" "}
        <Link
          className={linkClass}
          to="/sign-in"
          state={email ? { email } : undefined}
        >
          Back to sign in
        </Link>
      </p>
    </AuthSplitLayout>
  );
}
