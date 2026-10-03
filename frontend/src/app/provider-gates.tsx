import { Navigate, Outlet, useLocation } from "react-router-dom";
import { isProviderSignedIn } from "@/lib/provider/session";

/**
 * The platform console's gates. They read the platform admin's own session, never
 * the workspace one: a signed in workspace member is a stranger here, and the
 * reverse. Navigation re-renders these, so reading storage at render is enough.
 */
export function RequireProvider() {
  const location = useLocation();
  if (!isProviderSignedIn()) {
    return <Navigate to="/provider/login" replace state={{ from: location }} />;
  }
  return <Outlet />;
}

export function ProviderPublicOnly() {
  if (isProviderSignedIn()) {
    return <Navigate to="/provider/tenants" replace />;
  }
  return <Outlet />;
}
