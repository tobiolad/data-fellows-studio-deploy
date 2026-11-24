import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { Check, Mail, X } from "lucide-react"
import { AppShell } from "@/components/layout/AppShell"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api"
import { useAuth } from "@/lib/auth"
import type { Assignment } from "@/lib/types"

const STATUS_STYLES: Record<string, string> = {
  invited: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
  accepted: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  declined: "bg-muted text-muted-foreground",
  expired: "bg-muted text-muted-foreground",
  revoked: "bg-destructive/10 text-destructive",
}

export function ProfessionalAssignmentsPage() {
  const { session } = useAuth()
  const actorId = session!.actorId
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ["assignments", actorId],
    queryFn: () => api.get<Assignment[]>(`/professionals/${encodeURIComponent(actorId)}/assignments`),
  })

  const decide = useMutation({
    mutationFn: ({ id, decision }: { id: string; decision: "accept" | "decline" }) =>
      api.post(`/assignments/${encodeURIComponent(id)}/${decision}`),
    onSuccess: (_data, variables) => {
      toast.success(variables.decision === "accept" ? "Assignment accepted" : "Assignment declined")
      queryClient.invalidateQueries({ queryKey: ["assignments", actorId] })
    },
    onError: (error) => toast.error((error as Error).message),
  })

  return (
    <AppShell title="My assignments" description="Accept or decline invitations, and track active work.">
      <div className="space-y-3">
        {isLoading && <Skeleton className="h-20" />}
        {data?.length === 0 && (
          <Card className="border-dashed">
            <CardContent className="py-14 text-center text-sm text-muted-foreground">
              No assignments yet. Opportunities you're invited to will appear here.
            </CardContent>
          </Card>
        )}
        {data?.map((item) => (
          <Card key={item.id}>
            <CardContent className="flex items-center justify-between gap-4 p-5">
              <div className="min-w-0">
                <p className="truncate font-medium text-foreground">{item.title}</p>
                <p className="truncate text-xs text-muted-foreground">{item.project_name} · {item.engagement_name}</p>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                {item.status === "invited" ? (
                  <>
                    <Button size="sm" onClick={() => decide.mutate({ id: item.id, decision: "accept" })} disabled={decide.isPending}>
                      <Check className="h-3.5 w-3.5" /> Accept
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => decide.mutate({ id: item.id, decision: "decline" })} disabled={decide.isPending}>
                      <X className="h-3.5 w-3.5" /> Decline
                    </Button>
                  </>
                ) : (
                  <Badge variant="secondary" className={STATUS_STYLES[item.status]}>
                    {item.status}
                  </Badge>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {data && data.some((item) => item.status === "invited") && (
        <p className="mt-4 flex items-center gap-1.5 text-xs text-muted-foreground">
          <Mail className="h-3 w-3" /> Invitations may expire — respond promptly.
        </p>
      )}
    </AppShell>
  )
}
