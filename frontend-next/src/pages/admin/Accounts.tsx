import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { Mail, UserCheck } from "lucide-react"
import { AppShell } from "@/components/layout/AppShell"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Skeleton } from "@/components/ui/skeleton"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { api } from "@/lib/api"
import type { Organization, Role, StudioAccount } from "@/lib/types"

const ASSIGNABLE_ROLES: { role: Role; label: string }[] = [
  { role: "admin", label: "Internal admin" },
  { role: "client", label: "Client" },
  { role: "professional", label: "Professional" },
  { role: "reviewer", label: "Reviewer" },
]

/** Granting "client" also needs an organization membership, or the person sees an empty portal
 *  (client-scoped routes require both the global role and a membership row). Ask for the
 *  organization in the same action rather than sending the admin to a second screen. */
function ClientOrganizationDialog({
  account,
  open,
  onOpenChange,
  onDone,
}: {
  account: StudioAccount
  open: boolean
  onOpenChange: (open: boolean) => void
  onDone: () => void
}) {
  const [organizationId, setOrganizationId] = useState("")
  const organizations = useQuery({
    queryKey: ["organizations"],
    queryFn: () => api.get<Organization[]>("/organizations"),
    enabled: open,
  })

  const confirm = useMutation({
    mutationFn: async () => {
      await api.post(`/accounts/${account.id}/role`, { role: "client" })
      await api.post(`/organizations/${organizationId}/members`, { actor_id: account.id, role: "client" })
    },
    onSuccess: () => {
      toast.success(`${account.name || account.email} added as a client`)
      setOrganizationId("")
      onOpenChange(false)
      onDone()
    },
    onError: (error) => toast.error((error as Error).message),
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add {account.name || account.email} as a client</DialogTitle>
        </DialogHeader>
        <p className="text-sm text-muted-foreground">
          Choose which organization they belong to. They&apos;ll see that organization&apos;s projects as soon as you confirm.
        </p>
        <Select value={organizationId} onValueChange={setOrganizationId}>
          <SelectTrigger>
            <SelectValue placeholder="Choose an organization" />
          </SelectTrigger>
          <SelectContent>
            {organizations.data?.map((organization) => (
              <SelectItem key={organization.id} value={organization.id}>
                {organization.name}
              </SelectItem>
            ))}
            {organizations.data?.length === 0 && (
              <p className="px-3 py-2 text-xs text-muted-foreground">No organizations yet — create one on Clients &amp; engagements first.</p>
            )}
          </SelectContent>
        </Select>
        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button disabled={!organizationId || confirm.isPending} onClick={() => confirm.mutate()}>
            Add as client
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export function AdminAccountsPage() {
  const queryClient = useQueryClient()
  const [clientDialogFor, setClientDialogFor] = useState<StudioAccount | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ["accounts"],
    queryFn: () => api.get<StudioAccount[]>("/accounts"),
  })

  const assignRole = useMutation({
    mutationFn: ({ id, role }: { id: string; role: Role }) => api.post<StudioAccount>(`/accounts/${id}/role`, { role }),
    onSuccess: () => {
      toast.success("Role assigned")
      queryClient.invalidateQueries({ queryKey: ["accounts"] })
    },
    onError: (error) => toast.error((error as Error).message),
  })

  function chooseRole(account: StudioAccount, role: Role) {
    if (role === "client") {
      setClientDialogFor(account)
      return
    }
    assignRole.mutate({ id: account.id, role })
  }

  const pending = data?.filter((account) => !account.global_role) ?? []
  const assigned = data?.filter((account) => account.global_role) ?? []

  return (
    <AppShell
      title="People awaiting access"
      description="Anyone who signs in with Google gets an account but no workspace role until you assign one here."
    >
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Awaiting a role ({pending.length})</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {isLoading && <Skeleton className="h-16" />}
            {!isLoading && pending.length === 0 && (
              <div className="flex flex-col items-center gap-2 py-10 text-center">
                <span className="flex h-10 w-10 items-center justify-center rounded-full bg-muted text-muted-foreground">
                  <UserCheck className="h-[18px] w-[18px]" />
                </span>
                <p className="text-sm text-muted-foreground">Nobody is waiting. New Google sign-ins will show up here.</p>
              </div>
            )}
            {pending.map((account) => (
              <div key={account.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border p-4">
                <div className="flex items-center gap-3">
                  <Avatar className="h-9 w-9">
                    <AvatarFallback className="bg-primary/10 text-xs font-medium text-primary">
                      {account.name ? account.name.slice(0, 2).toUpperCase() : account.email.slice(0, 2).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  <div>
                    <p className="font-medium text-foreground">{account.name || account.email}</p>
                    <p className="flex items-center gap-1 text-xs text-muted-foreground">
                      <Mail className="h-3 w-3" /> {account.email}
                    </p>
                  </div>
                </div>
                <Select onValueChange={(role) => chooseRole(account, role as Role)}>
                  <SelectTrigger className="w-44">
                    <SelectValue placeholder="Assign a role" />
                  </SelectTrigger>
                  <SelectContent>
                    {ASSIGNABLE_ROLES.map(({ role, label }) => (
                      <SelectItem key={role} value={role}>
                        {label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Google accounts with access ({assigned.length})</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {!isLoading && assigned.length === 0 && (
              <p className="py-6 text-center text-sm text-muted-foreground">No Google accounts have a role yet.</p>
            )}
            {assigned.map((account) => (
              <div key={account.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border p-4">
                <div className="flex items-center gap-3">
                  <Avatar className="h-9 w-9">
                    <AvatarFallback className="bg-primary/10 text-xs font-medium text-primary">
                      {account.name ? account.name.slice(0, 2).toUpperCase() : account.email.slice(0, 2).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  <div>
                    <p className="font-medium text-foreground">{account.name || account.email}</p>
                    <p className="text-xs text-muted-foreground">{account.email}</p>
                  </div>
                </div>
                <Badge variant="secondary" className="capitalize">
                  {account.global_role}
                </Badge>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {clientDialogFor && (
        <ClientOrganizationDialog
          account={clientDialogFor}
          open={!!clientDialogFor}
          onOpenChange={(open) => !open && setClientDialogFor(null)}
          onDone={() => {
            setClientDialogFor(null)
            queryClient.invalidateQueries({ queryKey: ["accounts"] })
          }}
        />
      )}
    </AppShell>
  )
}
