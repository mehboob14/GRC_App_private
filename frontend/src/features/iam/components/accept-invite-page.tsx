import { useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { cn } from "@/lib/cn";
import { authApi } from "@/lib/api/endpoints";
import { useAuth } from "@/lib/auth/auth-context";
import type { AcceptInvitationRequest } from "@/lib/api/types";
import { authSuccessDelay } from "@/features/iam/auth-motion";
import { AuthSplitLayout } from "@/features/iam/components/auth-split-layout";
import { AuthSubmitButton } from "@/features/iam/components/auth-submit-button";
import { AuthAlert, FailureAlert } from "@/features/iam/auth-kit/auth-alert";
import { CtaLink } from "@/features/iam/auth-kit/auth-bits";
import { linkClass, secondaryPill } from "@/features/iam/auth-kit/helpers";
import { describeAuthFailure } from "@/features/iam/auth-kit/auth-errors";
import {
  AuthField,
  AuthPasswordField,
} from "@/features/iam/auth-kit/auth-field";
import { newPasswordSchema } from "@/features/iam/auth-kit/password-rules";

const newUserSchema = z.object({
  full_name: z.string().trim().min(2, "Enter your full name."),
  password: newPasswordSchema,
});

type NewUserValues = z.infer<typeof newUserSchema>;
type Choice = "new" | "existing";

export function AcceptInvitePage() {
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const [choice, setChoice] = useState<Choice>("new");
  const [accepted, setAccepted] = useState(false);
  const [shakeKey, setShakeKey] = useState(0);
  const alertRef = useRef<HTMLDivElement>(null);
  // A signed in visitor is by definition an existing user joining another
  // workspace: no new user fields, and they stay in the app afterwards.
  const asExistingUser = choice === "existing" || isAuthenticated;

  const form = useForm<NewUserValues>({
    resolver: zodResolver(newUserSchema),
    defaultValues: { full_name: "", password: "" },
    mode: "onTouched",
  });
  const password = form.watch("password");

  const acceptMutation = useMutation({
    mutationFn: (body: AcceptInvitationRequest) =>
      authApi.acceptInvitation(body),
    onSuccess: (result) => {
      if (isAuthenticated) {
        // Their session already knows them: refresh the switcher so the new
        // workspace appears, and show a success state rather than bouncing.
        void queryClient.invalidateQueries({ queryKey: ["workspaces"] });
        return;
      }
      const go = () =>
        navigate("/sign-in", {
          replace: true,
          state: {
            notice: `You joined ${result.tenant_name}. Sign in with your email${asExistingUser ? "" : " and new password"}.`,
          },
        });
      const delay = authSuccessDelay();
      if (!delay) {
        go();
        return;
      }
      setAccepted(true);
      window.setTimeout(go, delay);
    },
    onError: (error) => {
      setShakeKey((k) => k + 1);
      const failure = describeAuthFailure(error, "invite");
      if (failure.field === "password" && !asExistingUser) {
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

  if (isAuthenticated && acceptMutation.isSuccess) {
    return (
      <AuthSplitLayout
        mark={{ icon: "check", tone: "success" }}
        title="You're in"
        subtitle={`You joined ${acceptMutation.data.tenant_name}. Switch to it any time from the workspace menu.`}
      >
        <CtaLink to="/quick-start" replace>
          Continue to Verity
        </CtaLink>
      </AuthSplitLayout>
    );
  }

  if (!token) {
    return (
      <AuthSplitLayout
        mark={{ icon: "alert", tone: "warning" }}
        title="This invite link is incomplete"
        subtitle="Open the full link you were sent, or ask a workspace admin for a new one."
      >
        <Link to="/sign-in" className={secondaryPill}>
          Back to sign in
        </Link>
      </AuthSplitLayout>
    );
  }

  const failure = acceptMutation.isError
    ? describeAuthFailure(acceptMutation.error, "invite")
    : null;
  const bannerFailure =
    failure && !(failure.field === "password" && !asExistingUser)
      ? failure
      : null;
  const shake = () => setShakeKey((k) => k + 1);
  const clearFailure = () => {
    if (acceptMutation.isError) acceptMutation.reset();
  };
  const submitNew = form.handleSubmit(
    (values) => acceptMutation.mutate({ token, ...values }),
    shake,
  );
  const submit = () => {
    if (asExistingUser) acceptMutation.mutate({ token });
    else void submitNew();
  };

  return (
    <AuthSplitLayout
      mark={{ icon: "team" }}
      title="Join your team"
      subtitle="Accept your invitation to get started."
    >
      <form
        className="flex flex-col gap-4"
        noValidate
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        {bannerFailure ? (
          <FailureAlert
            ref={alertRef}
            failure={bannerFailure}
            onRetry={submit}
          />
        ) : null}

        {isAuthenticated ? null : (
          <div
            role="radiogroup"
            aria-label="Your Verity account"
            className="grid grid-cols-2 gap-1 rounded-full bg-surface-sunken p-1 ring-1 ring-border"
          >
            {(
              [
                ["new", "I'm new to Verity"],
                ["existing", "I have an account"],
              ] as const
            ).map(([id, label]) => (
              <button
                key={id}
                type="button"
                role="radio"
                aria-checked={choice === id}
                onClick={() => {
                  setChoice(id);
                  clearFailure();
                }}
                className={cn(
                  "h-9 rounded-full text-label-md transition-[background-color,color,box-shadow] duration-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent",
                  choice === id
                    ? "bg-surface-primary text-text-primary shadow-2"
                    : "text-text-subtle hover:text-text-primary",
                )}
              >
                {label}
              </button>
            ))}
          </div>
        )}

        {asExistingUser ? (
          <AuthAlert
            tone="info"
            icon="user"
            title={
              isAuthenticated
                ? "You're signed in"
                : "We'll add this workspace to your account"
            }
          >
            {isAuthenticated
              ? "Accepting adds this workspace to your account."
              : "Sign in with your usual email and password afterwards."}
          </AuthAlert>
        ) : (
          <>
            <AuthField
              label="Full name"
              icon="user"
              autoComplete="name"
              placeholder="How teammates will see you"
              valid={
                Boolean(form.formState.touchedFields.full_name) &&
                !form.formState.errors.full_name
              }
              error={form.formState.errors.full_name?.message}
              {...form.register("full_name", { onChange: clearFailure })}
            />
            <AuthPasswordField
              label="Create a password"
              autoComplete="new-password"
              rules
              typed={password}
              error={form.formState.errors.password?.message}
              {...form.register("password", { onChange: clearFailure })}
            />
          </>
        )}

        <AuthSubmitButton
          label="Accept invitation"
          steps={["Joining the workspace"]}
          successLabel="Invitation accepted"
          phase={
            accepted ? "success" : acceptMutation.isPending ? "loading" : "idle"
          }
          shakeKey={shakeKey}
        />
      </form>

      {isAuthenticated ? null : (
        <p className="mt-7 text-center text-body-md text-text-secondary">
          Already a member?{" "}
          <Link className={linkClass} to="/sign-in">
            Sign in
          </Link>
        </p>
      )}
    </AuthSplitLayout>
  );
}
