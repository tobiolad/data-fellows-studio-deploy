import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { Bot, CheckCircle2, Plus, ShieldAlert, XCircle } from "lucide-react"
import { AppShell } from "@/components/layout/AppShell"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Checkbox } from "@/components/ui/checkbox"
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
import type { AdminOverview, AiAgent, AiRunSummary } from "@/lib/types"

const RUN_STATUS_STYLES: Record<string, string> = {
  queued: "bg-muted text-muted-foreground",
  running: "bg-blue-500/10 text-blue-600 dark:text-blue-400",
  succeeded: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  failed: "bg-destructive/10 text-destructive",
  cancelled: "bg-muted text-muted-foreground",
}

function RegisterAgentDialog() {
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({
    name: "",
    purpose: "",
    capability_category: "planning",
    provider: "synthetic",
    model: "planner",
    model_version: "planning-only-v1",
    data_access_scope: "work_package",
    autonomy_level: "supervised",
    requires_human_approval: true,
    budget_cap_cents: 1000,
    owner_actor_id: "",
  })

  const create = useMutation({
    mutationFn: () => api.post("/ai-agents", { ...form, allowed_tools: ["planning"] }),
    onSuccess: () => {
      toast.success("Agent registered")
      setOpen(false)
      queryClient.invalidateQueries({ queryKey: ["ai-agents"] })
    },
    onError: (error) => toast.error((error as Error).message),
  })

  const valid = form.name.trim().length > 1 && form.purpose.trim().length > 1 && form.owner_actor_id.trim().length > 1

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm">
          <Plus className="h-3.5 w-3.5" /> Register agent
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Register an AI agent</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div className="space-y-1.5">
            <Label>Name</Label>
            <Input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} placeholder="research-assistant-v1" />
          </div>
          <div className="space-y-1.5">
            <Label>Purpose</Label>
            <Textarea rows={2} value={form.purpose} onChange={(event) => setForm({ ...form, purpose: event.target.value })} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Capability</Label>
              <Select value={form.capability_category} onValueChange={(value) => setForm({ ...form, capability_category: value })}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {["planning", "research", "code_generation", "qa", "vetting", "analytics"].map((value) => (
                    <SelectItem key={value} value={value}>
                      {value}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>Autonomy</Label>
              <Select value={form.autonomy_level} onValueChange={(value) => setForm({ ...form, autonomy_level: value })}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="supervised">supervised</SelectItem>
                  <SelectItem value="bounded_autonomous">bounded_autonomous</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Provider</Label>
              <Input value={form.provider} onChange={(event) => setForm({ ...form, provider: event.target.value })} />
            </div>
            <div className="space-y-1.5">
              <Label>Model</Label>
              <Input value={form.model} onChange={(event) => setForm({ ...form, model: event.target.value })} />
            </div>
          </div>
          {form.provider !== "synthetic" && (
            <p className="flex items-start gap-1.5 rounded-lg bg-amber-500/10 p-2.5 text-xs text-amber-700 dark:text-amber-400">
              <ShieldAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              Non-synthetic providers can be registered, but no run will execute against them unless an operator
              explicitly approves this deployment for real-model execution.
            </p>
          )}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Budget cap (cents)</Label>
              <Input
                type="number"
                value={form.budget_cap_cents}
                onChange={(event) => setForm({ ...form, budget_cap_cents: Number(event.target.value) })}
              />
            </div>
            <div className="space-y-1.5">
              <Label>Owner (accountable human)</Label>
              <Input value={form.owner_actor_id} onChange={(event) => setForm({ ...form, owner_actor_id: event.target.value })} placeholder="admin-1" />
            </div>
          </div>
          <label className="flex items-center gap-2 text-sm">
            <Checkbox
              checked={form.requires_human_approval}
              onCheckedChange={(checked) => setForm({ ...form, requires_human_approval: checked === true })}
            />
            Requires human approval before its output can be used
          </label>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button disabled={!valid || create.isPending} onClick={() => create.mutate()}>
            Register
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export function AdminAiOperationsPage() {
  const queryClient = useQueryClient()

  const agents = useQuery({ queryKey: ["ai-agents"], queryFn: () => api.get<AiAgent[]>("/ai-agents") })
  const overview = useQuery({ queryKey: ["admin-overview"], queryFn: () => api.get<AdminOverview>("/admin/overview") })

  const decide = useMutation({
    mutationFn: ({ runId, decision }: { runId: string; decision: "approved" | "rejected" }) =>
      api.post(`/ai-runs/${encodeURIComponent(runId)}/decision`, { decision, comment: decision === "approved" ? "Reviewed and approved." : "Reviewed and rejected." }),
    onSuccess: () => {
      toast.success("Decision recorded")
      queryClient.invalidateQueries({ queryKey: ["admin-overview"] })
    },
    onError: (error) => toast.error((error as Error).message),
  })

  const runs = (overview.data?.ai_runs ?? []) as unknown as AiRunSummary[]

  return (
    <AppShell
      title="AI operations"
      description="The agent registry and every run's audit trail — deterministic execution remains approval-controlled."
      actions={<RegisterAgentDialog />}
    >
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Agent registry</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {agents.isLoading && <Skeleton className="h-16" />}
            {agents.data?.map((agent) => (
              <div key={agent.id} className="flex items-center justify-between gap-4 rounded-lg border border-border px-4 py-3">
                <div className="flex items-center gap-3">
                  <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <Bot className="h-4 w-4" />
                  </span>
                  <div>
                    <p className="text-sm font-medium text-foreground">{agent.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {agent.provider}/{agent.model} · {agent.capability_category} · cap {agent.budget_cap_cents}¢
                    </p>
                  </div>
                </div>
                <Badge variant={agent.status === "active" ? "secondary" : "outline"}>{agent.status}</Badge>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Run history</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {overview.isLoading && <Skeleton className="h-16" />}
            {runs.length === 0 && <p className="text-sm text-muted-foreground">No AI runs yet.</p>}
            {runs.map((run) => (
              <div key={run.id} className="flex items-center justify-between gap-4 rounded-lg border border-border px-4 py-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-foreground">{run.work_package_title}</p>
                  <p className="truncate text-xs text-muted-foreground">
                    {run.project_name} · {run.agent_version} · {run.spent_cents}/{run.budget_cents}¢
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <Badge variant="secondary" className={RUN_STATUS_STYLES[run.status]}>
                    {run.status}
                  </Badge>
                  {run.artifact_status === "pending_review" && (
                    <>
                      <Button size="sm" variant="outline" onClick={() => decide.mutate({ runId: run.id, decision: "approved" })} disabled={decide.isPending}>
                        <CheckCircle2 className="h-3 w-3" />
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => decide.mutate({ runId: run.id, decision: "rejected" })} disabled={decide.isPending}>
                        <XCircle className="h-3 w-3" />
                      </Button>
                    </>
                  )}
                  {run.artifact_status && run.artifact_status !== "pending_review" && (
                    <Badge variant="outline" className="capitalize">
                      {run.artifact_status}
                    </Badge>
                  )}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </AppShell>
  )
}
