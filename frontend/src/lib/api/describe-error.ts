import { ApiError } from "@/lib/api/client";

export type ErrorKind =
  | "network"
  | "timeout"
  | "auth"
  | "permission"
  | "notFound"
  | "conflict"
  | "validation"
  | "rateLimit"
  | "server"
  | "unknown";

export type DescribedError = {
  kind: ErrorKind;
  /** Short, for an ErrorState heading or an ErrorBanner title. */
  title: string;
  /** One sentence a non-engineer can act on. Never contains internals. */
  message: string;
  /** Whether offering "Try again" makes sense. A 403 is not retryable. */
  retryable: boolean;
  /** Support reference. Only set when it would actually help support. */
  referenceId?: string;
};

/**
 * The single place a failure becomes words a person reads.
 *
 * Before this, every call site invented its own fallback string, so the same
 * failure read differently in every module and a dropped connection surfaced as
 * "Couldn't update." with no hint that the network was the problem.
 *
 * The split that matters: for DOMAIN failures (409, 422, 400) the backend's
 * message is the good one. Those come from typed exceptions in core.errors and
 * are written to be shown, so they are passed through. For INFRASTRUCTURE
 * failures (5xx, network, timeout) the server message is either generic or
 * absent, so we supply the copy and never surface internals.
 *
 * `subject` names the thing being acted on so the copy can be specific:
 * describeError(e, "control") -> "This control no longer exists."
 */
export function describeError(error: unknown, subject?: string): DescribedError {
  const thing = subject ?? "item";

  if (error instanceof ApiError) {
    const reference =
      error.correlationId && !["unknown", "offline", "timeout"].includes(error.correlationId)
        ? error.correlationId
        : undefined;

    if (error.code === "network_timeout") {
      return {
        kind: "timeout",
        title: "That took too long",
        message: "The request was stopped after 30 seconds. Try again.",
        retryable: true,
      };
    }
    if (error.status === 0) {
      return {
        kind: "network",
        title: "Can't reach Verity",
        message: navigator.onLine
          ? "The server is not responding. Check your connection, then try again."
          : "You appear to be offline. Reconnect, then try again.",
        retryable: true,
      };
    }
    if (error.status === 401) {
      return {
        kind: "auth",
        title: "Your session has ended",
        message: "Sign in again to continue.",
        retryable: false,
      };
    }
    if (error.status === 403) {
      return {
        kind: "permission",
        title: "You do not have access",
        message: `You do not have permission to view this ${thing}. Ask a workspace admin if you need it.`,
        retryable: false,
      };
    }
    if (error.status === 404) {
      return {
        kind: "notFound",
        title: "Not found",
        message: `This ${thing} no longer exists. It may have been deleted or moved.`,
        retryable: false,
      };
    }
    if (error.status === 429) {
      return {
        kind: "rateLimit",
        title: "Too many requests",
        message: "Wait a few seconds, then try again.",
        retryable: true,
      };
    }
    if (error.status >= 500) {
      return {
        kind: "server",
        title: "Something went wrong",
        message: "We're on it. Try again in a moment.",
        retryable: true,
        referenceId: reference,
      };
    }
    // 400/409/422 and any other 4xx: the server wrote this message for a reader.
    return {
      kind: error.status === 409 ? "conflict" : "validation",
      title: error.status === 409 ? "That conflicts with a change" : "That did not work",
      message: error.message,
      retryable: false,
      referenceId: reference,
    };
  }

  // Never render a raw Error message: it is a stack-adjacent developer string.
  return {
    kind: "unknown",
    title: "Something went wrong",
    message: "Try again, or contact support if it continues.",
    retryable: true,
  };
}

/** Convenience for a toast, which shows one line. */
export function errorToast(error: unknown, subject?: string): string {
  return describeError(error, subject).message;
}
