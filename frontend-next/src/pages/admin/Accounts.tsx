import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { Mail, UserCheck } from "lucide-react"
import { AppShell } from "@/components/layout/AppShell"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Skeleton } from "@/components/ui/skeleton"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { api } from "@/lib/api"
import type { Role, StudioAccount } from "@/lib/types"

const ASSIGNABLE_ROLES: { role: Role; label: string }[] = [
  { role: "admin", label: "Internal admin" },
  { role: "client", label: "Client" },
  { role: "professional", label: "Professional" },
  { role: "reviewer", label: "Reviewer" },
]

export function AdminAccountsPage() {
  const queryClient = useQueryClient()

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
                <Select onValueChange={(role) => assignRole.mutate({ id: account.id, role: role as Role })}>
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
    </AppShell>
  )
}
