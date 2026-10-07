/**
 * The platform admin's session, held apart from the workspace session on purpose.
 *
 * Its own storage keys, its own token plane, and the API client attaches this token
 * only to `/provider/*` paths (and never the workspace token there), so the two can
 * never be mixed. sessionStorage only, like the workspace session: never localStorage
 * (ADR-0006).
 */

import { createTabShare } from "@/lib/auth/tab-share";
import { forgetEntryState } from "@/lib/nav/entry-state";

const TOKEN_KEY = "verity.provider.token";
const ADMIN_KEY = "verity.provider.admin";

/** The same cross-tab sharing as the workspace session, on a channel of its own (see tab-share.ts). */
const share = createTabShare(
  "verity.provider",
  [TOKEN_KEY, ADMIN_KEY],
  TOKEN_KEY,
  // Only the console's own pages, and not its sign-in page.
  (pathname) => /^\/provider(\/|$)/.test(pathname) && !/^\/provider\/login(\/|$)/.test(pathname),
);
const signOutListeners = new Set<() => void>();

/** Call before the first render, so a tab opened from a link starts signed in. */
export const adoptProviderSessionFromOtherTab = share.adopt;

/** Hear that another tab signed this session out. Returns the unsubscribe. */
export function onRemoteProviderSignOut(listener: () => void): () => void {
  signOutListeners.add(listener);
  return () => {
    signOutListeners.delete(listener);
  };
}

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
  forgetEntryState();
  memoryToken = token;
  memoryAdmin = admin;
  try {
    sessionStorage.setItem(TOKEN_KEY, token);
    sessionStorage.setItem(ADMIN_KEY, JSON.stringify(admin));
  } catch {
    // Storage blocked: the session lives in memory until the tab reloads.
  }
}

function wipe(): void {
  memoryToken = null;
  memoryAdmin = null;
  forgetEntryState();
  try {
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(ADMIN_KEY);
  } catch {
    // Nothing stored to remove.
  }
}

share.serve(() => {
  wipe();
  for (const listener of signOutListeners) listener();
});

export function clearProviderSession(): void {
  const token = getProviderToken();
  wipe();
  share.announceSignOut(token);
}

/** Signed in, and not past the token's own expiry. The server is still the authority. */
export function isProviderSignedIn(): boolean {
  if (!getProviderToken()) return false;
  const admin = getProviderAdmin();
  return !admin || Date.parse(admin.expiresAt) > Date.now();
}
