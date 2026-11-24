import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { Clock, Folder, MessageCircle, Plus } from "lucide-react"
import { AppShell } from "@/components/layout/AppShell"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api"
import type { ClientOverview, Project } from "@/lib/types"

interface ProjectRequest {
  id: string
  project_id: string
  subject: string
  created_at: string
  decision: "approved" | "declined" | null
  rationale: string | null
  decided_at: string | null
}

const DECISION_STYLES: Record<string, string> = {
  approved: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  declined: "bg-muted text-muted-foreground",
}

function ProjectCard({ project }: { project: Project }) {
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const [subject, setSubject] = useState("")

  const coordination = useQuery({
    queryKey: ["coordination", project.id],
    queryFn: () => api.get<{ requests: ProjectRequest[] }>(`/projects/${project.id}/coordination`),
  })

  const openRequest = useMutation({
    mutationFn: () => api.post(`/projects/${project.id}/requests`, { subject: subject.trim() }),
    onSuccess: () => {
      toast.success("Request sent to your delivery team")
      setOpen(false)
      setSubject("")
      queryClient.invalidateQueries({ queryKey: ["coordination", project.id] })
    },
    onError: (error) => toast.error((error as Error).message),
  })

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <p className="text-xs font-medium text-primary">{project.organization_name}</p>
          <CardTitle className="text-base">{project.name}</CardTitle>
        </div>
        <Badge variant="secondary" className="capitalize">
          {project.status}
        </Badge>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          {(project.work_packages ?? []).map((pkg) => (
            <div key={pkg.id} className="flex items-center justify-between rounded-lg bg-muted/50 px-3 py-2 text-sm">
              <span className="text-foreground">{pkg.title}</span>
              <Badge variant="outline" className="capitalize">
                {pkg.status.replace("_", " ")}
              </Badge>
            </div>
          ))}
          {(project.work_packages ?? []).length === 0 && <p className="text-xs text-muted-foreground">No work packages started yet.</p>}
        </div>

        <div className="border-t border-border pt-3">
          <div className="mb-2 flex items-center justify-between">
            <p className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
              <MessageCircle className="h-3.5 w-3.5" /> Requests to your delivery team
            </p>
            <Dialog open={open} onOpenChange={setOpen}>
              <DialogTrigger asChild>
                <Button size="sm" variant="outline">
                  <Plus className="h-3 w-3" /> New request
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>New request for {project.name}</DialogTitle>
                </DialogHeader>
                <Input
                  placeholder="What do you need from your delivery team?"
                  value={subject}
                  onChange={(event) => setSubject(event.target.value)}
                />
                <DialogFooter>
                  <Button variant="ghost" onClick={() => setOpen(false)}>
                    Cancel
                  </Button>
                  <Button disabled={subject.trim().length < 3 || openRequest.isPending} onClick={() => openRequest.mutate()}>
                    Send request
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
          {coordination.isLoading && <Skeleton className="h-10" />}
          {coordination.data && coordination.data.requests.length === 0 && (
            <p className="text-xs text-muted-foreground">No requests on this project yet.</p>
          )}
          <div className="space-y-1.5">
            {coordination.data?.requests.map((request) => (
              <div key={request.id} className="flex items-center justify-between gap-3 rounded-lg border border-border px-3 py-2">
                <div className="min-w-0">
                  <p className="truncate text-sm text-foreground">{request.subject}</p>
                  {request.rationale && <p className="truncate text-xs text-muted-foreground">{request.rationale}</p>}
                </div>
                {request.decision ? (
                  <Badge variant="secondary" className={`shrink-0 capitalize ${DECISION_STYLES[request.decision]}`}>
                    {request.decision}
                  </Badge>
                ) : (
                  <Badge variant="outline" className="shrink-0 gap-1">
                    <Clock className="h-3 w-3" /> Pending
                  </Badge>
                )}
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export function ClientProjectsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["client-overview"],
    queryFn: () => api.get<ClientOverview>("/client/overview"),
  })

  return (
    <AppShell title="Projects & engagements" description="Every engagement authorized for your organization, and open requests to your delivery team.">
      {isLoading && (
        <div className="space-y-4">
          <Skeleton className="h-40" />
          <Skeleton className="h-40" />
        </div>
      )}
      {error && (
        <Card className="border-dashed">
          <CardContent className="py-12 text-center text-sm text-muted-foreground">
            {(error as Error).message || "No workspace is linked to this account yet."}
          </CardContent>
        </Card>
      )}
      {data && data.projects.length === 0 && (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center gap-2 py-16 text-center">
            <span className="flex h-10 w-10 items-center justify-center rounded-full bg-muted text-muted-foreground">
              <Folder className="h-[18px] w-[18px]" />
            </span>
            <p className="text-sm text-muted-foreground">No projects authorized yet. Your delivery team will update this once work begins.</p>
          </CardContent>
        </Card>
      )}
      {data && data.projects.length > 0 && (
        <div className="space-y-4">
          {data.projects.map((project) => (
            <ProjectCard key={project.id} project={project} />
          ))}
        </div>
      )}
    </AppShell>
  )
}
