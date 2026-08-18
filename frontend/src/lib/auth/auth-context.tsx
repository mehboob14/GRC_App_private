import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { LoginResponse, SessionPrincipal, WorkspaceSummary } from "@/lib/api/types";
import {
  clearSession,
  setPrincipalCache,
  getAccessToken,
  getPrincipal,
  setSession,
} from "@/lib/auth/session";
import { authApi } from "@/lib/api/endpoints";

type AuthContextValue = {
  principal: SessionPrincipal | null;
  token: string | null;
  isAuthenticated: boolean;
  applyLogin: (response: LoginResponse) => SessionPrincipal | null;
  /**
   * Switching is the SAME discriminated union as login: a target membership
   * that holds Admin comes back as `mfa_required` (challenge_token) rather than
   * a session. The session is applied only for `authenticated`; every caller
   * must route the other branches. Returns the raw response so it can.
   */
  switchWorkspace: (membershipId: string) => Promise<LoginResponse>;
  signOut: () => void;
  refreshPrincipal: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function applySuccess(response: Extract<LoginResponse, { status: "authenticated" }>) {
  setSession(response.access_token, response.principal);
  return response.principal;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [principal, setPrincipal] = useState<SessionPrincipal | null>(() =>
    getPrincipal(),
  );
  const [token, setToken] = useState<string | null>(() => getAccessToken());

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

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

export type { WorkspaceSummary };
