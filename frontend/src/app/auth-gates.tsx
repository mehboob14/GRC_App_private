import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "@/lib/auth/auth-context";

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
  if (isAuthenticated) {
    return <Navigate to="/quick-start" replace />;
  }
  return <Outlet />;
}
