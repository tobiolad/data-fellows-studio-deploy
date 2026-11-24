import { Link } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { ArrowUpRight, Briefcase, FileCheck2, Users } from "lucide-react"
import { AppShell } from "@/components/layout/AppShell"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api"
import type { AdmissionListItem, Assignment } from "@/lib/types"

function initialsOf(name: string) {
  const trimmed = name.trim()
  if (!trimmed) return "?"
  const parts = trimmed.split(/\s+/)
  return (parts[0][0] + (parts[1]?.[0] ?? "")).toUpperCase()
}

function ActiveAssignments({ professionalId }: { professionalId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["assignments", professionalId],
    queryFn: () => api.get<Assignment[]>(`/professionals/${encodeURIComponent(professionalId)}/assignments`),
  })
  const active = (data ?? []).filter((item) => item.status === "accepted" || item.status === "invited")

  if (isLoading) return <Skeleton className="h-4 w-40" />
  if (active.length === 0) return <p className="text-xs text-muted-foreground">No active assignment right now.</p>
  return (
    <div className="flex flex-wrap gap-1.5">
      {active.map((assignment) => (
        <Badge key={assignment.id} variant="outline" className="gap-1 text-xs">
          <Briefcase className="h-3 w-3" /> {assignment.title ?? "Work package"}
          {assignment.status === "invited" && <span className="text-muted-foreground">(invited)</span>}
        </Badge>
      ))}
    </div>
  )
}

export function AdminProfessionalsPage() {
  const admitted = useQuery({
    queryKey: ["admissions", "approved"],
    queryFn: () => api.get<AdmissionListItem[]>("/professionals/admissions?status_filter=approved"),
  })
  const inReview = useQuery({
    queryKey: ["admissions", "in-review"],
    queryFn: () => api.get<AdmissionListItem[]>("/professionals/admissions"),
  })

  const underReview = (inReview.data ?? []).filter((item) => ["submitted", "under_review", "assessment"].includes(item.status))

  return (
    <AppShell
      title="Professional network"
      description="Everyone admitted to deliver work for Data Fellows, and what they're on right now."
    >
      <div className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-2">
          <Card>
            <CardContent className="flex items-center gap-3.5 p-5">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Users className="h-4 w-4" />
              </span>
              <div>
                <p className="font-heading text-xl font-semibold tracking-tight text-foreground">{admitted.data?.length ?? "–"}</p>
                <p className="text-xs text-muted-foreground">Admitted professionals</p>
              </div>
            </CardContent>
          </Card>
          <Link to="/admin/applications">
            <Card className="transition-colors hover:bg-muted/40">
              <CardContent className="flex items-center gap-3.5 p-5">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-400">
                  <FileCheck2 className="h-4 w-4" />
                </span>
                <div>
                  <p className="font-heading text-xl font-semibold tracking-tight text-foreground">{underReview.length}</p>
                  <p className="text-xs text-muted-foreground">In review · view queue</p>
                </div>
              </CardContent>
            </Card>
          </Link>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Admitted roster</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {admitted.isLoading && <Skeleton className="h-16" />}
            {!admitted.isLoading && admitted.data?.length === 0 && (
              <div className="flex flex-col items-center gap-2 py-14 text-center">
                <span className="flex h-10 w-10 items-center justify-center rounded-full bg-muted text-muted-foreground">
                  <Users className="h-[18px] w-[18px]" />
                </span>
                <p className="text-sm text-muted-foreground">Nobody has been admitted yet. Approved applications show up here.</p>
              </div>
            )}
            {admitted.data?.map((professional) => {
              const name = professional.display_name || professional.professional_id
              return (
                <div key={professional.professional_id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border p-4">
                  <div className="flex items-center gap-3">
                    <Avatar className="h-9 w-9">
                      <AvatarFallback className="bg-primary/10 text-xs font-medium text-primary">{initialsOf(name)}</AvatarFallback>
                    </Avatar>
                    <div>
                      <p className="font-medium text-foreground">{name}</p>
                      <ActiveAssignments professionalId={professional.professional_id} />
                    </div>
                  </div>
                  <Link
                    to={`/admin/applications/${encodeURIComponent(professional.professional_id)}`}
                    className="flex shrink-0 items-center gap-0.5 text-xs font-medium text-primary hover:underline"
                  >
                    View history <ArrowUpRight className="h-3 w-3" />
                  </Link>
                </div>
              )
            })}
          </CardContent>
        </Card>
      </div>
    </AppShell>
  )
}
