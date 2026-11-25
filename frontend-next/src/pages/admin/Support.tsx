import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { CheckCircle2, LifeBuoy } from "lucide-react"
import { AppShell } from "@/components/layout/AppShell"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api"
import type { SupportRequest } from "@/lib/types"

export function AdminSupportPage() {
  const queryClient = useQueryClient()
  const [status, setStatus] = useState("open")

  const { data, isLoading } = useQuery({
    queryKey: ["support-requests-all", status],
    queryFn: () => api.get<SupportRequest[]>(`/support-requests${status === "all" ? "" : `?status_filter=${status}`}`),
  })

  const resolve = useMutation({
    mutationFn: (id: string) => api.post(`/support-requests/${id}/resolve`),
    onSuccess: () => {
      toast.success("Marked resolved")
      queryClient.invalidateQueries({ queryKey: ["support-requests-all"] })
    },
    onError: (error) => toast.error((error as Error).message),
  })

  return (
    <AppShell
      title="Support inbox"
      description="What clients have asked Data Fellows directly, outside any one project."
      actions={
        <Select value={status} onValueChange={setStatus}>
          <SelectTrigger className="w-36">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="open">Open</SelectItem>
            <SelectItem value="resolved">Resolved</SelectItem>
            <SelectItem value="all">All</SelectItem>
          </SelectContent>
        </Select>
      }
    >
      <Card>
        <CardContent className="space-y-2 p-4">
          {isLoading && <Skeleton className="h-16" />}
          {data?.length === 0 && (
            <div className="flex flex-col items-center gap-2 py-14 text-center">
              <span className="flex h-10 w-10 items-center justify-center rounded-full bg-muted text-muted-foreground">
                <LifeBuoy className="h-[18px] w-[18px]" />
              </span>
              <p className="text-sm text-muted-foreground">Nothing here.</p>
            </div>
          )}
          {data?.map((item) => (
            <div key={item.id} className="rounded-xl border border-border p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-xs font-medium text-primary">{item.organization_name}</p>
                  <p className="truncate text-sm font-medium text-foreground">{item.subject}</p>
                  <p className="mt-1 text-sm text-muted-foreground">{item.body}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{new Date(item.created_at).toLocaleString()}</p>
                </div>
                {item.status === "resolved" ? (
                  <Badge variant="secondary" className="shrink-0 gap-1 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                    <CheckCircle2 className="h-3 w-3" /> Resolved
                  </Badge>
                ) : (
                  <Button size="sm" variant="outline" className="shrink-0" disabled={resolve.isPending} onClick={() => resolve.mutate(item.id)}>
                    Mark resolved
                  </Button>
                )}
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </AppShell>
  )
}
