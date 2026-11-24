import { Construction } from "lucide-react"
import { AppShell } from "@/components/layout/AppShell"
import { Card, CardContent } from "@/components/ui/card"

export function ComingSoonPage({ title }: { title: string }) {
  return (
    <AppShell title={title}>
      <Card className="border-dashed">
        <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted text-muted-foreground">
            <Construction className="h-5 w-5" />
          </div>
          <p className="text-sm font-medium text-foreground">This screen isn't built yet</p>
          <p className="max-w-sm text-sm text-muted-foreground">
            It's on the roadmap but hasn't been rebuilt in the new design system yet — this placeholder is here so
            the navigation stays honest about what's real.
          </p>
        </CardContent>
      </Card>
    </AppShell>
  )
}
