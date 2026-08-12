import { Link, useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { AuthSplitLayout } from "@/features/iam/components/auth-split-layout";
import { Button, Icon, PasswordField, TextField } from "@/components/ui";
import { authApi } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-context";

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

  return (
    <AuthSplitLayout
      title="Start your trial"
      subtitle="Create a workspace. You’ll enroll MFA as the first Admin."
    >
      <form
        className="flex flex-col gap-1"
        onSubmit={(e) =>
          void form.handleSubmit((values) => signupMutation.mutate(values))(e)
        }
        noValidate
      >
        <TextField
          label="Company name"
          placeholder="Acme Inc."
          error={form.formState.errors.company_name?.message}
          {...form.register("company_name")}
        />
        <TextField
          label="Your full name"
          placeholder="Jordan Lee"
          error={form.formState.errors.full_name?.message}
          {...form.register("full_name")}
        />
        <TextField
          label="Work email"
          type="email"
          autoComplete="username"
          placeholder="name@company.com"
          error={form.formState.errors.email?.message}
          {...form.register("email")}
        />
        <PasswordField
          label="Password"
          autoComplete="new-password"
          placeholder="At least 10 characters"
          error={form.formState.errors.password?.message}
          {...form.register("password")}
        />
        {signupMutation.isError ? (
          <p className="mt-2 text-body-sm text-status-danger-text" role="alert">
            {signupMutation.error instanceof ApiError
              ? signupMutation.error.message
              : "Could not start your trial."}
          </p>
        ) : null}
        <Button
          type="submit"
          className="mt-3 w-full"
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
