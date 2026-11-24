import { type ReactNode, useState } from "react"
import { Link, useLocation, useNavigate } from "react-router-dom"
import { LogOut, Menu, X } from "lucide-react"
import { useAuth } from "@/lib/auth"
import { NAV_CONFIG, PORTAL_LABEL, ROLE_ICON } from "@/components/layout/nav-config"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

interface AppShellProps {
  children: ReactNode
  title: string
  description?: string
  actions?: ReactNode
  badges?: Record<string, number>
}

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const { session, signOut } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  if (!session) return null
  const sections = NAV_CONFIG[session.role]

  return (
    <div className="flex h-full flex-col text-sidebar-foreground">
      <div className="flex items-center gap-2.5 px-5 pt-6 pb-4">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-sidebar-primary font-heading text-sm font-semibold text-sidebar-primary-foreground">
          D
        </div>
        <div className="leading-tight">
          <p className="text-sm font-semibold">Data Fellows</p>
          <p className="text-xs text-sidebar-foreground/60">Studio</p>
        </div>
      </div>

      <nav className="flex-1 space-y-5 overflow-y-auto px-3 pb-4">
        {sections.map((section, index) => (
          <div key={section.label ?? index}>
            {section.label && (
              <p className="px-2.5 pb-1.5 text-[11px] font-medium uppercase tracking-wider text-sidebar-foreground/40">
                {section.label}
              </p>
            )}
            <div className="space-y-0.5">
              {section.items.map((item) => {
                const active = location.pathname === item.to
                return (
                  <Link
                    key={item.to}
                    to={item.to}
                    onClick={onNavigate}
                    className={cn(
                      "flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-[13px] font-medium transition-colors",
                      active
                        ? "bg-sidebar-accent text-sidebar-accent-foreground"
                        : "text-sidebar-foreground/70 hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground",
                    )}
                  >
                    <item.icon className="h-4 w-4 shrink-0" />
                    <span className="truncate">{item.label}</span>
                  </Link>
                )
              })}
            </div>
          </div>
        ))}
      </nav>

      <div className="border-t border-sidebar-border px-3 py-3">
        <button
          onClick={() => {
            signOut()
            navigate("/sign-in")
          }}
          className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-[13px] font-medium text-sidebar-foreground/60 transition-colors hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground"
        >
          <LogOut className="h-4 w-4" />
          Switch workspace
        </button>
      </div>
    </div>
  )
}

export function AppShell({ children, title, description, actions }: AppShellProps) {
  const { session } = useAuth()
  const [mobileOpen, setMobileOpen] = useState(false)
  if (!session) return null
  const RoleIcon = ROLE_ICON[session.role]

  return (
    <div className="flex min-h-svh bg-background">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 bg-sidebar lg:block">
        <SidebarContent />
      </aside>

      {mobileOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-black/40" onClick={() => setMobileOpen(false)} />
          <div className="absolute inset-y-0 left-0 w-64 bg-sidebar shadow-xl">
            <div className="flex justify-end p-3">
              <Button variant="ghost" size="icon" className="text-sidebar-foreground" onClick={() => setMobileOpen(false)}>
                <X className="h-4 w-4" />
              </Button>
            </div>
            <SidebarContent onNavigate={() => setMobileOpen(false)} />
          </div>
        </div>
      )}

      <div className="flex min-h-svh flex-1 flex-col lg:pl-64">
        <header className="sticky top-0 z-20 flex items-center justify-between gap-4 border-b border-border bg-background/95 px-4 py-3 backdrop-blur supports-[backdrop-filter]:bg-background/80 sm:px-8">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" className="lg:hidden" onClick={() => setMobileOpen(true)}>
              <Menu className="h-4 w-4" />
            </Button>
            <div>
              <h1 className="font-heading text-lg font-semibold leading-tight text-foreground sm:text-xl">{title}</h1>
              {description && <p className="hidden text-xs text-muted-foreground sm:block">{description}</p>}
            </div>
          </div>
          <div className="flex items-center gap-3">
            {actions}
            <div className="hidden items-center gap-2 rounded-full border border-border bg-card py-1 pl-1 pr-3 sm:flex">
              <Avatar className="h-6 w-6">
                <AvatarFallback className="bg-primary/10 text-[11px] font-medium text-primary">
                  {session.actorId.slice(0, 2).toUpperCase()}
                </AvatarFallback>
              </Avatar>
              <span className="text-xs font-medium text-foreground">{session.actorId}</span>
              <Badge variant="secondary" className="gap-1 px-1.5 py-0 text-[10px]">
                <RoleIcon className="h-2.5 w-2.5" />
                {PORTAL_LABEL[session.role]}
              </Badge>
            </div>
          </div>
        </header>

        <main className="flex-1 px-4 py-6 sm:px-8 sm:py-8">
          <div className="mx-auto w-full max-w-6xl">{children}</div>
        </main>
      </div>
    </div>
  )
}
