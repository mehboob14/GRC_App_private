import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { AuthSplitLayout } from "@/features/iam/components/auth-split-layout";
import { CheckEmailPanel } from "@/features/iam/components/check-email-panel";
import {
  Button,
  Checkbox,
  ErrorBanner,
  Icon,
  PasswordField,
  TextField,
} from "@/components/ui";
import { authApi } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-context";
import { useAlertFocus } from "@/features/iam/hooks/use-alert-focus";

const schema = z.object({
  company_name: z.string().min(2, "Enter your company name."),
  full_name: z.string().min(2, "Enter your full name."),
  email: z.string().email("Enter a work email."),
  password: z.string().min(10, "Use at least 10 characters."),
  accept_terms: z.boolean().refine((v) => v, {
    message: "Please accept the terms to continue.",
  }),
});

type FormValues = z.infer<typeof schema>;

export function SignUpPage() {
  const navigate = useNavigate();
  const { applyLogin } = useAuth();
  // Set once signup succeeds — the address we told the backend to verify.
  const [sentTo, setSentTo] = useState<string | null>(null);

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      company_name: "",
      full_name: "",
      email: "",
      password: "",
      accept_terms: false,
    },
    mode: "onBlur",
  });

  const signupMutation = useMutation({
    mutationFn: (values: FormValues) => authApi.signup(values),
    onSuccess: (response) => {
      if (response.status === "email_verification_required") {
        setSentTo(response.email);
        return;
      }
      // Defensive: the verify-first contract no longer returns these on signup,
      // but the union still allows them — route rather than dead-end.
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
    },
  });

  const alertRef = useAlertFocus(signupMutation.isError);

  if (sentTo) {
    return (
      <AuthSplitLayout
        title="Check your email"
        subtitle="Confirm your address to finish setting up your workspace."
      >
        <CheckEmailPanel email={sentTo} password={form.getValues("password")} />
      </AuthSplitLayout>
    );
  }

  return (
    <AuthSplitLayout
      title="Start your trial"
      subtitle="Start setting up your GRC workspace"
    >
      <form
        className="flex flex-col gap-3"
        onSubmit={(e) =>
          void form.handleSubmit((values) => signupMutation.mutate(values))(e)
        }
        noValidate
      >
        {signupMutation.isError ? (
          <ErrorBanner ref={alertRef} title="Couldn't create the workspace">
            {signupMutation.error instanceof ApiError
              ? signupMutation.error.message
              : "The request didn't reach the server. Check your connection and try again."}
          </ErrorBanner>
        ) : null}
        <TextField
          label="Company name"
          size="lg"
          placeholder="Acme Inc."
          error={form.formState.errors.company_name?.message}
          {...form.register("company_name")}
        />
        <TextField
          label="Your full name"
          size="lg"
          placeholder="Jordan Lee"
          error={form.formState.errors.full_name?.message}
          {...form.register("full_name")}
        />
        <TextField
          label="Work email"
          size="lg"
          type="email"
          autoComplete="username"
          placeholder="name@company.com"
          error={form.formState.errors.email?.message}
          {...form.register("email")}
        />
        <PasswordField
          label="Password"
          size="lg"
          autoComplete="new-password"
          placeholder="At least 10 characters"
          error={form.formState.errors.password?.message}
          {...form.register("password")}
        />

        <Controller
          control={form.control}
          name="accept_terms"
          render={({ field }) => (
            <div className="mt-1 flex flex-col gap-1.5">
              <label className="flex items-start gap-2 text-body-md text-text-primary">
                <Checkbox
                  id="accept_terms"
                  checked={field.value}
                  onCheckedChange={field.onChange}
                  className="mt-0.5"
                />
                I agree to the Terms &amp; Privacy Policy
              </label>
              {form.formState.errors.accept_terms?.message ? (
                <p className="flex items-start gap-1 text-body-sm text-status-danger-text">
                  <Icon name="alert" className="mt-px size-3.5 shrink-0" />
                  {form.formState.errors.accept_terms.message}
                </p>
              ) : null}
            </div>
          )}
        />

        <Button
          type="submit"
          className="auth-cta mt-1 w-full rounded-full bg-gradient-to-r from-action-accent via-action-primary to-action-primary-hover"
          size="lg"
          loading={signupMutation.isPending}
        >
          Create workspace
          <Icon name="arrowr" className="size-4" />
        </Button>
      </form>
      <p className="mt-6 text-body-sm text-text-secondary">
        Already have an account?{" "}
        <Link className="font-semibold text-text-link" to="/sign-in">
          Sign in
        </Link>
      </p>
    </AuthSplitLayout>
  );
}
