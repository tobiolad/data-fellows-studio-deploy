import { useQuery } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import { ArrowUpRight, Bot, Briefcase, FileCheck2, Users } from "lucide-react"
import { AppShell } from "@/components/layout/AppShell"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api"
import type { AdminOverview } from "@/lib/types"
import { cn } from "@/lib/utils"

function StatTile({ label, value, icon: Icon, hint }: { label: string; value: number; icon: typeof Users; hint?: string }) {
  return (
    <Card>
      <CardContent className="flex items-start justify-between p-5">
        <div>
          <p className="text-xs font-medium text-muted-foreground">{label}</p>
          <p className="mt-1.5 font-heading text-2xl font-semibold tracking-tight text-foreground">{value}</p>
          {hint && <p className="mt-0.5 text-xs text-muted-foreground">{hint}</p>}
        </div>
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <Icon className="h-4 w-4" />
        </span>
      </CardContent>
    </Card>
  )
}

const STATUS_STYLES: Record<string, string> = {
  active: "bg-blue-500/10 text-blue-600 dark:text-blue-400",
  completed: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  cancelled: "bg-muted text-muted-foreground",
}

export function AdminOverviewPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["admin-overview"],
    queryFn: () => api.get<AdminOverview>("/admin/overview"),
  })

  return (
    <AppShell
      title="Mission Control"
      description="Coordinate engagements, delivery, AI execution and quality across Data Fellows."
    >
      {isLoading && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-24" />
          ))}
        </div>
      )}

      {error && (
        <Card className="border-destructive/40 bg-destructive/5">
          <CardContent className="p-5 text-sm text-destructive">Couldn't load Mission Control. {(error as Error).message}</CardContent>
        </Card>
      )}

      {data && (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatTile label="Active engagements" value={data.metrics.active_engagements} icon={Briefcase} hint="Authorized client work" />
            <StatTile label="Awaiting review" value={data.metrics.awaiting_review} icon={FileCheck2} hint="Deliverables under review" />
            <StatTile label="Pending applications" value={data.metrics.pending_applications} icon={Users} hint="Professional vetting" />
            <StatTile label="AI awaiting approval" value={data.metrics.ai_pending_approval} icon={Bot} hint="Human decision required" />
          </div>

          <div className="grid gap-4 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-base">Recent projects</CardTitle>
                <Link to="/admin/projects" className="flex items-center gap-1 text-xs font-medium text-primary hover:underline">
                  View all <ArrowUpRight className="h-3 w-3" />
                </Link>
              </CardHeader>
              <CardContent className="p-0">
                {data.projects.length === 0 ? (
                  <p className="px-6 pb-6 text-sm text-muted-foreground">No projects yet. Create an engagement to get started.</p>
                ) : (
                  <div className="divide-y divide-border">
                    {data.projects.slice(0, 6).map((project) => (
                      <div key={project.id} className="flex items-center justify-between gap-4 px-6 py-3.5">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium text-foreground">{project.name}</p>
                          <p className="truncate text-xs text-muted-foreground">
                            {project.organization_name} · {project.work_package_count ?? 0} work packages
                          </p>
                        </div>
                        <Badge variant="secondary" className={cn("shrink-0 capitalize", STATUS_STYLES[project.status])}>
                          {project.status}
                        </Badge>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Recent activity</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3.5">
                {data.audit.length === 0 && <p className="text-sm text-muted-foreground">No recorded changes yet.</p>}
                {data.audit.slice(0, 6).map((event, index) => (
                  <div key={index} className="flex items-start gap-2.5 text-xs">
                    <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                    <div>
                      <p className="font-medium text-foreground">{event.action}</p>
                      <p className="text-muted-foreground">{event.actor_id}</p>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </AppShell>
  )
}
