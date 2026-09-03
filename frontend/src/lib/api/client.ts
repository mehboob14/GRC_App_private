import type { ApiErrorBody } from "@/lib/api/types";
import { clearSession, getAccessToken } from "@/lib/auth/session";

/** Mocks are a dev convenience and default OFF — opt in with VITE_USE_MOCKS=true. */
const USE_MOCKS = import.meta.env.VITE_USE_MOCKS === "true";

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly correlationId: string;

  constructor(status: number, body: ApiErrorBody) {
    super(body.error.message);
    this.name = "ApiError";
    this.status = status;
    this.code = body.error.code;
    this.correlationId = body.error.correlation_id;
  }

  /**
   * The request never reached the API: offline, DNS, TLS, a dropped connection,
   * or the server not running.
   *
   * This is an ApiError on purpose. Every call site in the app is written as
   * `e instanceof ApiError ? e.message : "<generic fallback>"`, so a bare
   * `TypeError: Failed to fetch` used to land on the fallback and tell the
   * reader nothing about the most common failure there is. Status 0 keeps it
   * distinguishable from any real HTTP response.
   */
  static network(): ApiError {
    return new ApiError(0, {
      error: {
        code: "network_unreachable",
        message: "Can't reach Verity. Check your connection, then try again.",
        correlation_id: "offline",
      },
    });
  }

  static timeout(): ApiError {
    return new ApiError(0, {
      error: {
        code: "network_timeout",
        message: "That request took too long and was stopped. Try again.",
        correlation_id: "timeout",
      },
    });
  }

  /** True when retrying the same request could plausibly succeed. */
  get retryable(): boolean {
    return this.status === 0 || this.status === 429 || this.status >= 500;
  }
}

/**
 * A request that has not answered by now is not going to. Without this a dead
 * connection hangs the calling view forever with a spinner and no way out.
 * Uploads get far longer: a scanner export can legitimately take minutes.
 */
const REQUEST_TIMEOUT_MS = 30_000;
const UPLOAD_TIMEOUT_MS = 300_000;

export function mocksEnabled(): boolean {
  return USE_MOCKS;
}

/**
 * `fetch` only rejects when the request never completed, and it does so with a
 * bare `TypeError` that carries nothing a reader could act on. Translate that,
 * and the abort we raise ourselves, into errors the UI already knows how to
 * render. Everything else (including every 4xx and 5xx) resolves normally and
 * is handled by the caller.
 */
async function fetchOrThrow(
  url: string,
  init: RequestInit,
  isUpload: boolean,
): Promise<Response> {
  const timeoutMs = isUpload ? UPLOAD_TIMEOUT_MS : REQUEST_TIMEOUT_MS;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  // Respect a caller's own signal as well as the timeout.
  init.signal?.addEventListener("abort", () => controller.abort(), { once: true });
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } catch (cause) {
    if (controller.signal.aborted && !init.signal?.aborted) throw ApiError.timeout();
    // A caller-initiated abort is a cancellation, not a failure: let it through
    // so react-query drops the result instead of showing an error.
    if (init.signal?.aborted) throw cause;
    throw ApiError.network();
  } finally {
    clearTimeout(timer);
  }
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  // FormData must set its own Content-Type: the browser appends the multipart
  // boundary, and overriding it here makes the body unparseable server-side.
  const isFormData = typeof FormData !== "undefined" && init.body instanceof FormData;
  if (init.body && !isFormData && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const token = getAccessToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const send = () => fetchOrThrow(`/api/v1${path}`, { ...init, headers }, isFormData);

  let response = await send();

  // Dev-mocks self-heal: when the browser restarts the MSW service worker
  // it forgets this client, and requests fall through to the Vite proxy
  // (which has no backend and 500s). Re-handshake and retry once. Never
  // taken in production — VITE_USE_MOCKS is a dev-only flag, and no mock
  // handler responds with a 5xx.
  if (USE_MOCKS && response.status >= 500) {
    const { startWorker } = await import("@/mocks/browser");
    await startWorker();
    response = await send();
  }

  if (!response.ok) {
    let body: ApiErrorBody;
    try {
      body = (await response.json()) as ApiErrorBody;
    } catch {
      // Not JSON: a proxy or gateway answered instead of the API, so there is
      // no domain message to show. statusText is often empty over HTTP/2 and
      // is jargon when it is not, so never put it in front of a reader.
      body = {
        error: {
          code: "http_error",
          message: "Something went wrong. Try again, or contact support if it continues.",
          correlation_id: "unknown",
        },
      };
    }
    // A 401 on a request that carried a bearer token means the session is dead
    // (12h TTL, disabled membership, non-active tenant). Clear it and return to
    // sign-in. Auth routes are exempt: a wrong password or expired challenge
    // must not cause a redirect loop.
    if (response.status === 401 && token && !path.startsWith("/auth/")) {
      clearSession();
      window.location.assign("/sign-in");
    }
    throw new ApiError(response.status, body);
  }

  // 202 (verification resend — accepted, no body) and 204 carry no payload;
  // calling response.json() on an empty body throws, so short-circuit both.
  if (response.status === 202 || response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}
