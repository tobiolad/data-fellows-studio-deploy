import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { CheckCircle2, ListChecks, RotateCcw } from "lucide-react"
import { AppShell } from "@/components/layout/AppShell"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api"
import type { ReviewQueueItem } from "@/lib/types"

export function ReviewerOverviewPage() {
  const queryClient = useQueryClient()
  const [active, setActive] = useState<{ item: ReviewQueueItem; decision: "approved" | "revision_requested" } | null>(null)
  const [comment, setComment] = useState("")

  const { data, isLoading } = useQuery({
    queryKey: ["reviewer-queue"],
    queryFn: () => api.get<{ items: ReviewQueueItem[]; has_more: boolean }>("/reviewer/queue"),
  })

  const submit = useMutation({
    mutationFn: ({ id, decision, comment }: { id: string; decision: string; comment: string }) =>
      api.post(`/deliverables/${encodeURIComponent(id)}/review`, { decision, comment }),
    onSuccess: () => {
      toast.success(active?.decision === "approved" ? "Deliverable approved" : "Revision requested")
      queryClient.invalidateQueries({ queryKey: ["reviewer-queue"] })
      setActive(null)
      setComment("")
    },
    onError: (error) => toast.error((error as Error).message),
  })

  return (
    <AppShell title="Submission review" description="Independent review decisions and requested revisions.">
      <div className="space-y-4">
        {isLoading && (
          <>
            <Skeleton className="h-32" />
            <Skeleton className="h-32" />
          </>
        )}

        {data && data.items.length === 0 && (
          <Card className="border-dashed">
            <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
              <span className="flex h-11 w-11 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                <ListChecks className="h-5 w-5" />
              </span>
              <p className="text-sm font-medium text-foreground">No submissions are awaiting your review.</p>
            </CardContent>
          </Card>
        )}

        {data?.items.map((item) => (
          <Card key={item.id}>
            <CardHeader className="flex flex-row items-start justify-between gap-4">
              <div>
                <CardTitle className="text-base">{item.title}</CardTitle>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {item.project_name} · {item.package_title} · v{item.version}
                </p>
              </div>
              <Badge variant="secondary">Under review</Badge>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="rounded-lg bg-muted/50 p-3 text-sm text-foreground">{item.content}</p>
              {item.acceptance_criteria.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-muted-foreground">Acceptance criteria</p>
                  <ul className="mt-1 list-inside list-disc text-sm text-foreground">
                    {item.acceptance_criteria.map((criterion, index) => (
                      <li key={index}>{criterion}</li>
                    ))}
                  </ul>
                </div>
              )}
              <div className="flex gap-2 pt-1">
                <Button size="sm" onClick={() => setActive({ item, decision: "approved" })}>
                  <CheckCircle2 className="h-3.5 w-3.5" /> Approve
                </Button>
                <Button size="sm" variant="outline" onClick={() => setActive({ item, decision: "revision_requested" })}>
                  <RotateCcw className="h-3.5 w-3.5" /> Request revision
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Dialog open={!!active} onOpenChange={(open) => !open && setActive(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{active?.decision === "approved" ? "Approve deliverable" : "Request a revision"}</DialogTitle>
            <DialogDescription>{active?.item.title}</DialogDescription>
          </DialogHeader>
          <Textarea
            placeholder="Explain what you checked, or what needs to change…"
            value={comment}
            onChange={(event) => setComment(event.target.value)}
            rows={4}
          />
          <DialogFooter>
            <Button variant="ghost" onClick={() => setActive(null)}>
              Cancel
            </Button>
            <Button
              disabled={!comment.trim() || submit.isPending}
              onClick={() => active && submit.mutate({ id: active.item.id, decision: active.decision, comment })}
            >
              Submit decision
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AppShell>
  )
}
