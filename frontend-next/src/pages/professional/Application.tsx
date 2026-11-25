import { Link } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { ArrowRight, CheckCircle2, Sparkles } from "lucide-react"
import { AppShell } from "@/components/layout/AppShell"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { api, ApiError } from "@/lib/api"
import { useAuth } from "@/lib/auth"
import { usePreviewedProfessionalId } from "@/lib/view-as"
import type { AdmissionApplication } from "@/lib/types"

const STATUS_STYLES: Record<string, string> = {
  submitted: "bg-blue-500/10 text-blue-600 dark:text-blue-400",
  under_review: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
  assessment: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
  approved: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  declined: "bg-muted text-muted-foreground",
  revoked: "bg-destructive/10 text-destructive",
}

export function ProfessionalApplicationPage() {
  const { session } = useAuth()
  const actorId = usePreviewedProfessionalId(session!.actorId)

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

  if (application.isLoading) {
    return (
      <AppShell title="My application">
        <Skeleton className="h-40" />
      </AppShell>
    )
  }

  return (
    <AppShell title="My application" description="Track admission and opportunity expressions of interest.">
      {!application.data ? (
        <Card className="border-primary/30 bg-primary/5">
          <CardContent className="flex flex-col items-start justify-between gap-4 p-6 sm:flex-row sm:items-center">
            <div className="flex items-start gap-3">
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                <Sparkles className="h-[18px] w-[18px]" />
              </span>
              <div>
                <p className="font-heading text-base font-semibold text-foreground">You haven't applied yet</p>
                <p className="text-sm text-muted-foreground">Build your profile and submit it for independent review.</p>
              </div>
            </div>
            <Button asChild>
              <Link to="/professional/profile">
                Start your profile <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-base">Application status</CardTitle>
              <Badge variant="secondary" className={STATUS_STYLES[application.data.status]}>
                {application.data.status.replace("_", " ")}
              </Badge>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-muted-foreground">Submitted {new Date(application.data.submitted_at).toLocaleDateString()}</p>
              {application.data.decision_reason && (
                <div className="rounded-lg bg-muted/50 p-3 text-sm text-foreground">{application.data.decision_reason}</div>
              )}
              {application.data.missing_information.length > 0 && (
                <div>
                  <p className="mb-1 text-xs font-medium text-muted-foreground">Missing information requested</p>
                  <ul className="list-inside list-disc text-sm text-foreground">
                    {application.data.missing_information.map((item, index) => (
                      <li key={index}>{item}</li>
                    ))}
                  </ul>
                </div>
              )}
              {application.data.assessment_requests.length > 0 && (
                <div>
                  <p className="mb-1 text-xs font-medium text-muted-foreground">Assessments requested</p>
                  <ul className="list-inside list-disc text-sm text-foreground">
                    {application.data.assessment_requests.map((item, index) => (
                      <li key={index}>{item.title}</li>
                    ))}
                  </ul>
                </div>
              )}
              {application.data.next_action && (
                <p className="text-sm font-medium text-foreground">Next step: {application.data.next_action}</p>
              )}
              {application.data.status === "approved" && (
                <p className="flex items-center gap-1.5 text-sm text-emerald-600 dark:text-emerald-400">
                  <CheckCircle2 className="h-4 w-4" /> You're an approved Data Fellows professional.
                </p>
              )}
            </CardContent>
          </Card>
          <Button variant="outline" asChild>
            <Link to="/professional/profile">Edit your profile</Link>
          </Button>
        </div>
      )}
    </AppShell>
  )
}
