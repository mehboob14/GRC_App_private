/**
 * The platform admin's session, held apart from the workspace session on purpose.
 *
 * Its own storage keys, its own token plane, and the API client attaches this token
 * only to `/provider/*` paths (and never the workspace token there), so the two can
 * never be mixed. sessionStorage only, like the workspace session: never localStorage
 * (ADR-0006).
 */

const TOKEN_KEY = "verity.provider.token";
const ADMIN_KEY = "verity.provider.admin";

export type ProviderAdmin = {
  /** What the admin typed to sign in; the session response carries no profile. */
  email: string;
  /** ISO time the token stops working, from the sign-in response. */
  expiresAt: string;
};

let memoryToken: string | null = null;
let memoryAdmin: ProviderAdmin | null = null;

/** The one test for "this request belongs to the platform plane". */
export function isProviderPath(path: string): boolean {
  return path === "/provider" || path.startsWith("/provider/");
}

/** The sign-in calls themselves: a 401 here is a refusal, not a dead session. */
export function isProviderAuthPath(path: string): boolean {
  return path === "/provider/login" || path.startsWith("/provider/mfa/");
}

export function getProviderToken(): string | null {
  if (memoryToken) return memoryToken;
  try {
    memoryToken = sessionStorage.getItem(TOKEN_KEY);
  } catch {
    memoryToken = null;
  }
  return memoryToken;
}

export function getProviderAdmin(): ProviderAdmin | null {
  if (memoryAdmin) return memoryAdmin;
  try {
    const raw = sessionStorage.getItem(ADMIN_KEY);
    memoryAdmin = raw ? (JSON.parse(raw) as ProviderAdmin) : null;
  } catch {
    memoryAdmin = null;
  }
  return memoryAdmin;
}

export function setProviderSession(token: string, admin: ProviderAdmin): void {
  memoryToken = token;
  memoryAdmin = admin;
  try {
    sessionStorage.setItem(TOKEN_KEY, token);
    sessionStorage.setItem(ADMIN_KEY, JSON.stringify(admin));
  } catch {
    // Storage blocked: the session lives in memory until the tab reloads.
  }
}

export function clearProviderSession(): void {
  memoryToken = null;
  memoryAdmin = null;
  try {
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(ADMIN_KEY);
  } catch {
    // Nothing stored to remove.
  }
}

/** Signed in, and not past the token's own expiry. The server is still the authority. */
export function isProviderSignedIn(): boolean {
  if (!getProviderToken()) return false;
  const admin = getProviderAdmin();
  return !admin || Date.parse(admin.expiresAt) > Date.now();
}
