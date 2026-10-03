import { useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/components/ui";
import { setProviderSession } from "@/lib/provider/session";
import { FailureAlert } from "@/features/iam/auth-kit/auth-alert";
import {
  AuthField,
  AuthPasswordField,
} from "@/features/iam/auth-kit/auth-field";
import { providerAuthApi } from "../api";
import { describeProviderAuthFailure } from "../errors";
import type {
  ProviderChallenge,
  ProviderEnrollConfirm,
  ProviderSession,
} from "../types";
import { ProviderAuthShell } from "./provider-auth-shell";
import {
  EnrollScreen,
  RecoveryCodesScreen,
  VerifyScreen,
} from "./provider-mfa-screens";

const schema = z.object({
  email: z
    .string()
    .trim()
    .min(1, "Enter your email.")
    .email("Enter a valid email, like name@company.com."),
  password: z.string().min(1, "Enter your password."),
});

type FormValues = z.infer<typeof schema>;

/** Where the sign in stands. A password buys a challenge; only the code buys a session. */
type Step =
  | { name: "credentials" }
  | { name: "verify"; challenge: ProviderChallenge }
  | { name: "enroll"; challenge: ProviderChallenge }
  | { name: "codes"; session: ProviderEnrollConfirm };

type LocationState = { from?: { pathname?: string } } | null;

export function ProviderSignInPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const destination =
    (location.state as LocationState)?.from?.pathname ?? "/provider/tenants";

  const [step, setStep] = useState<Step>({ name: "credentials" });
  const [email, setEmail] = useState("");
  const alertRef = useRef<HTMLDivElement>(null);

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { email: "", password: "" },
    mode: "onTouched",
  });

  const login = useMutation({
    mutationFn: (values: FormValues) =>
      providerAuthApi.login(values.email.trim().toLowerCase(), values.password),
    onSuccess: (challenge, values) => {
      setEmail(values.email.trim().toLowerCase());
      setStep(
        challenge.next_step === "mfa_enroll"
          ? { name: "enroll", challenge }
          : { name: "verify", challenge },
      );
    },
    onError: (error) => {
      if (describeProviderAuthFailure(error, "signin").field === "password") {
        form.setFocus("password", { shouldSelect: true });
      } else {
        window.requestAnimationFrame(() => alertRef.current?.focus());
      }
    },
  });

  function enter(session: ProviderSession) {
    setProviderSession(session.token, {
      email,
      expiresAt: session.expires_at,
    });
    navigate(destination, { replace: true });
  }

  function restart() {
    login.reset();
    form.setValue("password", "");
    setStep({ name: "credentials" });
  }

  if (step.name === "verify") {
    return (
      <VerifyScreen
        email={email}
        challenge={step.challenge}
        onSession={enter}
        onRestart={restart}
      />
    );
  }
  if (step.name === "enroll") {
    return (
      <EnrollScreen
        email={email}
        challenge={step.challenge}
        onEnrolled={(session) => setStep({ name: "codes", session })}
        onRestart={restart}
      />
    );
  }
  if (step.name === "codes") {
    const { session } = step;
    return (
      <RecoveryCodesScreen
        codes={session.recovery_codes}
        onContinue={() => enter(session)}
      />
    );
  }

  const failure = login.isError
    ? describeProviderAuthFailure(login.error, "signin")
    : null;
  const clearFailure = () => {
    if (login.isError) login.reset();
  };
  const submit = form.handleSubmit((values) => login.mutate(values));

  return (
    <ProviderAuthShell
      title="Platform sign in"
      subtitle="For Verity operators. Customers sign in to their workspace."
    >
      <form
        className="flex flex-col gap-4"
        noValidate
        onSubmit={(event) => void submit(event)}
      >
        {failure ? (
          <FailureAlert
            ref={alertRef}
            failure={failure}
            onRetry={() => void submit()}
          />
        ) : null}
        <AuthField
          label="Email"
          icon="mail"
          type="email"
          inputMode="email"
          autoComplete="username"
          autoCapitalize="none"
          autoFocus
          spellCheck={false}
          placeholder="name@verity.example"
          error={form.formState.errors.email?.message}
          {...form.register("email", { onChange: clearFailure })}
        />
        <AuthPasswordField
          label="Password"
          autoComplete="current-password"
          error={form.formState.errors.password?.message}
          {...form.register("password", { onChange: clearFailure })}
        />
        <Button
          type="submit"
          size="lg"
          className="mt-1 w-full"
          loading={login.isPending}
        >
          Continue
        </Button>
      </form>
    </ProviderAuthShell>
  );
}
