import { Link, useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { AuthSplitLayout } from "@/features/iam/components/auth-split-layout";
import {
  Button,
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
});

type FormValues = z.infer<typeof schema>;

export function SignUpPage() {
  const navigate = useNavigate();
  const { applyLogin } = useAuth();

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      company_name: "",
      full_name: "",
      email: "",
      password: "",
    },
    mode: "onBlur",
  });

  const signupMutation = useMutation({
    mutationFn: (values: FormValues) => authApi.signup(values),
    onSuccess: (response) => {
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

  return (
    <AuthSplitLayout
      title="Start your trial"
      subtitle="Create a workspace. You’ll enroll MFA as the first Admin."
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
              : "The request didn't reach the server — check your connection and try again."}
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
        <Button
          type="submit"
          className="mt-1 w-full"
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
