import { describeError, type DescribedError } from "@/lib/api/describe-error";
import {
  describeAuthFailure,
  type AuthContext,
  type AuthFailure,
} from "@/features/iam/auth-kit/auth-errors";

/**
 * `describeError` stays the one place a failure becomes words. The single thing it
 * cannot know is whose permission was missing: its 403 copy sends the reader to a
 * workspace admin, and on the platform plane the answer is a platform role.
 */
export function describeProviderError(
  error: unknown,
  subject?: string,
): DescribedError {
  const described = describeError(error, subject);
  if (described.kind !== "permission") return described;
  return {
    ...described,
    title: "Your role cannot do this",
    message: "Your platform role does not allow this. Ask a super admin if you need it.",
  };
}

/**
 * The sign in failures, as the workspace sign in words them, except where the
 * advice does not apply: a platform admin has no password reset to point at.
 */
export function describeProviderAuthFailure(
  error: unknown,
  context: AuthContext,
): AuthFailure {
  const failure = describeAuthFailure(error, context);
  return failure.kind === "credentials"
    ? { ...failure, body: "Check for typos and Caps Lock." }
    : failure;
}
