import { useParams } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { Gift, LineChart, UserPlus } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"

interface ReferralStatsResponse {
  partner_name: string
  code: string
  status: string
  created_at: string
  visit_count: number
  signup_count: number
}

export function ReferralStatsPage() {
  const { token } = useParams<{ token: string }>()

  const { data, isLoading, error } = useQuery({
    queryKey: ["referral-stats", token],
    queryFn: async () => {
      const response = await fetch(`/api/referral/${encodeURIComponent(token ?? "")}/stats`)
      if (!response.ok) throw new Error("This tracking link isn't valid.")
      return (await response.json()) as ReferralStatsResponse
    },
  })

  return (
    <div className="flex min-h-svh items-center justify-center bg-muted/30 px-4">
      <div className="w-full max-w-lg">
        <div className="mb-6 flex flex-col items-center text-center">
          <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-primary-foreground">
            <Gift className="h-5 w-5" />
          </div>
          <h1 className="font-heading text-xl font-semibold text-foreground">Referral performance</h1>
          <p className="text-sm text-muted-foreground">Shared by Data Fellows — no account needed.</p>
        </div>

        {isLoading && <p className="text-center text-sm text-muted-foreground">Loading…</p>}
        {error && <p className="text-center text-sm text-destructive">{(error as Error).message}</p>}

        {data && (
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-base">{data.partner_name}</CardTitle>
              <Badge variant="secondary" className="capitalize">
                {data.status}
              </Badge>
            </CardHeader>
            <CardContent className="grid grid-cols-2 gap-4">
              <div className="rounded-lg border border-border p-4 text-center">
                <LineChart className="mx-auto mb-2 h-4 w-4 text-primary" />
                <p className="font-heading text-2xl font-semibold text-foreground">{data.visit_count}</p>
                <p className="text-xs text-muted-foreground">Link visits</p>
              </div>
              <div className="rounded-lg border border-border p-4 text-center">
                <UserPlus className="mx-auto mb-2 h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                <p className="font-heading text-2xl font-semibold text-foreground">{data.signup_count}</p>
                <p className="text-xs text-muted-foreground">Clients onboarded</p>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
