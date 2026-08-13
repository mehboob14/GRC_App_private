import type { NavigateFunction } from "react-router-dom";
import type { LoginResponse } from "@/lib/api/types";

/** The login union minus the terminal, session-bearing branch. */
export type PendingAuth = Exclude<LoginResponse, { status: "authenticated" }>;

/**
 * Route a non-authenticated login/switch response onto the surface that can
 * finish it. Both target surfaces (`/mfa/enroll` and `/sign-in`) live behind
 * the PublicOnly gate, so the caller MUST drop any stale session first — an
 * authenticated visitor is bounced straight back off those routes.
 *
 * `mfa_required` / `select_workspace` are resumed by the sign-in page, which
 * reads the pending response from navigation state and owns their UI. This is
 * the single place that decides where each branch goes — shared by the
 * workspace switcher and invitation-accept flows so they can't drift.
 */
export function resumePendingAuth(
  response: PendingAuth,
  navigate: NavigateFunction,
): void {
  if (response.status === "mfa_enrollment_required") {
    navigate(`/mfa/enroll?challenge=${response.challenge_token}`, {
      replace: true,
    });
    return;
  }
  navigate("/sign-in", { replace: true, state: { pending: response } });
}
