import { Link } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { ArrowUpRight, Building2, Mail, ShieldCheck, UserCheck } from "lucide-react"
import { AppShell } from "@/components/layout/AppShell"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api"
import { useAuth } from "@/lib/auth"
import type { Me, StudioAccount } from "@/lib/types"

const QUICK_LINKS = [
  { to: "/admin/accounts", label: "People awaiting access", description: "Assign a role to a new Google sign-in.", icon: UserCheck },
  { to: "/admin/engagements", label: "Clients & engagements", description: "Organizations, memberships and engagements.", icon: Building2 },
]

export function AdminSettingsPage() {
  const { session } = useAuth()
  const me = useQuery({ queryKey: ["me"], queryFn: () => api.get<Me>("/me") })
  const accounts = useQuery({
    queryKey: ["accounts"],
    queryFn: () => api.get<StudioAccount[]>("/accounts"),
    enabled: me.data?.authentication === "google",
  })

  const account = accounts.data?.find((item) => item.id === me.data?.id)

  return (
    <AppShell title="Settings" description="Your account and where the rest of Studio's configuration lives.">
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Your account</CardTitle>
          </CardHeader>
          <CardContent>
            {me.isLoading && <Skeleton className="h-16" />}
            {me.data && (
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <Avatar className="h-10 w-10">
                    <AvatarFallback className="bg-primary/10 text-sm font-medium text-primary">
                      {(account?.name || account?.email || me.data.id).slice(0, 2).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  <div>
                    <p className="font-medium text-foreground">{account?.name || "Internal admin"}</p>
                    {account?.email ? (
                      <p className="flex items-center gap-1 text-xs text-muted-foreground">
                        <Mail className="h-3 w-3" /> {account.email}
                      </p>
                    ) : (
                      <p className="text-xs text-muted-foreground">Signed in as {session?.actorId}</p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="secondary" className="gap-1 capitalize">
                    <ShieldCheck className="h-3 w-3" /> {me.data.roles.join(", ")}
                  </Badge>
                  <Badge variant="outline" className="capitalize">
                    {me.data.authentication === "google" ? "Signed in with Google" : me.data.authentication}
                  </Badge>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">More administration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {QUICK_LINKS.map(({ to, label, description, icon: Icon }) => (
              <Link
                key={to}
                to={to}
                className="flex items-center justify-between gap-3 rounded-xl border border-border p-4 transition-colors hover:bg-muted/40"
              >
                <div className="flex items-center gap-3">
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <Icon className="h-4 w-4" />
                  </span>
                  <div>
                    <p className="text-sm font-medium text-foreground">{label}</p>
                    <p className="text-xs text-muted-foreground">{description}</p>
                  </div>
                </div>
                <ArrowUpRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
              </Link>
            ))}
          </CardContent>
        </Card>
      </div>
    </AppShell>
  )
}
