import { useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Checkbox, Icon } from "@/components/ui";
import { cn } from "@/lib/cn";
import { authApi } from "@/lib/api/endpoints";
import { useAuth } from "@/lib/auth/auth-context";
import { authSuccessDelay } from "@/features/iam/auth-motion";
import { AuthSplitLayout } from "@/features/iam/components/auth-split-layout";
import { AuthSubmitButton } from "@/features/iam/components/auth-submit-button";
import { CheckEmailPanel } from "@/features/iam/components/check-email-panel";
import { FailureAlert } from "@/features/iam/auth-kit/auth-alert";
import { EmailSuggestion } from "@/features/iam/auth-kit/auth-bits";
import { linkClass } from "@/features/iam/auth-kit/helpers";
import { describeAuthFailure } from "@/features/iam/auth-kit/auth-errors";
import {
  AuthField,
  AuthPasswordField,
} from "@/features/iam/auth-kit/auth-field";
import { newPasswordSchema } from "@/features/iam/auth-kit/password-rules";

const schema = z.object({
  full_name: z.string().trim().min(2, "Enter your full name."),
  company_name: z.string().trim().min(2, "Enter your company name."),
  email: z
    .string()
    .trim()
    .min(1, "Enter your work email.")
    .email("Enter a valid email, like name@company.com."),
  password: newPasswordSchema,
  accept_terms: z
    .boolean()
    .refine((v) => v, { message: "Accept the terms to continue." }),
});

type FormValues = z.infer<typeof schema>;

export function SignUpPage() {
  const navigate = useNavigate();
  const { applyLogin } = useAuth();
  // Set once signup succeeds: the address the backend is verifying.
  const [sentTo, setSentTo] = useState<string | null>(null);
  const [created, setCreated] = useState(false);
  const [shakeKey, setShakeKey] = useState(0);
  const alertRef = useRef<HTMLDivElement>(null);

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      full_name: "",
      company_name: "",
      email: "",
      password: "",
      accept_terms: false,
    },
    mode: "onTouched",
  });
  const { errors, touchedFields } = form.formState;
  const email = form.watch("email");
  const password = form.watch("password");
  const shake = () => setShakeKey((k) => k + 1);

  const signupMutation = useMutation({
    mutationFn: (values: FormValues) => authApi.signup(values),
    onSuccess: (response) => {
      // The workspace exists once this resolves: the button says so, then the page moves on.
      const delay = authSuccessDelay();
      if (!delay) {
        proceed(response);
        return;
      }
      setCreated(true);
      window.setTimeout(() => proceed(response), delay);
    },
    onError: (error) => {
      shake();
      // A taken email or a refused password belongs on its field, not in a banner.
      const failure = describeAuthFailure(error, "signup");
      if (failure.field === "email" || failure.field === "password") {
        form.setError(
          failure.field,
          { type: "server", message: failure.title },
          { shouldFocus: true },
        );
      } else {
        window.requestAnimationFrame(() => alertRef.current?.focus());
      }
    },
  });

  function proceed(response: Awaited<ReturnType<typeof authApi.signup>>) {
    if (response.status === "email_verification_required") {
      setSentTo(response.email);
      return;
    }
    // Defensive: the verify first contract no longer returns these on signup,
    // but the union still allows them, so route rather than dead end.
    if (response.status === "mfa_enrollment_required") {
      navigate(`/mfa/enroll?challenge=${response.challenge_token}`, {
        replace: true,
      });
      return;
    }
    if (response.status === "authenticated") {
      applyLogin(response);
      navigate("/quick-start", { replace: true });
    }
  }

  if (sentTo) {
    return (
      <AuthSplitLayout
        mark={{ icon: "mail" }}
        title="Check your inbox"
        subtitle="Click the link we sent to finish setting up your workspace."
      >
        <CheckEmailPanel
          email={sentTo}
          password={form.getValues("password")}
          onChangeEmail={() => {
            setSentTo(null);
            setCreated(false);
            signupMutation.reset();
            window.requestAnimationFrame(() =>
              form.setFocus("email", { shouldSelect: true }),
            );
          }}
        />
      </AuthSplitLayout>
    );
  }

  const failure = signupMutation.isError
    ? describeAuthFailure(signupMutation.error, "signup")
    : null;
  const bannerFailure = failure && !failure.field ? failure : null;
  const emailTaken =
    failure?.kind === "emailTaken" && errors.email?.type === "server";
  const clearFailure = () => {
    if (signupMutation.isError) signupMutation.reset();
  };
  const submit = form.handleSubmit(
    (values) => signupMutation.mutate(values),
    shake,
  );
  const valid = (field: "full_name" | "company_name" | "email") =>
    Boolean(touchedFields[field]) && !errors[field];

  return (
    <AuthSplitLayout
      title="Create your workspace"
      subtitle="Set up GRC for your company in minutes."
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
          />
        ) : null}

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <AuthField
            label="Full name"
            icon="user"
            autoComplete="name"
            placeholder="Jordan Lee"
            valid={valid("full_name")}
            error={errors.full_name?.message}
            {...form.register("full_name", { onChange: clearFailure })}
          />
          <AuthField
            label="Company"
            icon="vendor"
            autoComplete="organization"
            placeholder="Acme Inc."
            valid={valid("company_name")}
            error={errors.company_name?.message}
            {...form.register("company_name", { onChange: clearFailure })}
          />
        </div>

        <AuthField
          label="Work email"
          icon="mail"
          type="email"
          inputMode="email"
          autoComplete="email"
          autoCapitalize="none"
          spellCheck={false}
          placeholder="name@company.com"
          valid={valid("email")}
          error={errors.email?.message}
          below={
            errors.email ? null : (
              <EmailSuggestion
                email={email}
                onAccept={(value) =>
                  form.setValue("email", value, { shouldValidate: true })
                }
              />
            )
          }
          hint={
            emailTaken ? (
              <Link to="/sign-in" state={{ email }} className={linkClass}>
                Sign in instead
              </Link>
            ) : undefined
          }
          {...form.register("email", { onChange: clearFailure })}
        />

        <AuthPasswordField
          label="Password"
          autoComplete="new-password"
          rules
          typed={password}
          error={errors.password?.message}
          {...form.register("password", { onChange: clearFailure })}
        />

        <Controller
          control={form.control}
          name="accept_terms"
          render={({ field }) => (
            <div className="flex flex-col">
              <label
                className={cn(
                  "flex cursor-pointer items-start gap-2.5 rounded-xl border px-3 py-2.5 text-body-md transition-colors",
                  errors.accept_terms
                    ? "border-status-danger-border bg-status-danger-bg"
                    : "border-transparent hover:bg-surface-hover",
                )}
              >
                <Checkbox
                  id="accept_terms"
                  checked={field.value}
                  onCheckedChange={(checked) => {
                    field.onChange(checked);
                    field.onBlur();
                  }}
                  className="mt-0.5"
                />
                <span className="text-text-secondary">
                  I agree to the{" "}
                  <span className="font-semibold text-text-primary">
                    Terms of Service
                  </span>{" "}
                  and{" "}
                  <span className="font-semibold text-text-primary">
                    Privacy Policy
                  </span>
                </span>
              </label>
              {errors.accept_terms?.message ? (
                <p
                  role="alert"
                  className="auth-msg-in mt-1.5 flex items-center gap-1.5 text-body-sm font-medium text-status-danger-text"
                >
                  <Icon name="alert" className="size-3.5 shrink-0" />
                  {errors.accept_terms.message}
                </p>
              ) : null}
            </div>
          )}
        />

        <AuthSubmitButton
          label="Create workspace"
          steps={[
            "Creating your workspace",
            "Adding SOC 2 controls",
            "Securing your workspace",
          ]}
          successLabel="Workspace created"
          phase={
            created ? "success" : signupMutation.isPending ? "loading" : "idle"
          }
          shakeKey={shakeKey}
        />
      </form>

      <p className="mt-7 text-center text-body-md text-text-secondary">
        Already have an account?{" "}
        <Link
          className={linkClass}
          to="/sign-in"
          state={email ? { email } : undefined}
        >
          Sign in
        </Link>
      </p>
    </AuthSplitLayout>
  );
}
