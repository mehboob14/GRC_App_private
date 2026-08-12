import { Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "@/components/layout/app-layout";
import { ComingSoonPage } from "@/app/coming-soon-page";
import { PublicOnly, RequireAuth } from "@/app/auth-gates";
import { SignInPage } from "@/features/iam/components/sign-in-page";
import { SignUpPage } from "@/features/iam/components/sign-up-page";
import { MfaEnrollPage } from "@/features/iam/components/mfa-enroll-page";
import { AcceptInvitePage } from "@/features/iam/components/accept-invite-page";
import { SettingsLayout } from "@/features/iam/components/settings-layout";
import { TeamPage } from "@/features/iam/components/team-page";
import { GroupsPage } from "@/features/iam/components/groups-page";
import { RolesPage } from "@/features/iam/components/roles-page";
import { SecurityPage } from "@/features/iam/components/security-page";
import { AuditLogPage } from "@/features/audit/components/audit-log-page";
import { QuickStartPage } from "@/features/compliance/components/quick-start-page";
import { ConnectionsPage } from "@/features/connectors/components/connections-page";

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<PublicOnly />}>
        <Route path="/sign-in" element={<SignInPage />} />
        <Route path="/sign-up" element={<SignUpPage />} />
        <Route path="/mfa/enroll" element={<MfaEnrollPage />} />
        <Route path="/accept-invite" element={<AcceptInvitePage />} />
      </Route>

      <Route element={<RequireAuth />}>
        <Route element={<AppLayout />}>
          <Route index element={<Navigate to="/quick-start" replace />} />
          <Route path="quick-start" element={<QuickStartPage />} />
          <Route path="connectors" element={<ConnectionsPage />} />
          <Route path="people" element={<TeamPage />} />
          <Route path="settings" element={<SettingsLayout />}>
            <Route index element={<Navigate to="security" replace />} />
            <Route path="team" element={<Navigate to="/people" replace />} />
            <Route path="groups" element={<GroupsPage />} />
            <Route path="roles" element={<RolesPage />} />
            <Route path="security" element={<SecurityPage />} />
          </Route>
          <Route path="audit-log" element={<AuditLogPage />} />
          <Route
            path="coming-soon/:slug"
            element={<ComingSoonPage title="Coming soon" />}
          />
          <Route
            path="*"
            element={
              <ComingSoonPage
                notFound
                title="Page not found"
                description="That route is not part of the current shell — check the address, or head back to the dashboard."
              />
            }
          />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/sign-in" replace />} />
    </Routes>
  );
}
