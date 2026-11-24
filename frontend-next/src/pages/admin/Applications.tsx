import { useState } from "react"
import { Link } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { ArrowUpRight, FileCheck2 } from "lucide-react"
import { AppShell } from "@/components/layout/AppShell"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { api } from "@/lib/api"
import { useAuth } from "@/lib/auth"
import type { AdmissionListItem } from "@/lib/types"

const STATUS_OPTIONS = [
  { value: "all", label: "All statuses" },
  { value: "submitted", label: "Submitted" },
  { value: "under_review", label: "Under review" },
  { value: "assessment", label: "Assessment" },
  { value: "approved", label: "Approved" },
  { value: "declined", label: "Declined" },
  { value: "revoked", label: "Revoked" },
]

const STATUS_STYLES: Record<string, string> = {
  submitted: "bg-blue-500/10 text-blue-600 dark:text-blue-400",
  under_review: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
  assessment: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
  approved: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  declined: "bg-muted text-muted-foreground",
  revoked: "bg-destructive/10 text-destructive",
}

export function AdminApplicationsPage() {
  const { session } = useAuth()
  const basePath = session?.role === "reviewer" ? "/reviewer/admissions" : "/admin/applications"
  const [status, setStatus] = useState("all")

  const { data, isLoading } = useQuery({
    queryKey: ["admissions", status],
    queryFn: () =>
      api.get<AdmissionListItem[]>(`/professionals/admissions${status === "all" ? "" : `?status_filter=${status}`}`),
  })

  return (
    <AppShell
      title="Applications & vetting"
      description="Independent review of professional applications. AI screening and assessment tooling plugs in here next."
      actions={
        <Select value={status} onValueChange={setStatus}>
          <SelectTrigger className="w-44">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {STATUS_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      }
    >
      <Card>
        <CardContent className="space-y-2 p-4">
          {isLoading && <Skeleton className="h-16" />}
          {data?.length === 0 && (
            <div className="flex flex-col items-center gap-2 py-14 text-center">
              <span className="flex h-10 w-10 items-center justify-center rounded-full bg-muted text-muted-foreground">
                <FileCheck2 className="h-[18px] w-[18px]" />
              </span>
              <p className="text-sm text-muted-foreground">No applications in this status.</p>
            </div>
          )}
          {data?.map((item) => (
            <Link
              key={item.professional_id}
              to={`${basePath}/${encodeURIComponent(item.professional_id)}`}
              className="flex items-center justify-between gap-4 rounded-lg border border-border px-4 py-3 transition-colors hover:bg-muted/40"
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-foreground">{item.display_name || item.professional_id}</p>
                <p className="truncate text-xs text-muted-foreground">
                  Submitted {new Date(item.created_at).toLocaleDateString()}
                  {item.missing_information.length > 0 && ` · ${item.missing_information.length} item(s) requested`}
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <Badge variant="secondary" className={STATUS_STYLES[item.status]}>
                  {item.status.replace("_", " ")}
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
