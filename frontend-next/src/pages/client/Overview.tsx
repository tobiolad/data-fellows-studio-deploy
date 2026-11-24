import { useQuery } from "@tanstack/react-query"
import { ArrowUpRight, CheckCircle2, FileCheck2, Folder, PackageCheck } from "lucide-react"
import { AppShell } from "@/components/layout/AppShell"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api"
import type { ClientOverview } from "@/lib/types"

function StatTile({ label, value, icon: Icon }: { label: string; value: number; icon: typeof Folder }) {
  return (
    <Card>
      <CardContent className="flex items-center gap-3.5 p-5">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <Icon className="h-4 w-4" />
        </span>
        <div>
          <p className="font-heading text-xl font-semibold tracking-tight text-foreground">{value}</p>
          <p className="text-xs text-muted-foreground">{label}</p>
        </div>
      </CardContent>
    </Card>
  )
}

export function ClientOverviewPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["client-overview"],
    queryFn: () => api.get<ClientOverview>("/client/overview"),
  })

  return (
    <AppShell title="Your delivery overview" description="Track approved work, decisions and progress with Data Fellows.">
      {isLoading && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-20" />
          ))}
        </div>
      )}

      {error && (
        <Card className="border-dashed">
          <CardContent className="py-12 text-center text-sm text-muted-foreground">
            {(error as Error).message || "No workspace is linked to this account yet."}
          </CardContent>
        </Card>
      )}

      {data && (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatTile label="Active projects" value={data.metrics.active_projects} icon={Folder} />
            <StatTile label="Completed projects" value={data.metrics.completed_projects} icon={CheckCircle2} />
            <StatTile label="Deliverables to review" value={data.metrics.deliverables_for_review} icon={FileCheck2} />
            <StatTile label="Accepted deliverables" value={data.metrics.accepted_deliverables} icon={PackageCheck} />
          </div>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-base">Active projects</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {data.projects.length === 0 && (
                <p className="text-sm text-muted-foreground">No projects authorized yet. Your delivery team will update this once work begins.</p>
              )}
              {data.projects.map((project) => (
                <div key={project.id} className="rounded-xl border border-border p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs font-medium text-primary">{project.organization_name}</p>
                      <p className="font-heading text-base font-semibold text-foreground">{project.name}</p>
                    </div>
                    <Badge variant="secondary" className="capitalize">
                      {project.status}
                    </Badge>
                  </div>
                  <div className="mt-3 space-y-2">
                    {(project.work_packages ?? []).map((pkg) => (
                      <div key={pkg.id} className="flex items-center justify-between rounded-lg bg-muted/50 px-3 py-2 text-sm">
                        <span className="text-foreground">{pkg.title}</span>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className="capitalize">
                            {pkg.status.replace("_", " ")}
                          </Badge>
                          {pkg.deliverables && pkg.deliverables.length > 0 && (
                            <a href="#" className="flex items-center gap-0.5 text-xs font-medium text-primary hover:underline">
                              View <ArrowUpRight className="h-3 w-3" />
                            </a>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      )}
    </AppShell>
  )
}
