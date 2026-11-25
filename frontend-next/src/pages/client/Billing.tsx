import { useQuery } from "@tanstack/react-query"
import { ArrowUpRight, Banknote, CheckCircle2 } from "lucide-react"
import { AppShell } from "@/components/layout/AppShell"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api"
import type { ClientOverview, Invoice } from "@/lib/types"

const STATUS_STYLES: Record<string, string> = {
  open: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
  paid: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  void: "bg-muted text-muted-foreground",
  uncollectible: "bg-destructive/10 text-destructive",
}

function formatAmount(cents: number, currency: string) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: currency.toUpperCase() }).format(cents / 100)
}

function OrganizationInvoices({ organizationId, organizationName }: { organizationId: string; organizationName: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["invoices", organizationId],
    queryFn: () => api.get<Invoice[]>(`/organizations/${organizationId}/invoices`),
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{organizationName}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {isLoading && <Skeleton className="h-16" />}
        {data?.length === 0 && <p className="py-6 text-center text-sm text-muted-foreground">No invoices yet.</p>}
        {data?.map((invoice) => (
          <div key={invoice.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border p-4">
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-foreground">{invoice.description}</p>
              <p className="text-xs text-muted-foreground">
                {formatAmount(invoice.amount_cents, invoice.currency)}
                {invoice.paid_at && ` · Paid ${new Date(invoice.paid_at).toLocaleDateString()}`}
                {!invoice.paid_at && invoice.sent_at && ` · Sent ${new Date(invoice.sent_at).toLocaleDateString()}`}
              </p>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              {invoice.status === "paid" && (
                <Badge variant="secondary" className={`gap-1 ${STATUS_STYLES.paid}`}>
                  <CheckCircle2 className="h-3 w-3" /> Paid
                </Badge>
              )}
              {invoice.status === "open" && invoice.hosted_invoice_url && (
                <Button asChild size="sm">
                  <a href={invoice.hosted_invoice_url} target="_blank" rel="noreferrer">
                    Pay invoice <ArrowUpRight className="h-3 w-3" />
                  </a>
                </Button>
              )}
              {invoice.status === "void" && (
                <Badge variant="secondary" className={STATUS_STYLES.void}>
                  Voided
                </Badge>
              )}
              {invoice.status === "uncollectible" && (
                <Badge variant="secondary" className={STATUS_STYLES.uncollectible}>
                  Uncollectible
                </Badge>
              )}
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

export function ClientBillingPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["client-overview"],
    queryFn: () => api.get<ClientOverview>("/client/overview"),
  })

  return (
    <AppShell title="Billing" description="Invoices from Data Fellows for your organization, and a direct link to pay each one.">
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
              <Banknote className="h-[18px] w-[18px]" />
            </span>
            <p className="text-sm text-muted-foreground">No organization linked to this account yet.</p>
          </CardContent>
        </Card>
      )}
      {data && data.organizations.length > 0 && (
        <div className="space-y-4">
          {data.organizations.map((organization) => (
            <OrganizationInvoices key={organization.id} organizationId={organization.id} organizationName={organization.name} />
          ))}
        </div>
      )}
    </AppShell>
  )
}
