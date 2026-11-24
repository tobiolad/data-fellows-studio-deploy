import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { Copy, Gift, LineChart, Plus, UserPlus } from "lucide-react"
import { AppShell } from "@/components/layout/AppShell"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api"
import type { ReferralLink } from "@/lib/types"

function copy(value: string, label: string) {
  navigator.clipboard.writeText(value)
  toast.success(`${label} copied`)
}

export function AdminReferralsPage() {
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const [partnerName, setPartnerName] = useState("")

  const { data, isLoading } = useQuery({
    queryKey: ["referral-links"],
    queryFn: () => api.get<ReferralLink[]>("/referral-links"),
  })

  const create = useMutation({
    mutationFn: () => api.post<ReferralLink>("/referral-links", { partner_name: partnerName }),
    onSuccess: () => {
      toast.success("Referral link created")
      queryClient.invalidateQueries({ queryKey: ["referral-links"] })
      setOpen(false)
      setPartnerName("")
    },
    onError: (error) => toast.error((error as Error).message),
  })

  const origin = window.location.origin
  const totals = data?.reduce(
    (acc, link) => ({ visits: acc.visits + link.visit_count, signups: acc.signups + link.signup_count }),
    { visits: 0, signups: 0 },
  )

  return (
    <AppShell
      title="Referral program"
      description="Create a trackable link for an onboarded accelerator or partner, and track signups it brings in."
      actions={
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button size="sm">
              <Plus className="h-3.5 w-3.5" /> New referral link
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create a referral link</DialogTitle>
              <DialogDescription>One link per partner. Share it with them, and share their view link so they can track it too.</DialogDescription>
            </DialogHeader>
            <div className="space-y-1.5">
              <Label htmlFor="partner-name">Partner name</Label>
              <Input id="partner-name" value={partnerName} onChange={(event) => setPartnerName(event.target.value)} placeholder="Northstar Accelerator" />
            </div>
            <DialogFooter>
              <Button variant="ghost" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button disabled={partnerName.trim().length < 2 || create.isPending} onClick={() => create.mutate()}>
                Create link
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      }
    >
      <div className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-2">
          <Card>
            <CardContent className="flex items-center gap-3.5 p-5">
              <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <LineChart className="h-4 w-4" />
              </span>
              <div>
                <p className="font-heading text-xl font-semibold text-foreground">{totals?.visits ?? 0}</p>
                <p className="text-xs text-muted-foreground">Total link visits</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="flex items-center gap-3.5 p-5">
              <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                <UserPlus className="h-4 w-4" />
              </span>
              <div>
                <p className="font-heading text-xl font-semibold text-foreground">{totals?.signups ?? 0}</p>
                <p className="text-xs text-muted-foreground">Clients onboarded via referral</p>
              </div>
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Partner links</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {isLoading && <Skeleton className="h-16" />}
            {data?.length === 0 && (
              <div className="flex flex-col items-center gap-2 py-10 text-center">
                <span className="flex h-10 w-10 items-center justify-center rounded-full bg-muted text-muted-foreground">
                  <Gift className="h-4.5 w-4.5" />
                </span>
                <p className="text-sm text-muted-foreground">No referral links yet. Create one for a partner you've onboarded.</p>
              </div>
            )}
            {data?.map((link) => {
              const shareUrl = `${origin}/r/${link.code}`
              const partnerUrl = `${origin}/r/view/${link.view_token}`
              return (
                <div key={link.id} className="rounded-xl border border-border p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <p className="font-medium text-foreground">{link.partner_name}</p>
                      <p className="text-xs text-muted-foreground">Created {new Date(link.created_at).toLocaleDateString()}</p>
                    </div>
                    <Badge variant={link.status === "active" ? "secondary" : "outline"} className="capitalize">
                      {link.status}
                    </Badge>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-6 text-sm">
                    <div>
                      <p className="text-xs text-muted-foreground">Visits</p>
                      <p className="font-medium text-foreground">{link.visit_count}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Signups</p>
                      <p className="font-medium text-foreground">{link.signup_count}</p>
                    </div>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Button variant="outline" size="sm" onClick={() => copy(shareUrl, "Referral link")}>
                      <Copy className="h-3 w-3" /> Share link
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => copy(partnerUrl, "Partner tracking link")}>
                      <Copy className="h-3 w-3" /> Partner tracking link
                    </Button>
                  </div>
                </div>
              )
            })}
          </CardContent>
        </Card>
      </div>
    </AppShell>
  )
}
