import { ApiError } from "@/lib/api/client";

export type AuthFailureKind =
  | "credentials"
  | "code"
  | "emailTaken"
  | "weakPassword"
  | "rateLimit"
  | "expired"
  | "network"
  | "timeout"
  | "server"
  | "rejected"
  | "unknown";

export type AuthFailure = {
  kind: AuthFailureKind;
  /** One short line: what happened. */
  title: string;
  /** What to do about it. */
  body?: string;
  /** The field the failure belongs to, so it can be shown and focused there. */
  field?: "email" | "password" | "code";
  retryable: boolean;
  /** A support reference, only when it would help support. */
  reference?: string;
};

export type AuthContext =
  | "signin"
  | "signup"
  | "mfa"
  | "recovery"
  | "select"
  | "enroll"
  | "reset"
  | "forgot"
  | "invite"
  | "verify";

/**
 * Every failure on a sign in, sign up, reset or MFA form, turned into words a
 * person can act on. Credential and code failures are named plainly with the
 * likely fix; infrastructure failures never leak internals; the backend's own
 * reader copy (weak password, taken email, dead link) passes through where it
 * is already the most specific thing to say.
 */
export function describeAuthFailure(
  error: unknown,
  context: AuthContext,
): AuthFailure {
  if (!(error instanceof ApiError)) {
    return {
      kind: "unknown",
      title: "Something went wrong",
      body: "Try again in a moment.",
      retryable: true,
    };
  }
  const reference =
    error.correlationId &&
    !["unknown", "offline", "timeout"].includes(error.correlationId)
      ? error.correlationId
      : undefined;

  if (error.code === "network_timeout") {
    return {
      kind: "timeout",
      title: "That took too long",
      body: "Check your connection and try again.",
      retryable: true,
    };
  }
  if (error.status === 0) {
    const offline = typeof navigator !== "undefined" && !navigator.onLine;
    return {
      kind: "network",
      title: offline ? "You are offline" : "Can't reach Verity",
      body: offline
        ? "Reconnect to the internet, then try again."
        : "Check your connection, then try again.",
      retryable: true,
    };
  }
  if (error.status === 429) {
    // The server says how long the window has left; without it, say nothing exact.
    const minutes = error.retryAfterSeconds
      ? Math.max(1, Math.ceil(error.retryAfterSeconds / 60))
      : null;
    return {
      kind: "rateLimit",
      title: "Too many attempts",
      body: minutes
        ? `Try again in ${minutes} ${minutes === 1 ? "minute" : "minutes"}.`
        : "Wait a while, then try again.",
      retryable: false,
    };
  }
  // The single use step between password and session (MFA, workspace choice) timed out.
  if (
    error.code === "invalid_token" &&
    ["mfa", "recovery", "select", "enroll"].includes(context)
  ) {
    return {
      kind: "expired",
      title: "Your sign in timed out",
      body: "For your security that step expires quickly. Start again to continue.",
      retryable: false,
    };
  }
  if (error.status >= 500) {
    return {
      kind: "server",
      title: "Something went wrong on our side",
      body: "Your details are fine. Try again in a moment.",
      retryable: true,
      reference,
    };
  }
  if (error.code === "email_taken") {
    return {
      kind: "emailTaken",
      title: "This email already has an account",
      body: "Sign in instead, or use a different work email.",
      field: "email",
      retryable: false,
    };
  }
  if (error.code === "weak_password") {
    return {
      kind: "weakPassword",
      title: error.message,
      field: "password",
      retryable: false,
    };
  }
  if (context === "signin" && error.status === 401) {
    return {
      kind: "credentials",
      title: "Incorrect email or password",
      body: "Check for typos and Caps Lock, or reset your password.",
      field: "password",
      retryable: false,
    };
  }
  if (
    (context === "mfa" || context === "enroll" || context === "recovery") &&
    (error.status === 401 || error.status === 422)
  ) {
    return {
      kind: "code",
      title: "That code didn't work",
      body:
        context === "recovery"
          ? "Check it and try again. Each recovery code works only once."
          : "Codes change every 30 seconds. Enter the one your app shows now.",
      field: "code",
      retryable: false,
    };
  }
  // Any other 4xx carries reader copy the backend wrote for this moment.
  return {
    kind: "rejected",
    title: error.message,
    retryable: false,
    reference,
  };
}
