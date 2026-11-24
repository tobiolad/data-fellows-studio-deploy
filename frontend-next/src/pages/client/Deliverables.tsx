import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { CheckCircle2, FileCheck2, RotateCcw } from "lucide-react"
import { AppShell } from "@/components/layout/AppShell"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api"
import type { ClientOverview, Deliverable } from "@/lib/types"

const STATUS_STYLES: Record<string, string> = {
  under_review: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
  revision_requested: "bg-destructive/10 text-destructive",
  approved: "bg-blue-500/10 text-blue-600 dark:text-blue-400",
  accepted: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
}

export function ClientDeliverablesPage() {
  const queryClient = useQueryClient()
  const [revisionTarget, setRevisionTarget] = useState<Deliverable | null>(null)
  const [comment, setComment] = useState("")

  const { data, isLoading } = useQuery({
    queryKey: ["client-overview"],
    queryFn: () => api.get<ClientOverview>("/client/overview"),
  })

  const accept = useMutation({
    mutationFn: (id: string) => api.post(`/deliverables/${encodeURIComponent(id)}/accept`),
    onSuccess: () => {
      toast.success("Deliverable accepted")
      queryClient.invalidateQueries({ queryKey: ["client-overview"] })
    },
    onError: (error) => toast.error((error as Error).message),
  })

  const requestRevision = useMutation({
    mutationFn: ({ id, comment }: { id: string; comment: string }) =>
      api.post(`/deliverables/${encodeURIComponent(id)}/client-revision`, { comment }),
    onSuccess: () => {
      toast.success("Revision requested")
      queryClient.invalidateQueries({ queryKey: ["client-overview"] })
      setRevisionTarget(null)
      setComment("")
    },
    onError: (error) => toast.error((error as Error).message),
  })

  const deliverables = (data?.projects ?? []).flatMap((project) =>
    (project.work_packages ?? []).flatMap((pkg) =>
      (pkg.deliverables ?? []).map((item) => ({ ...item, projectName: project.name, packageTitle: pkg.title })),
    ),
  )

  return (
    <AppShell title="Deliverables" description="Review internally approved work and record your decision.">
      <div className="space-y-3">
        {isLoading && <Skeleton className="h-24" />}

        {deliverables.length === 0 && !isLoading && (
          <Card className="border-dashed">
            <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
              <span className="flex h-11 w-11 items-center justify-center rounded-full bg-muted text-muted-foreground">
                <FileCheck2 className="h-5 w-5" />
              </span>
              <p className="text-sm text-muted-foreground">Nothing to review yet. Approved deliverables will appear here.</p>
            </CardContent>
          </Card>
        )}

        {deliverables.map((item) => (
          <Card key={item.id}>
            <CardContent className="p-5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-medium text-primary">{item.projectName} · {item.packageTitle}</p>
                  <p className="font-heading text-base font-semibold text-foreground">{item.title}</p>
                  <p className="mt-0.5 text-xs text-muted-foreground">Version {item.version}</p>
                </div>
                <Badge variant="secondary" className={STATUS_STYLES[item.status]}>
                  {item.status.replace("_", " ")}
                </Badge>
              </div>
              <p className="mt-3 rounded-lg bg-muted/50 p-3 text-sm text-foreground">{item.content}</p>
              {item.status === "approved" && (
                <div className="mt-3 flex gap-2">
                  <Button size="sm" onClick={() => accept.mutate(item.id)} disabled={accept.isPending}>
                    <CheckCircle2 className="h-3.5 w-3.5" /> Accept
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => setRevisionTarget(item)}>
                    <RotateCcw className="h-3.5 w-3.5" /> Request revision
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      <Dialog open={!!revisionTarget} onOpenChange={(open) => !open && setRevisionTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Request a revision</DialogTitle>
            <DialogDescription>{revisionTarget?.title} — this doesn't change the current version, it asks your delivery team to follow up.</DialogDescription>
          </DialogHeader>
          <Textarea rows={4} value={comment} onChange={(event) => setComment(event.target.value)} placeholder="What needs to change?" />
          <DialogFooter>
            <Button variant="ghost" onClick={() => setRevisionTarget(null)}>
              Cancel
            </Button>
            <Button
              disabled={!comment.trim() || requestRevision.isPending}
              onClick={() => revisionTarget && requestRevision.mutate({ id: revisionTarget.id, comment })}
            >
              Send request
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AppShell>
  )
}
