import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { FileCheck2, Send } from "lucide-react"
import { AppShell } from "@/components/layout/AppShell"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api"
import { useAuth } from "@/lib/auth"
import { useIsPreviewingProfessional, usePreviewedProfessionalId } from "@/lib/view-as"
import type { Assignment, Deliverable } from "@/lib/types"

const STATUS_STYLES: Record<string, string> = {
  under_review: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
  revision_requested: "bg-destructive/10 text-destructive",
  approved: "bg-blue-500/10 text-blue-600 dark:text-blue-400",
  accepted: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
}

export function ProfessionalDeliverablesPage() {
  const { session } = useAuth()
  const actorId = usePreviewedProfessionalId(session!.actorId)
  const previewing = useIsPreviewingProfessional()
  const queryClient = useQueryClient()
  const [packageId, setPackageId] = useState<string>("")
  const [title, setTitle] = useState("")
  const [content, setContent] = useState("")

  const assignments = useQuery({
    queryKey: ["assignments", actorId],
    queryFn: () => api.get<Assignment[]>(`/professionals/${encodeURIComponent(actorId)}/assignments`),
  })

  const accepted = (assignments.data ?? []).filter((item) => item.status === "accepted")

  const deliverables = useQuery({
    queryKey: ["work-package-deliverables", packageId],
    queryFn: () => api.get<Deliverable[]>(`/work-packages/${encodeURIComponent(packageId)}/deliverables`),
    enabled: !!packageId,
  })

  const submit = useMutation({
    mutationFn: () => api.post("/deliverables", { work_package_id: packageId, title, content }),
    onSuccess: () => {
      toast.success("Deliverable submitted for review")
      setTitle("")
      setContent("")
      queryClient.invalidateQueries({ queryKey: ["work-package-deliverables", packageId] })
    },
    onError: (error) => toast.error((error as Error).message),
  })

  return (
    <AppShell title="Deliverables" description="Submit versioned work products and track review status.">
      <div className="grid gap-6 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Submit for review</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {assignments.isLoading && <Skeleton className="h-10" />}
              <div className="space-y-1.5">
                <Label>Accepted assignment</Label>
                <Select value={packageId} onValueChange={setPackageId}>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Choose an assignment" />
                  </SelectTrigger>
                  <SelectContent>
                    {accepted.map((item) => (
                      <SelectItem key={item.work_package_id} value={item.work_package_id}>
                        {item.title}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {accepted.length === 0 && !assignments.isLoading && (
                  <p className="text-xs text-muted-foreground">You need an accepted assignment before you can submit work.</p>
                )}
              </div>
              <div className="space-y-1.5">
                <Label>Title</Label>
                <Input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="What did you deliver?" />
              </div>
              <div className="space-y-1.5">
                <Label>Submission notes</Label>
                <Textarea rows={4} value={content} onChange={(event) => setContent(event.target.value)} placeholder="Describe what's included and how it meets the acceptance criteria." />
              </div>
              <Button
                className="w-full"
                disabled={previewing || !packageId || title.trim().length < 2 || content.trim().length < 2 || submit.isPending}
                onClick={() => submit.mutate()}
              >
                <Send className="h-3.5 w-3.5" /> {previewing ? "Previewing — read only" : "Submit for review"}
              </Button>
            </CardContent>
          </Card>
        </div>

        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Versions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {!packageId && <p className="text-sm text-muted-foreground">Choose an assignment to see its submission history.</p>}
              {packageId && deliverables.data?.length === 0 && (
                <div className="flex flex-col items-center gap-2 py-8 text-center">
                  <FileCheck2 className="h-5 w-5 text-muted-foreground" />
                  <p className="text-sm text-muted-foreground">No versions submitted yet.</p>
                </div>
              )}
              {deliverables.data?.map((item) => (
                <div key={item.id} className="flex items-center justify-between rounded-lg border border-border px-3 py-2.5">
                  <div>
                    <p className="text-sm font-medium text-foreground">v{item.version} · {item.title}</p>
                  </div>
                  <Badge variant="secondary" className={STATUS_STYLES[item.status]}>
                    {item.status.replace("_", " ")}
                  </Badge>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>
    </AppShell>
  )
}
