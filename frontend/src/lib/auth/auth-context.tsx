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
  switchWorkspace: (membershipId: string) => Promise<void>;
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

  const switchWorkspace = useCallback(async (membershipId: string) => {
    const response = await authApi.switchWorkspace(membershipId);
    if (response.status !== "authenticated") {
      throw new Error("Workspace switch did not complete.");
    }
    applySuccess(response);
    setPrincipal(response.principal);
    setToken(response.access_token);
  }, []);

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
