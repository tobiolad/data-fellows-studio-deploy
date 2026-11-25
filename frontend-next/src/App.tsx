import { Navigate, Route, Routes } from "react-router-dom"
import { useAuth } from "@/lib/auth"
import { RequireAuth } from "@/components/RequireAuth"
import { SignInPage } from "@/pages/SignIn"
import { SsoCallbackPage } from "@/pages/SsoCallback"
import { PendingApprovalPage } from "@/pages/PendingApproval"
import { ReferralRedirectPage } from "@/pages/ReferralRedirect"
import { ReferralStatsPage } from "@/pages/ReferralStats"
import { ComingSoonPage } from "@/pages/ComingSoon"
import { AdminOverviewPage } from "@/pages/admin/Overview"
import { AdminReferralsPage } from "@/pages/admin/Referrals"
import { AdminApplicationsPage } from "@/pages/admin/Applications"
import { AdminApplicationDetailPage } from "@/pages/admin/ApplicationDetail"
import { AdminEngagementsPage } from "@/pages/admin/Engagements"
import { AdminProjectsPage } from "@/pages/admin/Projects"
import { AdminProjectDetailPage } from "@/pages/admin/ProjectDetail"
import { AdminAiOperationsPage } from "@/pages/admin/AiOperations"
import { AdminAccountsPage } from "@/pages/admin/Accounts"
import { AdminProfessionalsPage } from "@/pages/admin/Professionals"
import { AdminSettingsPage } from "@/pages/admin/Settings"
import { ClientOverviewPage } from "@/pages/client/Overview"
import { ClientProjectsPage } from "@/pages/client/Projects"
import { ClientDeliverablesPage } from "@/pages/client/Deliverables"
import { ClientBillingPage } from "@/pages/client/Billing"
import { ClientMessagesPage } from "@/pages/client/Messages"
import { ProfessionalOverviewPage } from "@/pages/professional/Overview"
import { ProfileWizardPage } from "@/pages/professional/ProfileWizard"
import { ProfessionalDeliverablesPage } from "@/pages/professional/Deliverables"
import { ProfessionalAssignmentsPage } from "@/pages/professional/Assignments"
import { ProfessionalOpportunitiesPage } from "@/pages/professional/Opportunities"
import { ProfessionalApplicationPage } from "@/pages/professional/Application"
import { ReviewerOverviewPage } from "@/pages/reviewer/Overview"

export function App() {
  const { session } = useAuth()

  return (
    <Routes>
      <Route path="/sign-in" element={<SignInPage />} />
      <Route path="/sso-callback" element={<SsoCallbackPage />} />
      <Route path="/pending-approval" element={<PendingApprovalPage />} />
      <Route path="/r/view/:token" element={<ReferralStatsPage />} />
      <Route path="/r/:code" element={<ReferralRedirectPage />} />

      <Route path="/admin" element={<RequireAuth role="admin"><AdminOverviewPage /></RequireAuth>} />
      <Route path="/admin/engagements" element={<RequireAuth role="admin"><AdminEngagementsPage /></RequireAuth>} />
      <Route path="/admin/projects" element={<RequireAuth role="admin"><AdminProjectsPage /></RequireAuth>} />
      <Route path="/admin/projects/:id" element={<RequireAuth role="admin"><AdminProjectDetailPage /></RequireAuth>} />
      <Route path="/admin/accounts" element={<RequireAuth role="admin"><AdminAccountsPage /></RequireAuth>} />
      <Route path="/admin/professionals" element={<RequireAuth role="admin"><AdminProfessionalsPage /></RequireAuth>} />
      <Route path="/admin/applications" element={<RequireAuth role="admin"><AdminApplicationsPage /></RequireAuth>} />
      <Route path="/admin/applications/:id" element={<RequireAuth role="admin"><AdminApplicationDetailPage /></RequireAuth>} />
      <Route path="/admin/ai" element={<RequireAuth role="admin"><AdminAiOperationsPage /></RequireAuth>} />
      <Route path="/admin/referrals" element={<RequireAuth role="admin"><AdminReferralsPage /></RequireAuth>} />
      <Route path="/admin/settings" element={<RequireAuth role="admin"><AdminSettingsPage /></RequireAuth>} />

      <Route path="/client" element={<RequireAuth role="client"><ClientOverviewPage /></RequireAuth>} />
      <Route path="/client/projects" element={<RequireAuth role="client"><ClientProjectsPage /></RequireAuth>} />
      <Route path="/client/deliverables" element={<RequireAuth role="client"><ClientDeliverablesPage /></RequireAuth>} />
      <Route path="/client/messages" element={<RequireAuth role="client"><ClientMessagesPage /></RequireAuth>} />
      <Route path="/client/billing" element={<RequireAuth role="client"><ClientBillingPage /></RequireAuth>} />
      <Route path="/client/support" element={<RequireAuth role="client"><ComingSoonPage title="Support" /></RequireAuth>} />

      <Route path="/professional" element={<RequireAuth role="professional"><ProfessionalOverviewPage /></RequireAuth>} />
      <Route path="/professional/profile" element={<RequireAuth role="professional"><ProfileWizardPage /></RequireAuth>} />
      <Route path="/professional/opportunities" element={<RequireAuth role="professional"><ProfessionalOpportunitiesPage /></RequireAuth>} />
      <Route path="/professional/application" element={<RequireAuth role="professional"><ProfessionalApplicationPage /></RequireAuth>} />
      <Route path="/professional/assignments" element={<RequireAuth role="professional"><ProfessionalAssignmentsPage /></RequireAuth>} />
      <Route path="/professional/deliverables" element={<RequireAuth role="professional"><ProfessionalDeliverablesPage /></RequireAuth>} />

      <Route path="/reviewer" element={<RequireAuth role="reviewer"><ReviewerOverviewPage /></RequireAuth>} />
      <Route path="/reviewer/admissions" element={<RequireAuth role="reviewer"><AdminApplicationsPage /></RequireAuth>} />
      <Route path="/reviewer/admissions/:id" element={<RequireAuth role="reviewer"><AdminApplicationDetailPage /></RequireAuth>} />

      <Route path="/" element={<Navigate to={session ? `/${session.role}` : "/sign-in"} replace />} />
      <Route path="*" element={<Navigate to={session ? `/${session.role}` : "/sign-in"} replace />} />
    </Routes>
  )
}
