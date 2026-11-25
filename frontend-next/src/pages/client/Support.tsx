import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { CheckCircle2, Clock, LifeBuoy, Plus } from "lucide-react"
import { AppShell } from "@/components/layout/AppShell"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
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
import type { ClientOverview, SupportRequest } from "@/lib/types"

function OrganizationSupport({ organizationId, organizationName }: { organizationId: string; organizationName: string }) {
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const [subject, setSubject] = useState("")
  const [body, setBody] = useState("")

  const { data, isLoading } = useQuery({
    queryKey: ["support-requests", organizationId],
    queryFn: () => api.get<SupportRequest[]>(`/organizations/${organizationId}/support-requests`),
  })

  const submit = useMutation({
    mutationFn: () => api.post(`/organizations/${organizationId}/support-requests`, { subject, body }),
    onSuccess: () => {
      toast.success("Sent to Data Fellows. We'll follow up by email.")
      setOpen(false)
      setSubject("")
      setBody("")
      queryClient.invalidateQueries({ queryKey: ["support-requests", organizationId] })
    },
    onError: (error) => toast.error((error as Error).message),
  })

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-base">{organizationName}</CardTitle>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button size="sm">
              <Plus className="h-3.5 w-3.5" /> New request
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Get in touch with Data Fellows</DialogTitle>
            </DialogHeader>
            <div className="space-y-3">
              <div className="space-y-1.5">
                <Label>What's it about</Label>
                <Input value={subject} onChange={(event) => setSubject(event.target.value)} placeholder="Question about my invoice" />
              </div>
              <div className="space-y-1.5">
                <Label>Details</Label>
                <Textarea rows={4} value={body} onChange={(event) => setBody(event.target.value)} placeholder="Tell us what's going on" />
              </div>
            </div>
            <DialogFooter>
              <Button variant="ghost" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button disabled={subject.trim().length < 2 || body.trim().length < 2 || submit.isPending} onClick={() => submit.mutate()}>
                Send
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </CardHeader>
      <CardContent className="space-y-2">
        {isLoading && <Skeleton className="h-16" />}
        {data?.length === 0 && <p className="py-6 text-center text-sm text-muted-foreground">Nothing sent yet.</p>}
        {data?.map((item) => (
          <div key={item.id} className="rounded-xl border border-border p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-foreground">{item.subject}</p>
                <p className="mt-1 text-sm text-muted-foreground">{item.body}</p>
              </div>
              {item.status === "resolved" ? (
                <Badge variant="secondary" className="shrink-0 gap-1 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                  <CheckCircle2 className="h-3 w-3" /> Resolved
                </Badge>
              ) : (
                <Badge variant="outline" className="shrink-0 gap-1">
                  <Clock className="h-3 w-3" /> Waiting on us
                </Badge>
              )}
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

export function ClientSupportPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["client-overview"],
    queryFn: () => api.get<ClientOverview>("/client/overview"),
  })

  return (
    <AppShell title="Support" description="Reach Data Fellows directly. We reply by email, usually within a business day.">
      {isLoading && <Skeleton className="h-40" />}
      {error && (
        <Card className="border-dashed">
          <CardContent className="py-12 text-center text-sm text-muted-foreground">
            {(error as Error).message || "No workspace is linked to this account yet."}
          </CardContent>
        </Card>
      )}
      {data && data.organizations.length === 0 && (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center gap-2 py-16 text-center">
            <span className="flex h-10 w-10 items-center justify-center rounded-full bg-muted text-muted-foreground">
              <LifeBuoy className="h-[18px] w-[18px]" />
            </span>
            <p className="text-sm text-muted-foreground">No organization linked to this account yet.</p>
          </CardContent>
        </Card>
      )}
      {data && data.organizations.length > 0 && (
        <div className="space-y-4">
          {data.organizations.map((organization) => (
            <OrganizationSupport key={organization.id} organizationId={organization.id} organizationName={organization.name} />
          ))}
        </div>
      )}
    </AppShell>
  )
}
