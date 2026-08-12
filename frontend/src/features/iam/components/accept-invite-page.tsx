import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { AuthSplitLayout } from "@/features/iam/components/auth-split-layout";
import {
  Button,
  Checkbox,
  Icon,
  PasswordField,
  TextField,
} from "@/components/ui";
import { authApi } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import type { AcceptInvitationRequest } from "@/lib/api/types";

const newUserSchema = z.object({
  full_name: z.string().min(2, "Enter your full name."),
  password: z.string().min(10, "Use at least 10 characters."),
});

type NewUserValues = z.infer<typeof newUserSchema>;

function messageFrom(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback;
}

export function AcceptInvitePage() {
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const navigate = useNavigate();
  const [existingAccount, setExistingAccount] = useState(false);

  const form = useForm<NewUserValues>({
    resolver: zodResolver(newUserSchema),
    defaultValues: { full_name: "", password: "" },
    mode: "onBlur",
  });

  const acceptMutation = useMutation({
    mutationFn: (body: AcceptInvitationRequest) =>
      authApi.acceptInvitation(body),
    onSuccess: (result) => {
      navigate("/sign-in", {
        replace: true,
        state: {
          notice: `Invitation accepted — sign in to ${result.tenant_name} with your email${
            existingAccount ? "" : " and new password"
          }.`,
        },
      });
    },
  });

  if (!token) {
    return (
      <AuthSplitLayout
        title="Join your workspace"
        subtitle="This invite link is missing its token. Open the full link you were given, or ask a workspace admin to send a new one."
      >
        <Link className="text-text-link" to="/sign-in">
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
        className="flex flex-col gap-2"
        onSubmit={(e) => {
          if (existingAccount) {
            e.preventDefault();
            acceptMutation.mutate({ token });
            return;
          }
          void form.handleSubmit(submitNewUser)(e);
        }}
        noValidate
      >
        <label className="mb-1 flex items-center gap-2 text-body-md text-text-primary">
          <Checkbox
            checked={existingAccount}
            onCheckedChange={setExistingAccount}
          />
          I already have a Verity account
        </label>

        {existingAccount ? (
          <p className="mb-1 text-body-sm text-text-secondary">
            We'll attach this workspace to your existing account. Sign in with
            your usual email and password afterwards.
          </p>
        ) : (
          <>
            <TextField
              label="Full name"
              autoComplete="name"
              placeholder="Your name as teammates will see it"
              error={form.formState.errors.full_name?.message}
              {...form.register("full_name")}
            />
            <PasswordField
              label="Password"
              autoComplete="new-password"
              placeholder="At least 10 characters"
              error={form.formState.errors.password?.message}
              {...form.register("password")}
            />
          </>
        )}

        {acceptMutation.isError ? (
          <p className="mt-1 text-body-sm text-status-danger-text" role="alert">
            {messageFrom(
              acceptMutation.error,
              "Could not accept the invitation. Open the full link you were given, or ask a workspace admin to send a new one.",
            )}
          </p>
        ) : null}

        <Button
          type="submit"
          className="mt-3 w-full"
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
