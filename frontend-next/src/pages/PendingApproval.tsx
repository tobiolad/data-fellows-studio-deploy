import { useLocation, useNavigate } from "react-router-dom"
import { Hourglass } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"

export function PendingApprovalPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const email = (location.state as { email?: string } | null)?.email

  return (
    <div className="relative flex min-h-svh items-center justify-center overflow-hidden bg-background px-4 py-10">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-primary/15 via-background to-background"
      />
      <Card className="w-full max-w-md border-border/60 shadow-xl shadow-black/5">
        <CardHeader className="items-center text-center">
          <div className="mb-2 flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10 text-primary">
            <Hourglass className="h-5 w-5" />
          </div>
          <CardTitle className="text-xl">Your account is set up</CardTitle>
          <CardDescription>
            {email ? <>Signed in as <span className="font-medium text-foreground">{email}</span>.</> : "You're signed in."}{" "}
            An admin still needs to assign your workspace role before you can get in.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col items-center gap-3 pt-2">
          <p className="text-center text-sm text-muted-foreground">
            This usually doesn't take long. Try signing in again once you've heard back, or check with whoever
            invited you to Data Fellows Studio.
          </p>
          <Button variant="outline" onClick={() => navigate("/sign-in", { replace: true })}>
            Back to sign in
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
