import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { AuthSplitLayout } from "@/features/iam/components/auth-split-layout";
import {
  Button,
  Checkbox,
  ErrorBanner,
  Icon,
  PasswordField,
  TextField,
} from "@/components/ui";
import { authApi } from "@/lib/api/endpoints";
import { describeAuthError } from "@/lib/api/describe-error";
import { useAuth } from "@/lib/auth/auth-context";
import { useAlertFocus } from "@/features/iam/hooks/use-alert-focus";
import type { AcceptInvitationRequest } from "@/lib/api/types";

const newUserSchema = z.object({
  full_name: z.string().min(2, "Enter your full name."),
  password: z.string().min(10, "Use at least 10 characters."),
});

type NewUserValues = z.infer<typeof newUserSchema>;

export function AcceptInvitePage() {
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const [existingAccount, setExistingAccount] = useState(false);
  // A signed-in visitor is definitionally an existing user joining a second
  // workspace: no new-user fields, and they stay in the app afterwards.
  const asExistingUser = existingAccount || isAuthenticated;

  const form = useForm<NewUserValues>({
    resolver: zodResolver(newUserSchema),
    defaultValues: { full_name: "", password: "" },
    mode: "onBlur",
  });

  const acceptMutation = useMutation({
    mutationFn: (body: AcceptInvitationRequest) =>
      authApi.acceptInvitation(body),
    onSuccess: (result) => {
      if (isAuthenticated) {
        // Their session already knows them; refresh the switcher's workspace list
        // so the new one appears, and show a success state rather than bouncing.
        void queryClient.invalidateQueries({ queryKey: ["workspaces"] });
        return;
      }
      navigate("/sign-in", {
        replace: true,
        state: {
          notice: `Invitation accepted. Sign in to ${result.tenant_name} with your email${
            existingAccount ? "" : " and new password"
          }.`,
        },
      });
    },
  });

  const alertRef = useAlertFocus(acceptMutation.isError);

  if (isAuthenticated && acceptMutation.isSuccess && acceptMutation.data) {
    const joined = acceptMutation.data.tenant_name;
    return (
      <AuthSplitLayout
        title="You're in"
        subtitle={`You've joined ${joined}. It's now in your workspace switcher, top left, so you can jump between organisations.`}
      >
        <Button
          className="w-full"
          size="lg"
          onClick={() => navigate("/quick-start", { replace: true })}
        >
          Continue to Verity
          <Icon name="arrowr" className="size-4" />
        </Button>
      </AuthSplitLayout>
    );
  }

  if (!token) {
    return (
      <AuthSplitLayout
        title="Join your workspace"
        subtitle="This invite link is missing its token. Open the full link you were given, or ask a workspace admin to send a new one."
      >
        <Link className="font-semibold text-text-link" to="/sign-in">
          Back to sign in
        </Link>
      </AuthSplitLayout>
    );
  }

  function submitNewUser(values: NewUserValues) {
    acceptMutation.mutate({ token, ...values });
  }

  return (
    <AuthSplitLayout
      title="Join your workspace"
      subtitle="Accept your invitation to finish setting up access. You'll sign in right after."
    >
      <form
        className="flex flex-col gap-3"
        onSubmit={(e) => {
          if (asExistingUser) {
            e.preventDefault();
            acceptMutation.mutate({ token });
            return;
          }
          void form.handleSubmit(submitNewUser)(e);
        }}
        noValidate
      >
        {acceptMutation.isError ? (
          <ErrorBanner
            ref={alertRef}
            title={describeAuthError(acceptMutation.error).message}
          />
        ) : null}
        {isAuthenticated ? null : (
          <label className="flex items-center gap-2 text-body-md text-text-primary">
            <Checkbox
              checked={existingAccount}
              onCheckedChange={setExistingAccount}
            />
            I already have a Verity account
          </label>
        )}

        {asExistingUser ? (
          <p className="text-body-sm text-text-secondary">
            {isAuthenticated
              ? "You're signed in. Accepting attaches this workspace to your account."
              : "We'll attach this workspace to your existing account. Sign in with your usual email and password afterwards."}
          </p>
        ) : (
          <>
            <TextField
              label="Full name"
              size="lg"
              autoComplete="name"
              placeholder="Your name as teammates will see it"
              error={form.formState.errors.full_name?.message}
              {...form.register("full_name")}
            />
            <PasswordField
              label="Password"
              size="lg"
              autoComplete="new-password"
              placeholder="At least 10 characters"
              error={form.formState.errors.password?.message}
              {...form.register("password")}
            />
          </>
        )}

        <Button
          type="submit"
          className="mt-1 w-full"
          size="lg"
          loading={acceptMutation.isPending}
        >
          Accept invitation
          <Icon name="arrowr" className="size-4" />
        </Button>
      </form>

      <p className="mt-6 text-body-sm text-text-secondary">
        Already a member of this workspace?{" "}
        <Link className="font-semibold text-text-link" to="/sign-in">
          Sign in
        </Link>
      </p>
    </AuthSplitLayout>
  );
}
