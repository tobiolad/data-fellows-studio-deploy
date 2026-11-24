import { Navigate, Route, Routes } from "react-router-dom"
import { useAuth } from "@/lib/auth"
import { RequireAuth } from "@/components/RequireAuth"
import { SignInPage } from "@/pages/SignIn"
import { ReferralRedirectPage } from "@/pages/ReferralRedirect"
import { ReferralStatsPage } from "@/pages/ReferralStats"
import { ComingSoonPage } from "@/pages/ComingSoon"
import { AdminOverviewPage } from "@/pages/admin/Overview"
import { AdminReferralsPage } from "@/pages/admin/Referrals"
import { AdminApplicationsPage } from "@/pages/admin/Applications"
import { AdminApplicationDetailPage } from "@/pages/admin/ApplicationDetail"
import { AdminEngagementsPage } from "@/pages/admin/Engagements"
import { ClientOverviewPage } from "@/pages/client/Overview"
import { ClientDeliverablesPage } from "@/pages/client/Deliverables"
import { ProfessionalOverviewPage } from "@/pages/professional/Overview"
import { ProfileWizardPage } from "@/pages/professional/ProfileWizard"
import { ProfessionalDeliverablesPage } from "@/pages/professional/Deliverables"
import { ProfessionalAssignmentsPage } from "@/pages/professional/Assignments"
import { ReviewerOverviewPage } from "@/pages/reviewer/Overview"

export function App() {
  const { session } = useAuth()

  return (
    <Routes>
      <Route path="/sign-in" element={<SignInPage />} />
      <Route path="/r/view/:token" element={<ReferralStatsPage />} />
      <Route path="/r/:code" element={<ReferralRedirectPage />} />

      <Route path="/admin" element={<RequireAuth role="admin"><AdminOverviewPage /></RequireAuth>} />
      <Route path="/admin/engagements" element={<RequireAuth role="admin"><AdminEngagementsPage /></RequireAuth>} />
      <Route path="/admin/projects" element={<RequireAuth role="admin"><ComingSoonPage title="Projects" /></RequireAuth>} />
      <Route path="/admin/professionals" element={<RequireAuth role="admin"><ComingSoonPage title="Professional network" /></RequireAuth>} />
      <Route path="/admin/applications" element={<RequireAuth role="admin"><AdminApplicationsPage /></RequireAuth>} />
      <Route path="/admin/applications/:id" element={<RequireAuth role="admin"><AdminApplicationDetailPage /></RequireAuth>} />
      <Route path="/admin/ai" element={<RequireAuth role="admin"><ComingSoonPage title="AI operations" /></RequireAuth>} />
      <Route path="/admin/referrals" element={<RequireAuth role="admin"><AdminReferralsPage /></RequireAuth>} />
      <Route path="/admin/settings" element={<RequireAuth role="admin"><ComingSoonPage title="Settings" /></RequireAuth>} />

      <Route path="/client" element={<RequireAuth role="client"><ClientOverviewPage /></RequireAuth>} />
      <Route path="/client/projects" element={<RequireAuth role="client"><ComingSoonPage title="Projects & engagements" /></RequireAuth>} />
      <Route path="/client/deliverables" element={<RequireAuth role="client"><ClientDeliverablesPage /></RequireAuth>} />
      <Route path="/client/messages" element={<RequireAuth role="client"><ComingSoonPage title="Messages" /></RequireAuth>} />
      <Route path="/client/billing" element={<RequireAuth role="client"><ComingSoonPage title="Billing" /></RequireAuth>} />
      <Route path="/client/support" element={<RequireAuth role="client"><ComingSoonPage title="Support" /></RequireAuth>} />

      <Route path="/professional" element={<RequireAuth role="professional"><ProfessionalOverviewPage /></RequireAuth>} />
      <Route path="/professional/profile" element={<RequireAuth role="professional"><ProfileWizardPage /></RequireAuth>} />
      <Route path="/professional/opportunities" element={<RequireAuth role="professional"><ComingSoonPage title="Opportunities" /></RequireAuth>} />
      <Route path="/professional/application" element={<RequireAuth role="professional"><ComingSoonPage title="My application" /></RequireAuth>} />
      <Route path="/professional/assignments" element={<RequireAuth role="professional"><ProfessionalAssignmentsPage /></RequireAuth>} />
      <Route path="/professional/deliverables" element={<RequireAuth role="professional"><ProfessionalDeliverablesPage /></RequireAuth>} />

      <Route path="/reviewer" element={<RequireAuth role="reviewer"><ReviewerOverviewPage /></RequireAuth>} />
      <Route path="/reviewer/admissions" element={<RequireAuth role="reviewer"><ComingSoonPage title="Admission review" /></RequireAuth>} />

      <Route path="/" element={<Navigate to={session ? `/${session.role}` : "/sign-in"} replace />} />
      <Route path="*" element={<Navigate to={session ? `/${session.role}` : "/sign-in"} replace />} />
    </Routes>
  )
}
