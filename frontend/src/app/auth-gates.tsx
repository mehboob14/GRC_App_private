import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "@/lib/auth/auth-context";

/**
 * Both gates decide from the AuthProvider snapshot, which is hydrated
 * synchronously from sessionStorage before the first render — there is no
 * async "checking session" frame, so neither gate can flash the wrong tree.
 * RequireAuth remembers where the visitor was heading; SignInPage returns
 * them there after auth resolves.
 */
export function RequireAuth() {
  const { isAuthenticated } = useAuth();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/sign-in" replace state={{ from: location }} />;
  }

  return <Outlet />;
}

export function PublicOnly() {
  const { isAuthenticated } = useAuth();
  const location = useLocation();
  const from = (location.state as { from?: { pathname?: string } } | null)
    ?.from?.pathname;

  if (isAuthenticated) {
    return <Navigate to={from ?? "/quick-start"} replace />;
  }
  return <Outlet />;
}
