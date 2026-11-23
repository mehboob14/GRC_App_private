import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { AuthSplitLayout } from "@/features/iam/components/auth-split-layout";
import { AuthAlert } from "@/features/iam/auth-kit/auth-alert";
import { linkClass } from "@/features/iam/auth-kit/helpers";
import { describeAuthFailure } from "@/features/iam/auth-kit/auth-errors";
import { ApiError } from "@/lib/api/client";
import { authApi } from "@/lib/api/endpoints";
import { useAuth } from "@/lib/auth/auth-context";

/**
 * Where Keycloak's sign in lands (openspec/changes/add-keycloak-sso). The API validated the
 * identity and left a one time handoff; claiming it gives a session, or a workspace choice that
 * the sign in page shows. Failures arrive as a fixed code and are said in one sentence.
 */

const FAILURES: Record<string, string> = {
  unavailable: "Single sign on is not available right now. Try again, or use your password.",
  state: "That sign in link has expired. Start again.",
  denied: "Your organisation's sign in did not complete. Start again.",
  token: "We could not confirm your sign in. Start again.",
};

export function SsoCompletePage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { applyLogin } = useAuth();
  const handoff = params.get("handoff");
  const code = params.get("error");
  const [failure, setFailure] = useState<string | null>(
    code ? (FAILURES[code] ?? FAILURES.token) : handoff ? null : FAILURES.state,
  );
  const claimed = useRef(false);

  useEffect(() => {
    if (!handoff || claimed.current) return;
    claimed.current = true; // a handoff is single use; React's double effect must not spend it twice
    authApi
      .ssoComplete(handoff)
      .then((response) => {
        if (response.status === "authenticated") {
          applyLogin(response);
          navigate("/quick-start", { replace: true });
        } else {
          navigate("/sign-in", { replace: true, state: { pending: response } });
        }
      })
      .catch((error: unknown) =>
        // A refused SSO sign in carries reader copy that says what to do (ask for an invite);
        // the password wording of the shared helper would be wrong here.
        setFailure(
          error instanceof ApiError && error.status === 401
            ? error.message
            : describeAuthFailure(error, "signin").title,
        ),
      );
  }, [handoff, applyLogin, navigate]);

  return (
    <AuthSplitLayout title="Signing you in" subtitle="Through your organisation's sign in.">
      {failure ? (
        <AuthAlert
          title={failure}
          action={
            <Link to="/sign-in" className={linkClass}>
              Back to sign in
            </Link>
          }
        />
      ) : (
        <p className="text-body-md text-text-secondary">One moment.</p>
      )}
    </AuthSplitLayout>
  );
}
