import { useState } from "react"
import { Link, useParams } from "react-router-dom"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { ArrowLeft, Check, MessageCircle, Plus, UserPlus, X } from "lucide-react"
import { AppShell } from "@/components/layout/AppShell"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { TagInput } from "@/components/TagInput"
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
import type { WorkPackage } from "@/lib/types"

interface ProjectRequest {
  id: string
  project_id: string
  subject: string
  created_at: string
  decision: "approved" | "declined" | null
  rationale: string | null
  decided_at: string | null
}

function DecideDialog({ projectId, request, decision }: { projectId: string; request: ProjectRequest; decision: "approved" | "declined" }) {
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const [rationale, setRationale] = useState("")

  const decide = useMutation({
    mutationFn: () => api.post(`/projects/${projectId}/requests/${request.id}/decision`, { decision, rationale }),
    onSuccess: () => {
      toast.success(decision === "approved" ? "Approved" : "Declined")
      setOpen(false)
      setRationale("")
      queryClient.invalidateQueries({ queryKey: ["coordination", projectId] })
    },
    onError: (error) => toast.error((error as Error).message),
  })

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm" variant={decision === "approved" ? "default" : "outline"}>
          {decision === "approved" ? <Check className="h-3 w-3" /> : <X className="h-3 w-3" />}
          {decision === "approved" ? "Approve" : "Decline"}
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{decision === "approved" ? "Approve" : "Decline"} "{request.subject}"</DialogTitle>
        </DialogHeader>
        <div className="space-y-1.5">
          <Label>Why (the client sees this)</Label>
          <Textarea rows={3} value={rationale} onChange={(event) => setRationale(event.target.value)} />
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button disabled={rationale.trim().length < 2 || decide.isPending} onClick={() => decide.mutate()}>
            Confirm
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function ProjectRequests({ projectId }: { projectId: string }) {
  const coordination = useQuery({
    queryKey: ["coordination", projectId],
    queryFn: () => api.get<{ requests: ProjectRequest[] }>(`/projects/${projectId}/coordination`),
  })

  const requests = coordination.data?.requests ?? []

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <MessageCircle className="h-4 w-4 text-primary" /> Client requests
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {coordination.isLoading && <Skeleton className="h-16" />}
        {requests.length === 0 && !coordination.isLoading && <p className="text-sm text-muted-foreground">No requests on this project.</p>}
        {requests.map((request) => (
          <div key={request.id} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border px-3 py-2">
            <div className="min-w-0">
              <p className="truncate text-sm text-foreground">{request.subject}</p>
              {request.rationale && <p className="truncate text-xs text-muted-foreground">{request.rationale}</p>}
            </div>
            {request.decision ? (
              <Badge variant="secondary" className={`shrink-0 capitalize ${request.decision === "approved" ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400" : "bg-muted text-muted-foreground"}`}>
                {request.decision}
              </Badge>
            ) : (
              <div className="flex shrink-0 gap-2">
                <DecideDialog projectId={projectId} request={request} decision="approved" />
                <DecideDialog projectId={projectId} request={request} decision="declined" />
              </div>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

const STATUS_STYLES: Record<string, string> = {
  unassigned: "bg-muted text-muted-foreground",
  assigned: "bg-blue-500/10 text-blue-600 dark:text-blue-400",
  in_progress: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
  under_review: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
  completed: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
}

function AssignDialog({ workPackageId }: { workPackageId: string }) {
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const [professionalId, setProfessionalId] = useState("")

  const invite = useMutation({
    mutationFn: () => api.post(`/work-packages/${workPackageId}/assignments`, { professional_id: professionalId }),
    onSuccess: () => {
      toast.success("Invitation sent")
      setOpen(false)
      setProfessionalId("")
      queryClient.invalidateQueries({ queryKey: ["work-packages"] })
    },
    onError: (error) => toast.error((error as Error).message),
  })

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm" variant="outline">
          <UserPlus className="h-3 w-3" /> Invite professional
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Invite a professional</DialogTitle>
        </DialogHeader>
        <div className="space-y-1.5">
          <Label>Professional id</Label>
          <Input value={professionalId} onChange={(event) => setProfessionalId(event.target.value)} placeholder="professional-1" />
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button disabled={professionalId.trim().length < 2 || invite.isPending} onClick={() => invite.mutate()}>
            Send invitation
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export function AdminProjectDetailPage() {
  const { id } = useParams<{ id: string }>()
  const projectId = id!
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const [title, setTitle] = useState("")
  const [criteria, setCriteria] = useState<string[]>([])

  const packages = useQuery({
    queryKey: ["work-packages", projectId],
    queryFn: () => api.get<WorkPackage[]>(`/projects/${projectId}/work-packages`),
  })

  const create = useMutation({
    mutationFn: () => api.post("/work-packages", { project_id: projectId, title, acceptance_criteria: criteria, depends_on: [] }),
    onSuccess: () => {
      toast.success("Work package created")
      setOpen(false)
      setTitle("")
      setCriteria([])
      queryClient.invalidateQueries({ queryKey: ["work-packages", projectId] })
    },
    onError: (error) => toast.error((error as Error).message),
  })

  return (
    <AppShell
      title="Project work packages"
      actions={
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button size="sm">
              <Plus className="h-3.5 w-3.5" /> New work package
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>New work package</DialogTitle>
            </DialogHeader>
            <div className="space-y-3">
              <div className="space-y-1.5">
                <Label>Title</Label>
                <Input value={title} onChange={(event) => setTitle(event.target.value)} />
              </div>
              <div className="space-y-1.5">
                <Label>Acceptance criteria</Label>
                <TagInput value={criteria} onChange={setCriteria} placeholder="Type a criterion and press Enter" />
              </div>
            </div>
            <DialogFooter>
              <Button variant="ghost" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button disabled={title.trim().length < 2 || criteria.length === 0 || create.isPending} onClick={() => create.mutate()}>
                Create
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      }
    >
      <Link to="/admin/projects" className="mb-4 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-3.5 w-3.5" /> Back to projects
      </Link>

      <div className="mb-4">
        <ProjectRequests projectId={projectId} />
      </div>

      <div className="space-y-3">
        {packages.isLoading && <Skeleton className="h-24" />}
        {packages.data?.length === 0 && (
          <Card className="border-dashed">
            <CardContent className="py-14 text-center text-sm text-muted-foreground">No work packages yet.</CardContent>
          </Card>
        )}
        {packages.data?.map((pkg) => (
          <Card key={pkg.id}>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-base">{pkg.title}</CardTitle>
              <Badge variant="secondary" className={STATUS_STYLES[pkg.status]}>
                {pkg.status.replace("_", " ")}
              </Badge>
            </CardHeader>
            <CardContent className="space-y-3">
              <ul className="list-inside list-disc text-sm text-muted-foreground">
                {pkg.acceptance_criteria.map((criterion, index) => (
                  <li key={index}>{criterion}</li>
                ))}
              </ul>
              <AssignDialog workPackageId={pkg.id} />
            </CardContent>
          </Card>
        ))}
      </div>
    </AppShell>
  )
}
