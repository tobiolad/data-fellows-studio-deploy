import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { Building2, Plus, X } from "lucide-react"
import { AppShell } from "@/components/layout/AppShell"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
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
import type { Engagement, Organization } from "@/lib/types"

interface Member {
  actor_id: string
  role: string
}

const ROLES = ["client", "professional", "reviewer", "owner"]

function OrganizationCard({ organization, engagements }: { organization: Organization; engagements: Engagement[] }) {
  const queryClient = useQueryClient()
  const [memberActor, setMemberActor] = useState("")
  const [memberRole, setMemberRole] = useState("client")
  const [engagementOpen, setEngagementOpen] = useState(false)
  const [engagementName, setEngagementName] = useState("")
  const [engagementObjective, setEngagementObjective] = useState("")

  const members = useQuery({
    queryKey: ["members", organization.id],
    queryFn: () => api.get<Member[]>(`/organizations/${organization.id}/members`),
  })

  const addMember = useMutation({
    mutationFn: () => api.post(`/organizations/${organization.id}/members`, { actor_id: memberActor, role: memberRole }),
    onSuccess: () => {
      toast.success("Member added")
      setMemberActor("")
      queryClient.invalidateQueries({ queryKey: ["members", organization.id] })
    },
    onError: (error) => toast.error((error as Error).message),
  })

  const removeMember = useMutation({
    mutationFn: ({ actorId, role }: { actorId: string; role: string }) =>
      api.delete(`/organizations/${organization.id}/members/${encodeURIComponent(actorId)}/${encodeURIComponent(role)}`),
    onSuccess: () => {
      toast.success("Member removed")
      queryClient.invalidateQueries({ queryKey: ["members", organization.id] })
    },
  })

  const createEngagement = useMutation({
    mutationFn: () => api.post("/engagements", { organization_id: organization.id, name: engagementName, objective: engagementObjective }),
    onSuccess: () => {
      toast.success("Engagement created")
      setEngagementOpen(false)
      setEngagementName("")
      setEngagementObjective("")
      queryClient.invalidateQueries({ queryKey: ["engagements"] })
    },
    onError: (error) => toast.error((error as Error).message),
  })

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2 text-base">
          <Building2 className="h-4 w-4 text-primary" /> {organization.name}
        </CardTitle>
        <Dialog open={engagementOpen} onOpenChange={setEngagementOpen}>
          <DialogTrigger asChild>
            <Button size="sm" variant="outline">
              <Plus className="h-3 w-3" /> New engagement
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>New engagement for {organization.name}</DialogTitle>
            </DialogHeader>
            <div className="space-y-3">
              <div className="space-y-1.5">
                <Label>Name</Label>
                <Input value={engagementName} onChange={(event) => setEngagementName(event.target.value)} />
              </div>
              <div className="space-y-1.5">
                <Label>Objective</Label>
                <Textarea rows={3} value={engagementObjective} onChange={(event) => setEngagementObjective(event.target.value)} />
              </div>
            </div>
            <DialogFooter>
              <Button variant="ghost" onClick={() => setEngagementOpen(false)}>
                Cancel
              </Button>
              <Button disabled={engagementName.trim().length < 2 || engagementObjective.trim().length < 2 || createEngagement.isPending} onClick={() => createEngagement.mutate()}>
                Create
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <p className="mb-2 text-xs font-medium text-muted-foreground">Members</p>
          <div className="flex flex-wrap gap-1.5">
            {members.data?.map((member) => (
              <Badge key={`${member.actor_id}-${member.role}`} variant="secondary" className="gap-1 pr-1">
                {member.actor_id} · {member.role}
                <button onClick={() => removeMember.mutate({ actorId: member.actor_id, role: member.role })} className="rounded-full p-0.5 hover:bg-muted-foreground/20">
                  <X className="h-2.5 w-2.5" />
                </button>
              </Badge>
            ))}
            {members.data?.length === 0 && <p className="text-xs text-muted-foreground">No members yet.</p>}
          </div>
          <div className="mt-2 flex gap-2">
            <Input placeholder="actor id" value={memberActor} onChange={(event) => setMemberActor(event.target.value)} className="h-8 flex-1" />
            <Select value={memberRole} onValueChange={setMemberRole}>
              <SelectTrigger className="h-8 w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {ROLES.map((role) => (
                  <SelectItem key={role} value={role}>
                    {role}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button size="sm" variant="outline" disabled={memberActor.trim().length < 2 || addMember.isPending} onClick={() => addMember.mutate()}>
              Add
            </Button>
          </div>
        </div>

        <div>
          <p className="mb-2 text-xs font-medium text-muted-foreground">Engagements</p>
          {engagements.length === 0 && <p className="text-xs text-muted-foreground">No engagements yet.</p>}
          <div className="space-y-1.5">
            {engagements.map((engagement) => (
              <div key={engagement.id} className="flex items-center justify-between rounded-lg border border-border px-3 py-2">
                <div>
                  <p className="text-sm font-medium text-foreground">{engagement.name}</p>
                  <p className="text-xs text-muted-foreground">{engagement.objective}</p>
                </div>
                <Badge variant="outline" className="capitalize">
                  {engagement.status}
                </Badge>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export function AdminEngagementsPage() {
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const [name, setName] = useState("")

  const organizations = useQuery({ queryKey: ["organizations"], queryFn: () => api.get<Organization[]>("/organizations") })
  const engagements = useQuery({ queryKey: ["engagements"], queryFn: () => api.get<Engagement[]>("/engagements") })

  const create = useMutation({
    mutationFn: () => api.post("/organizations", { name }),
    onSuccess: () => {
      toast.success("Organization created")
      setOpen(false)
      setName("")
      queryClient.invalidateQueries({ queryKey: ["organizations"] })
    },
    onError: (error) => toast.error((error as Error).message),
  })

  return (
    <AppShell
      title="Clients & engagements"
      description="Organizations are the authorization boundary for every engagement, project and membership."
      actions={
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button size="sm">
              <Plus className="h-3.5 w-3.5" /> New organization
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>New client organization</DialogTitle>
            </DialogHeader>
            <div className="space-y-1.5">
              <Label>Name</Label>
              <Input value={name} onChange={(event) => setName(event.target.value)} placeholder="Acme Logistics" />
            </div>
            <DialogFooter>
              <Button variant="ghost" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button disabled={name.trim().length < 2 || create.isPending} onClick={() => create.mutate()}>
                Create
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      }
    >
      <div className="space-y-4">
        {organizations.isLoading && <Skeleton className="h-48" />}
        {organizations.data?.map((org) => (
          <OrganizationCard key={org.id} organization={org} engagements={(engagements.data ?? []).filter((item) => item.organization_id === org.id)} />
        ))}
      </div>
    </AppShell>
  )
}
