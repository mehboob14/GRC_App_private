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
import { SettingsSection } from "@/features/iam/components/settings-section";
import { TeamPage } from "@/features/iam/components/team-page";
import { GroupsPage } from "@/features/iam/components/groups-page";
import { RolesPage } from "@/features/iam/components/roles-page";
import {
  PasswordPolicyPage,
  SecurityPage,
} from "@/features/iam/components/security-page";
import { AuditLogPage } from "@/features/audit/components/audit-log-page";
import { QuickStartPage } from "@/features/compliance/components/quick-start-page";
import { DashboardPage } from "@/features/dashboard/dashboard-page";
import { FrameworksPage } from "@/features/compliance/components/frameworks-page";
import { FrameworkDetailPage } from "@/features/compliance/components/framework-detail-page";
import { ControlsPage } from "@/features/compliance/components/controls-page";
import { ControlDetailPage } from "@/features/compliance/components/control-detail-page";
import { EvidencePage } from "@/features/evidence/components/evidence-page";
import { EvidenceDetailPage } from "@/features/evidence/components/evidence-detail-page";
import { DocumentsRegisterPage } from "@/features/documents/components/documents-register-page";
import { DocumentDetailPage } from "@/features/documents/components/document-detail-page";
import { CampaignPage } from "@/features/documents/components/campaign-page";
import { DocumentApprovalPage } from "@/features/documents/components/document-approval-page";
import { DocumentEditorPage } from "@/features/documents/components/document-editor-page";
import { TasksLayout } from "@/features/tasks/components/tasks-layout";
import { TasksRegisterPage } from "@/features/tasks/components/tasks-register-page";
import { TasksOverviewPage } from "@/features/tasks/components/tasks-overview-page";
import { TasksSettingsPage } from "@/features/tasks/components/tasks-settings-page";
import { TaskDetailPage } from "@/features/tasks/components/task-detail-page";
import { AssetsLayout } from "@/features/assets/components/assets-layout";
import { AssetsRegisterPage } from "@/features/assets/components/assets-register-page";
import { AssetsOverviewPage } from "@/features/assets/components/assets-overview-page";
import { AssetDetailPage } from "@/features/assets/components/asset-detail-page";
import { AssetsImportPage } from "@/features/assets/components/assets-import-page";
import { VulnerabilitiesRegisterPage } from "@/features/vulnerabilities/components/vulnerabilities-register-page";
import { VulnerabilitiesOverviewPage } from "@/features/vulnerabilities/components/vulnerabilities-overview-page";
import { VulnerabilitiesImportPage } from "@/features/vulnerabilities/components/vulnerabilities-import-page";
import { VulnerabilitiesSettingsPage } from "@/features/vulnerabilities/components/vulnerabilities-settings-page";
import { VulnerabilityDetailPage } from "@/features/vulnerabilities/components/vulnerability-detail-page";
import { ScopePage } from "@/features/compliance/components/scope-page";
import { CoveragePage } from "@/features/compliance/components/coverage-page";
import { ComplianceDashboardPage } from "@/features/compliance/components/compliance-dashboard-page";
import { FrameworksLayout } from "@/features/compliance/components/frameworks-layout";
import { CompanyProfilePage } from "@/features/tenancy/company-profile-page";
import { VendorsLayout } from "@/features/vendors/components/vendors-layout";
import { VendorsOverviewPage } from "@/features/vendors/components/vendors-overview-page";
import { VendorsRegisterPage } from "@/features/vendors/components/vendors-register-page";
import { VendorIntakePage } from "@/features/vendors/components/vendor-intake-page";
import { VendorFindingsPage } from "@/features/vendors/components/vendor-findings-page";
import { VendorRosterPage } from "@/features/vendors/components/vendor-roster-page";
import { VendorDetailPage } from "@/features/vendors/components/vendor-detail-page";
import { VendorPortalPage } from "@/features/vendors/components/vendor-portal-page";
import { VendorQuestionnairesPage } from "@/features/vendors/components/vendor-questionnaires-page";
import { QuestionnaireBuilderPage } from "@/features/vendors/components/questionnaire-builder-page";
import { ConnectionsLayout } from "@/features/connectors/components/connections-layout";
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

      {/* The vendor questionnaire. A third party with no account opens this from
          an emailed link, so it sits outside RequireAuth entirely — and outside
          PublicOnly too, since one of our own people may open it while signed
          in. The page never calls apiFetch: that client would attach their
          bearer token and sign them out on the portal's 401. */}
      <Route path="/vendor-portal/:token" element={<VendorPortalPage />} />

      {/* Reset link is reachable whether or not signed in — a signed-in user's
          reset revokes their current session by construction. */}
      <Route path="/reset-password" element={<ResetPasswordPage />} />

      <Route element={<RequireAuth />}>
        {/* Full-screen policy editor — its own tab, no app shell (ADR-0012). */}
        <Route
          path="documents/:documentId/edit"
          element={<DocumentEditorPage />}
        />
        <Route element={<AppLayout />}>
          <Route index element={<Navigate to="/quick-start" replace />} />
          <Route path="quick-start" element={<QuickStartPage />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="frameworks" element={<FrameworksLayout />}>
            {/* Frameworks opens on the compliance dashboard: the posture read is
                what people come here for; the framework list is a tab. */}
            <Route
              index
              element={<Navigate to="/frameworks/dashboard" replace />}
            />
            <Route path="dashboard" element={<ComplianceDashboardPage />} />
            <Route path="list" element={<FrameworksPage />} />
            <Route path="scope" element={<ScopePage />} />
            <Route path="coverage" element={<CoveragePage />} />
          </Route>
          {/* Detail sits outside the tab strip: it is a drill-down, not a tab. */}
          <Route
            path="frameworks/:frameworkId"
            element={<FrameworkDetailPage />}
          />
          <Route path="controls" element={<ControlsPage />} />
          <Route path="controls/:controlId" element={<ControlDetailPage />} />
          <Route path="evidence" element={<EvidencePage />} />
          <Route path="evidence/:evidenceId" element={<EvidenceDetailPage />} />
          <Route path="documents" element={<DocumentsRegisterPage />} />
          <Route path="documents/campaigns/:campaignId" element={<CampaignPage />} />
          <Route
            path="documents/:documentId/approvals/:tier"
            element={<DocumentApprovalPage />}
          />
          <Route path="documents/:documentId" element={<DocumentDetailPage />} />
          <Route path="tasks" element={<TasksLayout />}>
            <Route index element={<TasksRegisterPage />} />
            <Route path="overview" element={<TasksOverviewPage />} />
            <Route path="automations" element={<Navigate to="/tasks/settings" replace />} />
            <Route path="settings" element={<TasksSettingsPage />} />
          </Route>
          <Route path="tasks/:taskId" element={<TaskDetailPage />} />
          <Route path="assets" element={<AssetsLayout />}>
            <Route index element={<AssetsRegisterPage />} />
            <Route path="overview" element={<AssetsOverviewPage />} />
          </Route>
          <Route path="assets/import" element={<AssetsImportPage />} />
          <Route path="assets/:assetId" element={<AssetDetailPage />} />
          <Route path="vendors" element={<VendorsLayout />}>
            <Route index element={<VendorsRegisterPage />} />
            {/* Literal segments only — the :vendorId route is a sibling below,
                so nothing here can be captured by it. */}
            <Route path="overview" element={<VendorsOverviewPage />} />
            <Route path="intake" element={<VendorIntakePage />} />
            <Route path="findings" element={<VendorFindingsPage />} />
            <Route path="questionnaires" element={<VendorQuestionnairesPage />} />
            <Route path="roster" element={<VendorRosterPage />} />
          </Route>
          <Route
            path="vendors/questionnaires/:questionnaireId"
            element={<QuestionnaireBuilderPage />}
          />
          <Route path="vendors/:vendorId" element={<VendorDetailPage />} />
          <Route path="vulnerabilities" element={<VulnerabilitiesRegisterPage />} />
          <Route path="vulnerabilities/overview" element={<VulnerabilitiesOverviewPage />} />
          <Route path="vulnerabilities/import" element={<VulnerabilitiesImportPage />} />
          {/* Literal segments must precede the :instanceId route below. */}
          <Route path="vulnerabilities/settings" element={<VulnerabilitiesSettingsPage />} />
          <Route path="vulnerabilities/:instanceId" element={<VulnerabilityDetailPage />} />
          <Route
            path="scope"
            element={<Navigate to="/frameworks/scope" replace />}
          />
          <Route path="connectors" element={<ConnectionsLayout />}>
            <Route index element={<ConnectionsPage />} />
          </Route>
          {/* People and Company profile live under Settings; keep old paths working. */}
          <Route
            path="people"
            element={<Navigate to="/settings/access/people" replace />}
          />
          <Route
            path="company-profile"
            element={<Navigate to="/settings/organization/profile" replace />}
          />
          <Route path="settings" element={<SettingsLayout />}>
            <Route index element={<Navigate to="access/people" replace />} />

            {/* Access Management — People / Groups / Roles as top tabs */}
            <Route
              path="access"
              element={<SettingsSection categoryId="access" />}
            >
              <Route index element={<Navigate to="people" replace />} />
              <Route path="people" element={<TeamPage />} />
              <Route path="groups" element={<GroupsPage />} />
              <Route path="roles" element={<RolesPage />} />
            </Route>

            {/* Security — MFA and password policy now; Authentication / SSO later */}
            <Route
              path="security"
              element={<SettingsSection categoryId="security" />}
            >
              <Route index element={<Navigate to="mfa" replace />} />
              <Route path="mfa" element={<SecurityPage />} />
              <Route path="password" element={<PasswordPolicyPage />} />
            </Route>

            {/* Organization — Org info now; Key personnel arrives later */}
            <Route
              path="organization"
              element={<SettingsSection categoryId="organization" />}
            >
              <Route index element={<Navigate to="profile" replace />} />
              <Route path="profile" element={<CompanyProfilePage />} />
            </Route>

            {/* Workflow — the configurer arrives with the task engine */}
            <Route
              path="workflow"
              element={<SettingsSection categoryId="workflow" />}
            >
              <Route
                index
                element={<ComingSoonPage title="Workflow configurer" />}
              />
            </Route>

            {/* Integrations — every tab is Phase 2 */}
            <Route
              path="integrations"
              element={<SettingsSection categoryId="integrations" />}
            >
              <Route
                index
                element={
                  <ComingSoonPage
                    title="Integrations"
                    description="API keys, webhooks and app integrations arrive in a later phase."
                  />
                }
              />
            </Route>

            {/* Back-compat: the old flat settings paths */}
            <Route
              path="team"
              element={<Navigate to="/settings/access/people" replace />}
            />
            <Route
              path="people"
              element={<Navigate to="/settings/access/people" replace />}
            />
            <Route
              path="groups"
              element={<Navigate to="/settings/access/groups" replace />}
            />
            <Route
              path="roles"
              element={<Navigate to="/settings/access/roles" replace />}
            />
            <Route
              path="company"
              element={<Navigate to="/settings/organization/profile" replace />}
            />
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
                description="That route is not part of the current shell. Check the address, or head back to the dashboard."
              />
            }
          />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/sign-in" replace />} />
    </Routes>
  );
}
