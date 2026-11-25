import { useEffect, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { MessageSquare, Send } from "lucide-react"
import { AppShell } from "@/components/layout/AppShell"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api"
import { useAuth } from "@/lib/auth"
import { useClientOverview } from "@/lib/client-overview"
import type { ProjectMessage } from "@/lib/types"

export function ClientMessagesPage() {
  const { session } = useAuth()
  const actorId = session!.actorId
  const queryClient = useQueryClient()
  const [projectId, setProjectId] = useState("")
  const [body, setBody] = useState("")

  const overview = useClientOverview()

  useEffect(() => {
    if (!projectId && overview.data?.projects.length) setProjectId(overview.data.projects[0].id)
  }, [overview.data, projectId])

  const messages = useQuery({
    queryKey: ["project-messages", projectId],
    queryFn: () => api.get<ProjectMessage[]>(`/projects/${encodeURIComponent(projectId)}/messages`),
    enabled: !!projectId,
  })

  const send = useMutation({
    mutationFn: () => api.post(`/projects/${encodeURIComponent(projectId)}/messages`, { body, recipient_group: "internal" }),
    onSuccess: () => {
      setBody("")
      queryClient.invalidateQueries({ queryKey: ["project-messages", projectId] })
    },
    onError: (error) => toast.error((error as Error).message),
  })

  return (
    <AppShell
      title="Messages"
      description="Communicate with your Data Fellows delivery team."
      actions={
        overview.data && overview.data.projects.length > 0 ? (
          <Select value={projectId} onValueChange={setProjectId}>
            <SelectTrigger className="w-56">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {overview.data.projects.map((project) => (
                <SelectItem key={project.id} value={project.id}>
                  {project.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        ) : undefined
      }
    >
      {overview.data?.projects.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="py-14 text-center text-sm text-muted-foreground">No active project to message yet.</CardContent>
        </Card>
      ) : (
        <Card className="flex h-[32rem] flex-col">
          <CardContent className="flex flex-1 flex-col gap-3 overflow-y-auto p-5">
            {messages.isLoading && <Skeleton className="h-16" />}
            {messages.data?.length === 0 && (
              <div className="m-auto flex flex-col items-center gap-2 text-center">
                <MessageSquare className="h-5 w-5 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">Start a scoped conversation with your delivery team.</p>
              </div>
            )}
            {messages.data?.map((message) => {
              const mine = message.sender_id === actorId
              return (
                <div key={message.id} className={`flex ${mine ? "justify-end" : "justify-start"}`}>
                  <div className={`max-w-sm rounded-2xl px-4 py-2.5 text-sm ${mine ? "bg-primary text-primary-foreground" : "bg-muted text-foreground"}`}>
                    <p>{message.body}</p>
                    <p className={`mt-1 text-[10px] ${mine ? "text-primary-foreground/70" : "text-muted-foreground"}`}>
                      {mine ? "You" : message.sender_id} · {new Date(message.created_at).toLocaleTimeString()}
                    </p>
                  </div>
                </div>
              )
            })}
          </CardContent>
          <form
            className="flex items-center gap-2 border-t border-border p-3"
            onSubmit={(event) => {
              event.preventDefault()
              if (body.trim()) send.mutate()
            }}
          >
            <Textarea
              rows={1}
              value={body}
              onChange={(event) => setBody(event.target.value)}
              placeholder="Share a question, decision or request"
              className="min-h-10 flex-1 resize-none"
            />
            <Button type="submit" size="icon" disabled={!body.trim() || send.isPending}>
              <Send className="h-4 w-4" />
            </Button>
          </form>
        </Card>
      )}
    </AppShell>
  )
}
