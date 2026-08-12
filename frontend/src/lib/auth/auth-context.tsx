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
  refreshPrincipal: () => void;
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

  const refreshPrincipal = useCallback(() => {
    setPrincipal(getPrincipal());
    setToken(getAccessToken());
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
