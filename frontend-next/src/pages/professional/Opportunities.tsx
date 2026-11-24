import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { Sparkles } from "lucide-react"
import { AppShell } from "@/components/layout/AppShell"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api"
import type { Opportunity } from "@/lib/types"

export function ProfessionalOpportunitiesPage() {
  const queryClient = useQueryClient()
  const [target, setTarget] = useState<Opportunity | null>(null)
  const [approach, setApproach] = useState("")

  const { data, isLoading } = useQuery({
    queryKey: ["opportunities"],
    queryFn: () => api.get<Opportunity[]>("/opportunities"),
  })

  const expressInterest = useMutation({
    mutationFn: () => api.post(`/opportunities/${encodeURIComponent(target!.id)}/interests`, { approach }),
    onSuccess: () => {
      toast.success("Interest submitted for Data Fellows review")
      setTarget(null)
      setApproach("")
      queryClient.invalidateQueries({ queryKey: ["opportunities"] })
    },
    onError: (error) => toast.error((error as Error).message),
  })

  return (
    <AppShell title="Find meaningful work" description="Explore sanitized opportunities published by Data Fellows.">
      {isLoading && (
        <div className="grid gap-4 sm:grid-cols-2">
          <Skeleton className="h-40" />
          <Skeleton className="h-40" />
        </div>
      )}

      {data?.length === 0 && (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
            <Sparkles className="h-5 w-5 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">No opportunities published right now. Check back soon.</p>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        {data?.map((item) => (
          <Card key={item.id}>
            <CardContent className="space-y-3 p-5">
              <div>
                <p className="font-heading text-base font-semibold text-foreground">{item.title}</p>
                {item.specialization && <p className="text-xs font-medium text-primary">{item.specialization}</p>}
              </div>
              <p className="text-sm text-muted-foreground">{item.summary}</p>
              {item.skills.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {item.skills.map((skill) => (
                    <Badge key={skill} variant="outline">
                      {skill}
                    </Badge>
                  ))}
                </div>
              )}
              <div className="flex items-center justify-between pt-1">
                {item.compensation && <p className="text-xs text-muted-foreground">{item.compensation}</p>}
                <Button size="sm" onClick={() => setTarget(item)}>
                  Express interest
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Dialog open={!!target} onOpenChange={(open) => !open && setTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Express interest</DialogTitle>
            <DialogDescription>{target?.title}</DialogDescription>
          </DialogHeader>
          <Textarea
            rows={4}
            value={approach}
            onChange={(event) => setApproach(event.target.value)}
            placeholder="Briefly describe the relevant experience you'd bring to this opportunity."
          />
          <DialogFooter>
            <Button variant="ghost" onClick={() => setTarget(null)}>
              Cancel
            </Button>
            <Button disabled={approach.trim().length < 2 || expressInterest.isPending} onClick={() => expressInterest.mutate()}>
              Submit
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AppShell>
  )
}
