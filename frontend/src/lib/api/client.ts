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
}

export function mocksEnabled(): boolean {
  return USE_MOCKS;
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const token = getAccessToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  let response = await fetch(`/api/v1${path}`, {
    ...init,
    headers,
  });

  // Dev-mocks self-heal: when the browser restarts the MSW service worker
  // it forgets this client, and requests fall through to the Vite proxy
  // (which has no backend and 500s). Re-handshake and retry once. Never
  // taken in production — VITE_USE_MOCKS is a dev-only flag, and no mock
  // handler responds with a 5xx.
  if (USE_MOCKS && response.status >= 500) {
    const { startWorker } = await import("@/mocks/browser");
    await startWorker();
    response = await fetch(`/api/v1${path}`, { ...init, headers });
  }

  if (!response.ok) {
    let body: ApiErrorBody;
    try {
      body = (await response.json()) as ApiErrorBody;
    } catch {
      body = {
        error: {
          code: "http_error",
          message: response.statusText || "Request failed.",
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
