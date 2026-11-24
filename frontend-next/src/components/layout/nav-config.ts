import type { LucideIcon } from "lucide-react"
import {
  Banknote,
  Bell,
  Briefcase,
  Building2,
  FileCheck2,
  Gift,
  LayoutDashboard,
  LifeBuoy,
  MessageSquare,
  Settings,
  ShieldCheck,
  Sparkles,
  UserCheck,
  UserCircle,
  Users,
} from "lucide-react"
import type { Role } from "@/lib/types"

export interface NavItem {
  label: string
  to: string
  icon: LucideIcon
  badgeKey?: string
}

export interface NavSection {
  label?: string
  items: NavItem[]
}

export const PORTAL_LABEL: Record<Role, string> = {
  admin: "Mission Control",
  client: "Client portal",
  professional: "Professional portal",
  reviewer: "Review workspace",
}

export const NAV_CONFIG: Record<Role, NavSection[]> = {
  admin: [
    { items: [{ label: "Overview", to: "/admin", icon: LayoutDashboard }] },
    {
      label: "Delivery",
      items: [
        { label: "Clients & engagements", to: "/admin/engagements", icon: Building2 },
        { label: "Projects", to: "/admin/projects", icon: Briefcase },
      ],
    },
    {
      label: "People",
      items: [
        { label: "Professional network", to: "/admin/professionals", icon: Users },
        { label: "Applications & vetting", to: "/admin/applications", icon: FileCheck2, badgeKey: "pending_applications" },
        { label: "People awaiting access", to: "/admin/accounts", icon: UserCheck },
      ],
    },
    {
      label: "Operations",
      items: [
        { label: "AI operations", to: "/admin/ai", icon: Sparkles, badgeKey: "ai_pending_approval" },
        { label: "Referral program", to: "/admin/referrals", icon: Gift },
      ],
    },
    { label: "Administration", items: [{ label: "Settings", to: "/admin/settings", icon: Settings }] },
  ],
  client: [
    { items: [{ label: "Overview", to: "/client", icon: LayoutDashboard }] },
    {
      items: [
        { label: "Projects & engagements", to: "/client/projects", icon: Briefcase },
        { label: "Deliverables", to: "/client/deliverables", icon: FileCheck2 },
        { label: "Messages", to: "/client/messages", icon: MessageSquare },
        { label: "Billing", to: "/client/billing", icon: Banknote },
        { label: "Support", to: "/client/support", icon: LifeBuoy },
      ],
    },
  ],
  professional: [
    { items: [{ label: "Overview", to: "/professional", icon: LayoutDashboard }] },
    {
      items: [
        { label: "Opportunities", to: "/professional/opportunities", icon: Sparkles },
        { label: "My application", to: "/professional/application", icon: FileCheck2 },
        { label: "My assignments", to: "/professional/assignments", icon: Briefcase },
        { label: "Deliverables", to: "/professional/deliverables", icon: FileCheck2 },
        { label: "Profile", to: "/professional/profile", icon: UserCircle },
      ],
    },
  ],
  reviewer: [
    { items: [{ label: "Submission review", to: "/reviewer", icon: FileCheck2 }] },
    { items: [{ label: "Admission review", to: "/reviewer/admissions", icon: ShieldCheck }] },
  ],
}

export const ROLE_ICON: Record<Role, LucideIcon> = {
  admin: ShieldCheck,
  client: Building2,
  professional: Sparkles,
  reviewer: Bell,
}
