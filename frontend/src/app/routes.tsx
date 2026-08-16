import { Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "@/components/layout/app-layout";
import { ComingSoonPage } from "@/app/coming-soon-page";
import { PublicOnly, RequireAuth } from "@/app/auth-gates";
import { SignInPage } from "@/features/iam/components/sign-in-page";
import { SignUpPage } from "@/features/iam/components/sign-up-page";
import { MfaEnrollPage } from "@/features/iam/components/mfa-enroll-page";
import { AcceptInvitePage } from "@/features/iam/components/accept-invite-page";
import { VerifyEmailPage } from "@/features/iam/components/verify-email-page";
import { ForgotPasswordPage } from "@/features/iam/components/forgot-password-page";
import { ResetPasswordPage } from "@/features/iam/components/reset-password-page";
import { SettingsLayout } from "@/features/iam/components/settings-layout";
import { TeamPage } from "@/features/iam/components/team-page";
import { GroupsPage } from "@/features/iam/components/groups-page";
import { RolesPage } from "@/features/iam/components/roles-page";
import { SecurityPage } from "@/features/iam/components/security-page";
import { AuditLogPage } from "@/features/audit/components/audit-log-page";
import { QuickStartPage } from "@/features/compliance/components/quick-start-page";
import { FrameworksPage } from "@/features/compliance/components/frameworks-page";
import { FrameworkDetailPage } from "@/features/compliance/components/framework-detail-page";
import { ControlsPage } from "@/features/compliance/components/controls-page";
import { CompanyProfilePage } from "@/features/tenancy/company-profile-page";
import { ConnectionsPage } from "@/features/connectors/components/connections-page";

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<PublicOnly />}>
        <Route path="/sign-in" element={<SignInPage />} />
        <Route path="/sign-up" element={<SignUpPage />} />
        <Route path="/mfa/enroll" element={<MfaEnrollPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      </Route>

      {/* Reachable whether or not you are signed in: an existing user accepting a
          second workspace is already authenticated, and PublicOnly would bounce
          them off, dropping the token (review finding 24). */}
      <Route path="/accept-invite" element={<AcceptInvitePage />} />

      {/* Verify-first signup lands here from the emailed link — reachable
          whether or not signed in, and it drops any stale session before
          resuming MFA / workspace selection (see verify-email-page). */}
      <Route path="/verify-email" element={<VerifyEmailPage />} />

      {/* Reset link is reachable whether or not signed in — a signed-in user's
          reset revokes their current session by construction. */}
      <Route path="/reset-password" element={<ResetPasswordPage />} />

      <Route element={<RequireAuth />}>
        <Route element={<AppLayout />}>
          <Route index element={<Navigate to="/quick-start" replace />} />
          <Route path="quick-start" element={<QuickStartPage />} />
          <Route path="frameworks" element={<FrameworksPage />} />
          <Route path="frameworks/:frameworkId" element={<FrameworkDetailPage />} />
          <Route path="controls" element={<ControlsPage />} />
          <Route path="connectors" element={<ConnectionsPage />} />
          {/* People and Company profile live under Settings; keep old paths working. */}
          <Route path="people" element={<Navigate to="/settings/people" replace />} />
          <Route
            path="company-profile"
            element={<Navigate to="/settings/company" replace />}
          />
          <Route path="settings" element={<SettingsLayout />}>
            <Route index element={<Navigate to="people" replace />} />
            <Route path="team" element={<Navigate to="/settings/people" replace />} />
            <Route path="people" element={<TeamPage />} />
            <Route path="company" element={<CompanyProfilePage />} />
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
