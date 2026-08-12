/**
 * Session tokens are held in memory for the SPA lifetime.
 * sessionStorage is used only so a refresh during demos keeps the session —
 * production Phase 1 will use httpOnly cookies (ADR-0006). Never localStorage.
 */

import { isPermissionKey } from "@/lib/api/types";
import type { SessionPrincipal, WorkspaceSummary } from "@/lib/api/types";

const TOKEN_KEY = "verity.session.token";
const PRINCIPAL_KEY = "verity.session.principal";

let memoryToken: string | null = null;
let memoryPrincipal: SessionPrincipal | null = null;

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
  memoryToken = token;
  memoryPrincipal = principal;
  sessionStorage.setItem(TOKEN_KEY, token);
  sessionStorage.setItem(PRINCIPAL_KEY, JSON.stringify(principal));
}

export function clearSession(): void {
  memoryToken = null;
  memoryPrincipal = null;
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(PRINCIPAL_KEY);
}

export function hasPermission(
  principal: SessionPrincipal | null,
  key: string,
): boolean {
  return isPermissionKey(key) && Boolean(principal?.permissions.includes(key));
}

export type AuthSnapshot = {
  token: string | null;
  principal: SessionPrincipal | null;
  workspaces: WorkspaceSummary[];
};
