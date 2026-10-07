/**
 * Session tokens are held in memory for the SPA lifetime.
 * sessionStorage is used only so a refresh during demos keeps the session —
 * production Phase 1 will use httpOnly cookies (ADR-0006). Never localStorage.
 */

import { isPermissionKey } from "@/lib/api/types";
import type { SessionPrincipal, WorkspaceSummary } from "@/lib/api/types";
import { createTabShare } from "@/lib/auth/tab-share";
import { forgetEntryState } from "@/lib/nav/entry-state";

const TOKEN_KEY = "verity.session.token";
const PRINCIPAL_KEY = "verity.session.principal";

let memoryToken: string | null = null;
let memoryPrincipal: SessionPrincipal | null = null;

/**
 * A tab opened with window.open (the policy editor) starts with empty
 * sessionStorage — it is per-tab. Copy the session from the opener, which is
 * same-origin, so the new tab is authenticated without a second sign-in.
 * sessionStorage only; still never localStorage (ADR-0006).
 */
function bootstrapFromOpener(): void {
  try {
    if (sessionStorage.getItem(TOKEN_KEY)) return;
    const opener = window.opener as Window | null;
    if (!opener) return;
    const token = opener.sessionStorage.getItem(TOKEN_KEY);
    const principal = opener.sessionStorage.getItem(PRINCIPAL_KEY);
    if (token && principal) {
      sessionStorage.setItem(TOKEN_KEY, token);
      sessionStorage.setItem(PRINCIPAL_KEY, principal);
    }
  } catch {
    // Cross-origin opener or blocked storage — fall through to normal auth.
  }
}

bootstrapFromOpener();

/**
 * A tab opened from a link has no sessionStorage of its own. It asks the open tabs
 * for the session before it first renders (see `adoptSessionFromOtherTab`), and
 * every tab answers and hears when the session ends. See tab-share.ts.
 */
const share = createTabShare(
  "verity.session",
  [TOKEN_KEY, PRINCIPAL_KEY],
  TOKEN_KEY,
  // The pages a person reaches signed out on purpose never ask: someone opening an
  // invitation or the sign-in page is not to be handed the session of whoever else
  // used this browser. The platform console has a session of its own.
  (pathname) =>
    !/^\/(sign-in|sign-up|mfa|forgot-password|reset-password|accept-invite|verify-email|vendor-portal|provider)(\/|$)/.test(
      pathname,
    ),
);
const signOutListeners = new Set<() => void>();

/** Call before the first render, so a tab opened from a link starts signed in. */
export const adoptSessionFromOtherTab = share.adopt;

/** Hear that another tab signed this session out. Returns the unsubscribe. */
export function onRemoteSignOut(listener: () => void): () => void {
  signOutListeners.add(listener);
  return () => {
    signOutListeners.delete(listener);
  };
}

function wipe(): void {
  memoryToken = null;
  memoryPrincipal = null;
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(PRINCIPAL_KEY);
  forgetEntryState();
}

share.serve(() => {
  wipe();
  for (const listener of signOutListeners) listener();
});

function readJson<T>(key: string): T | null {
  try {
    const raw = sessionStorage.getItem(key);
    if (!raw) return null;
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

export function getAccessToken(): string | null {
  if (memoryToken) return memoryToken;
  memoryToken = sessionStorage.getItem(TOKEN_KEY);
  return memoryToken;
}

export function getPrincipal(): SessionPrincipal | null {
  if (memoryPrincipal) return memoryPrincipal;
  memoryPrincipal = readJson<SessionPrincipal>(PRINCIPAL_KEY);
  return memoryPrincipal;
}

export function setSession(
  token: string,
  principal: SessionPrincipal,
): void {
  // A new sign-in or a switch of workspace: filters and ids remembered for the last
  // one mean nothing here.
  forgetEntryState();
  memoryToken = token;
  memoryPrincipal = principal;
  sessionStorage.setItem(TOKEN_KEY, token);
  sessionStorage.setItem(PRINCIPAL_KEY, JSON.stringify(principal));
}

/**
 * Replace the cached principal, keeping the current token.
 *
 * The token carries identity, not display data: renaming the workspace or
 * correcting a person's name changes rows the token knows nothing about, so
 * the cached copy goes stale while the session stays perfectly valid.
 */
export function setPrincipalCache(principal: SessionPrincipal): void {
  memoryPrincipal = principal;
  sessionStorage.setItem(PRINCIPAL_KEY, JSON.stringify(principal));
}

export function clearSession(): void {
  const token = getAccessToken();
  wipe();
  share.announceSignOut(token);
}

export function hasPermission(
  principal: SessionPrincipal | null,
  key: string,
): boolean {
  // The SERVER is the authority on what a principal may do. This used to also
  // require `isPermissionKey(key)`, which made the frontend's own list a second
  // gate — so a key the backend had issued but the list had not caught up with
  // denied everyone who legitimately held it, with no error anywhere. That is
  // how every `vulnerabilities:*` check silently returned false once the module
  // shipped. The union stays for type-safety at call sites; it is not a runtime
  // allowlist.
  if (import.meta.env.DEV && !isPermissionKey(key)) {
    console.warn(
      `hasPermission("${key}"): not in PERMISSION_KEYS. Add it to lib/api/types.ts ` +
        "so call sites stay type-checked.",
    );
  }
  return Boolean((principal?.permissions as readonly string[] | undefined)?.includes(key));
}

export type AuthSnapshot = {
  token: string | null;
  principal: SessionPrincipal | null;
  workspaces: WorkspaceSummary[];
};
