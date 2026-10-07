import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import type { LoginResponse, SessionPrincipal } from "@/lib/api/types";
import {
  clearSession,
  getAccessToken,
  getPrincipal,
  onRemoteSignOut,
  setPrincipalCache,
  setSession,
} from "@/lib/auth/session";
import { authApi } from "@/lib/api/endpoints";
import { AuthContext } from "@/lib/auth/auth-context";

function applySuccess(response: Extract<LoginResponse, { status: "authenticated" }>) {
  setSession(response.access_token, response.principal);
  return response.principal;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [principal, setPrincipal] = useState<SessionPrincipal | null>(() =>
    getPrincipal(),
  );
  const [token, setToken] = useState<string | null>(() => getAccessToken());

  // Signing out in one tab ends the session in every tab that holds it, so a tab
  // left open does not keep working on a session the person ended.
  useEffect(
    () =>
      onRemoteSignOut(() => {
        setPrincipal(null);
        setToken(null);
      }),
    [],
  );

  /**
   * Re-read the principal from the server and update the cache.
   *
   * Reading sessionStorage alone would just return the stale copy again — the
   * workspace name and the person's own name live in rows the token does not
   * carry, so a round trip is the only way to notice they changed. Failure is
   * deliberately silent: the cached values stay on screen rather than the
   * chrome emptying out because one background refresh did not land.
   */
  const refreshPrincipal = useCallback(async () => {
    setToken(getAccessToken());
    if (!getAccessToken()) {
      setPrincipal(getPrincipal());
      return;
    }
    try {
      const fresh = await authApi.me();
      setPrincipalCache(fresh);
      setPrincipal(fresh);
    } catch {
      setPrincipal(getPrincipal());
    }
  }, []);

  const applyLogin = useCallback((response: LoginResponse) => {
    if (response.status !== "authenticated") return null;
    const next = applySuccess(response);
    setPrincipal(next);
    setToken(response.access_token);
    return next;
  }, []);

  const switchWorkspace = useCallback(
    async (membershipId: string): Promise<LoginResponse> => {
      const response = await authApi.switchWorkspace(membershipId);
      if (response.status === "authenticated") {
        applySuccess(response);
        setPrincipal(response.principal);
        setToken(response.access_token);
      }
      // Non-authenticated branches (mfa_required, mfa_enrollment_required,
      // select_workspace) are routed by the caller — see Topbar.
      return response;
    },
    [],
  );

  const signOut = useCallback(() => {
    // Record the sign-out in the audit trail (best-effort). apiFetch reads the
    // bearer token synchronously, so this captures it before clearSession runs;
    // a failed call must never block the user from signing out.
    void authApi.logout().catch(() => {});
    clearSession();
    setPrincipal(null);
    setToken(null);
  }, []);

  const value = useMemo(
    () => ({
      principal,
      token,
      isAuthenticated: Boolean(token && principal),
      applyLogin,
      switchWorkspace,
      signOut,
      refreshPrincipal,
    }),
    [
      principal,
      token,
      applyLogin,
      switchWorkspace,
      signOut,
      refreshPrincipal,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
