import { useQuery } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import { ArrowUpRight, Briefcase, Mail, Sparkles } from "lucide-react"
import { AppShell } from "@/components/layout/AppShell"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { api, ApiError } from "@/lib/api"
import { useAuth } from "@/lib/auth"
import { usePreviewedProfessionalId } from "@/lib/view-as"
import type { AdmissionApplication, Assignment } from "@/lib/types"

const STATUS_LABEL: Record<string, string> = {
  invited: "Invitation pending",
  accepted: "Accepted",
  declined: "Declined",
  expired: "Expired",
  revoked: "Revoked",
}

export function ProfessionalOverviewPage() {
  const { session } = useAuth()
  const actorId = usePreviewedProfessionalId(session!.actorId)

  const assignments = useQuery({
    queryKey: ["assignments", actorId],
    queryFn: () => api.get<Assignment[]>(`/professionals/${encodeURIComponent(actorId)}/assignments`),
  })

  const application = useQuery({
    queryKey: ["application", actorId],
    queryFn: async () => {
      try {
        return await api.get<AdmissionApplication>(`/professionals/${encodeURIComponent(actorId)}/application`)
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) return null
        throw error
      }
    },
  })

  const active = assignments.data?.filter((item) => item.status === "accepted") ?? []
  const pending = assignments.data?.filter((item) => item.status === "invited") ?? []

  return (
    <AppShell title="Assignment overview" description="Review your accepted work and outstanding invitations.">
      <div className="space-y-6">
        {application.data === null && (
          <Card className="border-primary/30 bg-primary/5">
            <CardContent className="flex flex-col items-start justify-between gap-4 p-6 sm:flex-row sm:items-center">
              <div className="flex items-start gap-3">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                  <Sparkles className="h-[18px] w-[18px]" />
                </span>
                <div>
                  <p className="font-heading text-base font-semibold text-foreground">Become a Data Fellows professional</p>
                  <p className="text-sm text-muted-foreground">
                    Build your profile and submit it for independent review in a few minutes.
                  </p>
                </div>
              </div>
              <Button asChild>
                <Link to="/professional/profile">Start your profile</Link>
              </Button>
            </CardContent>
          </Card>
        )}

        {application.data && application.data.status !== "approved" && (
          <Card>
            <CardContent className="flex items-center justify-between p-5">
              <div>
                <p className="text-sm font-medium text-foreground">Application status</p>
                <p className="text-xs text-muted-foreground">Submitted {new Date(application.data.submitted_at).toLocaleDateString()}</p>
              </div>
              <Badge variant="secondary" className="capitalize">
                {application.data.status.replace("_", " ")}
              </Badge>
            </CardContent>
          </Card>
        )}

        {assignments.isLoading && (
          <div className="grid gap-4 sm:grid-cols-2">
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
          </div>
        )}

        {assignments.data && (
          <div className="grid gap-4 sm:grid-cols-2">
            <Card>
              <CardContent className="flex items-center gap-3.5 p-5">
                <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <Briefcase className="h-4 w-4" />
                </span>
                <div>
                  <p className="font-heading text-xl font-semibold text-foreground">{active.length}</p>
                  <p className="text-xs text-muted-foreground">Active assignments</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="flex items-center gap-3.5 p-5">
                <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-400">
                  <Mail className="h-4 w-4" />
                </span>
                <div>
                  <p className="font-heading text-xl font-semibold text-foreground">{pending.length}</p>
                  <p className="text-xs text-muted-foreground">Pending invitations</p>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        <Card>
          <CardHeader>
            <CardTitle className="text-base">My assignments</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {assignments.data?.length === 0 && (
              <p className="px-6 pb-6 text-sm text-muted-foreground">No assignments yet. Approved opportunities will appear here.</p>
            )}
            {assignments.data?.map((item) => (
              <div key={item.id} className="flex items-center justify-between gap-4 border-t border-border px-6 py-3.5 first:border-t-0">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-foreground">{item.title}</p>
                  <p className="truncate text-xs text-muted-foreground">{item.project_name}</p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <Badge variant="secondary">{STATUS_LABEL[item.status] ?? item.status}</Badge>
                  <ArrowUpRight className="h-3.5 w-3.5 text-muted-foreground" />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </AppShell>
  )
}
