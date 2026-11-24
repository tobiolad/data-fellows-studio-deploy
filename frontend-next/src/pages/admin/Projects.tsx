import { Link } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { ArrowUpRight, Briefcase } from "lucide-react"
import { AppShell } from "@/components/layout/AppShell"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api"
import type { AdminOverview } from "@/lib/types"

const STATUS_STYLES: Record<string, string> = {
  active: "bg-blue-500/10 text-blue-600 dark:text-blue-400",
  completed: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  cancelled: "bg-muted text-muted-foreground",
}

export function AdminProjectsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["admin-overview"],
    queryFn: () => api.get<AdminOverview>("/admin/overview"),
  })

  return (
    <AppShell title="Projects" description="Every authorized project across Data Fellows' active engagements.">
      <Card>
        <CardContent className="space-y-2 p-4">
          {isLoading && <Skeleton className="h-16" />}
          {data?.projects.length === 0 && (
            <div className="flex flex-col items-center gap-2 py-14 text-center">
              <Briefcase className="h-5 w-5 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">No projects yet. Create one from Clients & engagements.</p>
            </div>
          )}
          {data?.projects.map((project) => (
            <Link
              key={project.id}
              to={`/admin/projects/${project.id}`}
              className="flex items-center justify-between gap-4 rounded-lg border border-border px-4 py-3.5 transition-colors hover:bg-muted/40"
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-foreground">{project.name}</p>
                <p className="truncate text-xs text-muted-foreground">
                  {project.organization_name} · {project.engagement_name} · {project.work_package_count ?? 0} work packages
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <Badge variant="secondary" className={STATUS_STYLES[project.status]}>
                  {project.status}
                </Badge>
                <ArrowUpRight className="h-3.5 w-3.5 text-muted-foreground" />
              </div>
            </Link>
          ))}
        </CardContent>
      </Card>
    </AppShell>
  )
}
