import { createContext, useContext } from "react";
import type {
  LoginResponse,
  SessionPrincipal,
  WorkspaceSummary,
} from "@/lib/api/types";

export type AuthContextValue = {
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

export const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

export type { WorkspaceSummary };
