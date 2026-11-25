export type Role = "admin" | "client" | "professional" | "reviewer"

export interface Me {
  id: string
  roles: Role[]
  authentication: string
}

export interface Organization {
  id: string
  name: string
  created_at: string
}

export interface Engagement {
  id: string
  organization_id: string
  name: string
  objective: string
  status: "authorized" | "active" | "completed" | "cancelled"
  created_at: string
}

export interface Project {
  id: string
  engagement_id: string
  name: string
  status: "active" | "completed" | "cancelled"
  created_at: string
  engagement_name?: string
  organization_name?: string
  work_package_count?: number
  deliverable_count?: number
  awaiting_review?: number
  work_packages?: WorkPackage[]
}

export interface WorkPackage {
  id: string
  project_id: string
  title: string
  acceptance_criteria: string[]
  status: "unassigned" | "assigned" | "in_progress" | "under_review" | "completed"
  created_at: string
  deliverables?: Deliverable[]
  depends_on?: string[]
}

export interface Deliverable {
  id: string
  work_package_id: string
  version: number
  title: string
  content: string
  submitted_by?: string
  status: "under_review" | "revision_requested" | "approved" | "accepted"
  created_at: string
}

export interface Assignment {
  id: string
  work_package_id: string
  professional_id: string
  status: "invited" | "accepted" | "declined" | "expired" | "revoked"
  expires_at: string | null
  created_at: string
  title?: string
  project_id?: string
  project_name?: string
  engagement_name?: string
  objective?: string
}

export interface EvidenceReference {
  label: string
  reference: string
  classification?: string
  status?: "unverified" | "reviewer verified"
}

export interface ProfessionalProfile {
  professional_id: string
  display_name: string
  headline: string
  bio: string
  skills: string[]
  specializations: string[]
  education: Record<string, string>[]
  experience: Record<string, string>[]
  portfolio: Record<string, string>[]
  evidence_references: EvidenceReference[]
  availability: string
  version: number
  updated_at: string
  application_status?: string
}

export interface AdmissionApplication {
  professional_id: string
  status: "submitted" | "under_review" | "assessment" | "approved" | "declined" | "revoked"
  decided_by: string | null
  decided_at: string | null
  created_at: string
  submitted_at: string
  reviewed_at: string | null
  decision_reason: string
  missing_information: string[]
  assessment_requests: { title: string; detail?: string }[]
  next_action: string
}

export interface AdminOverview {
  organizations: Organization[]
  engagements: Engagement[]
  projects: Project[]
  applications: (AdmissionApplication & { display_name?: string })[]
  deliverables: Deliverable[]
  ai_runs: Record<string, unknown>[]
  audit: { action: string; actor_id: string; resource_type: string; created_at: string }[]
  metrics: {
    active_engagements: number
    active_projects: number
    awaiting_review: number
    client_approvals_pending: number
    pending_applications: number
    open_opportunities: number
    active_assignments: number
    ai_pending_approval: number
    ai_failed: number
  }
}

export interface ClientOverview {
  organizations: Organization[]
  engagements: Engagement[]
  projects: Project[]
  deliverables: Deliverable[]
  metrics: {
    active_projects: number
    completed_projects: number
    deliverables_for_review: number
    accepted_deliverables: number
  }
}

export interface AiAgent {
  id: string
  name: string
  purpose: string
  capability_category: string
  provider: string
  model: string
  model_version: string
  allowed_tools: string[]
  data_access_scope: string
  autonomy_level: string
  requires_human_approval: boolean
  budget_cap_cents: number
  owner_actor_id: string
  status: "active" | "disabled"
  created_at: string
}

export interface AiRunSummary {
  id: string
  work_package_id: string
  requested_by: string
  agent_version: string
  policy_version: string
  budget_cents: number
  spent_cents: number
  status: string
  cancel_requested: boolean
  error_code: string | null
  created_at: string
  work_package_title: string
  project_name: string
  engagement_name: string
  artifact_status: string | null
}

export interface ProjectMessage {
  id: string
  project_id: string
  sender_id: string
  recipient_group: "client" | "professional" | "internal"
  body: string
  created_at: string
}

export interface Opportunity {
  id: string
  title: string
  summary: string
  specialization?: string
  skills: string[]
  compensation?: string
  deadline?: string | null
  status: string
  created_by?: string
  created_at: string
}

export interface AdmissionListItem {
  professional_id: string
  status: "submitted" | "under_review" | "assessment" | "approved" | "declined" | "revoked"
  decided_by: string | null
  decided_at: string | null
  created_at: string
  reviewed_at: string | null
  decision_reason: string
  missing_information: string[]
  assessment_requests: { title: string; detail?: string }[]
  next_action: string
  display_name?: string
}

export interface ReviewQueueItem {
  id: string
  title: string
  version: number
  content: string
  project_name: string
  package_title: string
  acceptance_criteria: string[]
  previous_reviews: { version: number; decision: string; comment: string }[]
}

export interface ReferralLink {
  id: string
  code: string
  partner_name: string
  status: "active" | "disabled"
  created_by: string
  created_at: string
  visit_count: number
  signup_count: number
  view_token: string
}

export interface GoogleSignInResponse {
  access_token: string
  actor_id: string
  email: string
  name: string
  role: Role | null
  pending: boolean
}

export interface SupportRequest {
  id: string
  organization_id: string
  organization_name: string
  submitted_by: string
  subject: string
  body: string
  status: "open" | "resolved"
  resolved_by: string | null
  resolved_at: string | null
  created_at: string
}

export interface Invoice {
  id: string
  organization_id: string
  description: string
  amount_cents: number
  currency: string
  status: "draft" | "open" | "paid" | "void" | "uncollectible"
  hosted_invoice_url: string | null
  created_by: string
  created_at: string
  sent_at: string | null
  paid_at: string | null
}

export type SignupIntent = "professional" | "client" | "team"

export interface StudioAccount {
  id: string
  email: string
  name: string
  avatar_url: string | null
  global_role: Role | null
  created_at: string
  last_login_at: string | null
  signup_intent: SignupIntent | null
}
