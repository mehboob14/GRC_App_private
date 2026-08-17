import { useAuth } from "@/lib/auth/auth-context";
import { AdminDashboard } from "@/features/dashboard/admin-dashboard";
import { MyDayDashboard } from "@/features/dashboard/my-day-dashboard";

/**
 * Role-aware landing: admins see the org-wide compliance posture; everyone else
 * gets their personal work queue (Operations · My Day).
 */
export function DashboardPage() {
  const { principal } = useAuth();
  const isAdmin = principal?.role_names.includes("Admin") ?? false;
  return isAdmin ? <AdminDashboard /> : <MyDayDashboard />;
}
